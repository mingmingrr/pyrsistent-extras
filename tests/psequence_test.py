from pyrsistent_extras import psequence, PSequence, sq
import pyrsistent_extras.lenses

import hypothesis
from hypothesis import given, strategies as st

import pickle
import functools
import pytest
import inspect
import typing
import gc
import os
import platform
import datetime
from lenses import lens

hypothesis.settings.register_profile('coverage',
	max_examples=200,
	deadline=datetime.timedelta(milliseconds=2500))

hypothesis.settings.register_profile('fast',
	max_examples=10,
	deadline=datetime.timedelta(milliseconds=1000),
	suppress_health_check=[
		hypothesis.HealthCheck.too_slow,
		hypothesis.HealthCheck.data_too_large,
	])

default_depth = 4

hypothesis.settings.load_profile(
	os.getenv('HYPOTHESIS_PROFILE', 'default'))

# {{{ strategies

class RefInt(int):
	'integer type that tracks garbage collection'
	count = 0
	def __new__(cls, *args, **kwargs):
		RefInt.count += 1
		return super().__new__(cls, *args, **kwargs)
	def __del__(self):
		if 'RefInt' not in globals() or RefInt is None: return
		RefInt.count -= 1

IndexSeq = object()

@functools.lru_cache(maxsize=None)
def fingernodes(elements, depth):
	'generate a Node'
	if depth <= 0: return st.builds(lambda x: ('Node', 1, x), elements)
	node = fingernodes(elements, depth-1)
	return st.builds(lambda xs: ('Node', sum(x[1] for x in xs), *xs),
		st.lists(node, min_size=2, max_size=3))

@functools.lru_cache(maxsize=None)
def fingerdigits(elements, depth):
	'generate a Digit'
	node = fingernodes(elements, depth)
	return st.builds(lambda xs: ('Digit', sum(x[1] for x in xs), *xs),
		st.lists(node, min_size=1, max_size=4))

@functools.lru_cache(maxsize=None)
def fingertrees(elements, depth, max_depth):
	'generate a Tree'
	if depth >= max_depth: return st.just(('Tree', 0))
	node = fingernodes(elements, depth)
	digit = fingerdigits(elements, depth)
	tree = fingertrees(elements, depth+1, max_depth)
	return st.one_of(st.builds(lambda n: ('Tree', n[1], n), node),
		st.builds(lambda l, m, r: ('Tree', l[1] + m[1] + r[1], l, m, r),
			digit, tree, digit))

def psequences(elements=st.integers(), max_depth=default_depth):
	'generate a PSequence as its tuple representation'
	return st.one_of(fingertrees(elements, 0, depth)
		for depth in range(max_depth + 1))

@st.composite
def indexseqs(draw, count=1, scale=2, *args, **kwargs):
	'generate an int-PSequence pair'
	seq = draw(psequences(*args, **kwargs))
	length = seq[1]
	ns = draw(st.lists(st.integers(
		-scale * length, max(0, scale * length - 1)),
		min_size=count, max_size=count,))
	return (*ns, seq)

# }}}

# {{{ checkers

def check_items(size, acc, *items):
	sizes = []
	for item in items:
		sizes.append(check_tree(*item, acc))
	assert sum(sizes) == size

def check_tree(tree, depth, acc):
	assert type(tree) is tuple
	ftype, size, *items = tree
	if ftype == 'Node':
		if len(items) == 1:
			assert size == 1
			assert depth == 0
			acc.append(items[0])
		else:
			assert len(items) in (2, 3)
			check_items(size, acc, *((item, depth - 1) for item in items))
	elif ftype == 'Digit':
		assert len(items) in (1, 2, 3, 4)
		check_items(size, acc, *((item, depth) for item in items))
	else:
		assert ftype == 'Tree'
		if len(items) == 0:
			assert size == 0
		elif len(items) == 1:
			check_items(size, acc, (items[0], depth))
		else:
			assert len(items) == 3
			check_items(size, acc, (items[0], depth),
				(items[1], depth + 1), (items[2], depth))
	return size

def check_seq(seq):
	'check invariants of PSequence while converting it to a list'
	acc = []
	check_tree(seq._totree(), 0, acc)
	return acc

# }}}

# {{{ decorators

def iter_tree(tree):
	'flatten tree representation of PSequence'
	ftype, size, *items = tree
	if size == 1 and ftype == 'Node':
		yield items[0]
	else:
		for item in items:
			yield from iter_tree(item)

def with_list(items):
	'track gc for list'
	return [RefInt(item) for item in items]

def with_fingertree(tree):
	ftype, size, *items = tree
	if size == 1 and ftype == 'Node':
		return ftype, size, RefInt(items[0])
	return (ftype, size, *map(with_fingertree, items))

def with_psequence(tree):
	'track gc for PSequence'
	tree = with_fingertree(tree)
	items = list(iter_tree(tree))
	tree = PSequence._fromtree(tree)
	return tree, items

def with_indexseq(indextree):
	*index, tree = indextree
	return (*map(RefInt, index), *with_psequence(tree))

def check_garbage(func):
	'check all garbage is collected properly'
	types = {k: {
		int: RefInt,
		list: with_list,
		PSequence: with_psequence,
		IndexSeq: with_indexseq,
	}.get(v, lambda x: x) for k, v in typing.get_type_hints(func).items()}
	@functools.wraps(func)
	def inner(*args, **kwargs):
		gc.collect(0)
		int0, ref0 = RefInt.count, PSequence._refcount()
		kwargs = inspect.getcallargs(func, *args, **kwargs)
		result =  func(**{k: types[k](v) for k, v in kwargs.items()})
		if platform.python_implementation() == 'CPython':
			gc.collect(0)
			assert PSequence._refcount() == ref0, 'tree ref count'
			assert RefInt.count == int0, 'int ref count'
		return result
	inner.__signature__ = inspect.signature(func)
	return inner

# }}}

# {{{ test_psequence

def test_c_ext(): # pragma: no cover
	if os.environ.get('PYRSISTENT_NO_C_EXTENSION'): pytest.skip()
	import pyrsistent_extras._psequence._c_ext

@given(psequences())
@check_garbage
def test_types(seqitems:PSequence):
	seq, items = seqitems
	assert isinstance(seq, PSequence)
	assert type(items) is list
	if items: assert type(items[0]) is RefInt

@given(psequences())
@check_garbage
def test_bool(seqitems:PSequence):
	seq, items = seqitems
	assert bool(seq) == bool(items)

@given(psequences())
@check_garbage
def test_length(seqitems:PSequence):
	seq, items = seqitems
	assert len(seq) == len(items)

@given(psequences())
@check_garbage
def test_tolist(seqitems:PSequence):
	seq, items = seqitems
	assert seq.tolist() == items

@given(psequences())
@check_garbage
def test_totuple(seqitems:PSequence):
	seq, items = seqitems
	assert seq.totuple() == tuple(items)

@given(st.lists(st.integers()))
@check_garbage
def test_fromlist(items:list):
	assert check_seq(psequence(items)) == items

@given(st.lists(st.integers()))
@check_garbage
def test_sq(items:list):
	assert check_seq(sq(*items)) == items

@given(psequences())
@check_garbage
def test_repr(seqitems:PSequence):
	seq, items = seqitems
	r = repr(seq)
	assert r.startswith('psequence')
	assert check_seq(eval(r)) == items

@given(psequences(), psequences())
@check_garbage
def test_compare(seqitems1:PSequence, seqitems2:PSequence):
	seq1, items1 = seqitems1 ; seq2, items2 = seqitems2
	assert seq1 == seq1 ; assert seq2 == seq2
	assert (seq1 == seq2) == (items1 == items2) == (seq1 == items2) == (items1 == seq2)
	assert (seq1 != seq2) == (items1 != items2) == (seq1 != items2) == (items1 != seq2)
	assert (seq1 <= seq2) == (items1 <= items2) == (seq1 <= items2) == (items1 <= seq2)
	assert (seq1 >= seq2) == (items1 >= items2) == (seq1 >= items2) == (items1 >= seq2)
	assert (seq1 <  seq2) == (items1 <  items2) == (seq1 <  items2) == (items1 <  seq2)
	assert (seq1 >  seq2) == (items1 >  items2) == (seq1 >  items2) == (items1 >  seq2)

@given(psequences())
@check_garbage
def test_viewleft(seqitems:PSequence):
	seq, items = seqitems
	if items:
		head, tail = seq.viewleft()
		assert head == items[0]
		assert check_seq(tail) == items[1:]
	else:
		with pytest.raises(IndexError):
			seq.viewleft()

@given(psequences())
@check_garbage
def test_viewright(seqitems:PSequence):
	seq, items = seqitems
	if items:
		init, last = seq.viewright()
		assert last == items[-1]
		assert check_seq(init) == items[:-1]
	else:
		with pytest.raises(IndexError):
			seq.viewright()

@given(indexseqs(count=2, scale=1))
@check_garbage
def test_view(iseqitems:IndexSeq):
	n1, n2, seq, items = iseqitems
	if items:
		m1, m2 = n1 % len(items), n2 % len(items)
		left, item, right = seq.view(n1)
		assert check_seq(left) == items[:m1]
		assert item == items[m1]
		assert check_seq(right) == items[m1+1:]
		if m1 != m2:
			if m1 > m2: n1, n2, m1, m2 = n2, n1, m2, m1
			left, item1, mid, item2, right = seq.view(n1, n2)
			with pytest.raises(IndexError):
				seq.view(n2, n1)
			assert check_seq(left) == items[:m1]
			assert item1 == items[m1]
			assert check_seq(mid) == items[m1+1:m2]
			assert item2 == items[m2]
			assert check_seq(right) == items[m2+1:]
	if not (-len(items) <= n1 < len(items)):
		with pytest.raises(IndexError):
			seq.view(n1)

@given(psequences())
@check_garbage
def test_peekleft(seqitems:PSequence):
	seq, items = seqitems
	if items:
		assert seq.left == items[0]
	else:
		with pytest.raises(IndexError):
			seq.left

@given(psequences())
@check_garbage
def test_peekright(seqitems:PSequence):
	seq, items = seqitems
	if items:
		assert seq.right == items[-1]
	else:
		with pytest.raises(IndexError):
			seq.right

@given(st.integers(), psequences())
@check_garbage
def test_appendleft(item:int, seqitems:PSequence):
	seq, items = seqitems
	assert check_seq(seq.appendleft(item)) == [item] + items

@given(st.integers(), psequences())
@check_garbage
def test_appendright(item:int, seqitems:PSequence):
	seq, items = seqitems
	expect = items + [item]
	assert check_seq(seq.append(item)) == expect
	assert check_seq(seq.appendright(item)) == expect

@given(psequences(), psequences())
@check_garbage
def test_extendleft(seqitems1:PSequence, seqitems2:PSequence):
	seq1, items1 = seqitems1
	seq2, items2 = seqitems2
	expect = items2 + items1
	assert check_seq(seq1.extendleft(seq2)) == expect
	assert check_seq(seq1.extendleft(items2)) == expect

@given(psequences(), psequences())
@check_garbage
def test_extendright(seqitems1:PSequence, seqitems2:PSequence):
	seq1, items1 = seqitems1
	seq2, items2 = seqitems2
	expect = items1 + items2
	assert check_seq(seq1.extend(seq2)) == expect
	assert check_seq(seq1.extendright(seq2)) == expect
	assert check_seq(seq1.extendright(items2)) == expect
	assert check_seq(seq1 + seq2) == expect

@given(psequences(max_depth=2), st.integers(-20, 100))
@hypothesis.settings(deadline=None)
@check_garbage
def test_repeat(seqitems:PSequence, times:int):
	seq, items = seqitems
	assert check_seq(seq * times) == items * times

@given(psequences(elements=st.integers(0, 100)), st.integers(0, 100))
@check_garbage
def test_contains(seqitems:PSequence, item:int):
	seq, items = seqitems
	assert (item in seq) == (item in items)

@given(psequences(elements=st.integers(0, 20)), st.integers(0, 20))
@check_garbage
def test_index(seqitems:PSequence, item:int):
	seq, items = seqitems
	if item in items:
		assert seq.index(item) == items.index(item)
	else:
		with pytest.raises(ValueError):
			seq.index(item)

@given(psequences(elements=st.integers(0, 20)), st.integers(0, 20))
@check_garbage
def test_remove(seqitems:PSequence, item:int):
	seq, items = seqitems
	if item in items:
		copy = items[:] ; copy.remove(item)
		assert check_seq(seq.remove(item)) == copy
	else:
		with pytest.raises(ValueError):
			seq.remove(item)

@given(psequences(elements=st.integers(0, 10)), st.integers(0, 10))
@check_garbage
def test_count(seqitems:PSequence, item:int):
	seq, items = seqitems
	assert seq.count(item) == items.count(item)

@given(psequences())
@check_garbage
def test_sort(seqitems:PSequence):
	seq, items = seqitems
	assert check_seq(seq.sort()) == sorted(items)
	assert check_seq(seq) == items

@given(indexseqs())
@check_garbage
def test_get(iseqitems:IndexSeq):
	index, seq, items = iseqitems
	if -len(items) <= index < len(items):
		assert seq[index] == items[index]
	else:
		with pytest.raises(IndexError):
			seq[index]

@given(indexseqs(), st.integers())
@check_garbage
def test_set_single(iseqitems:IndexSeq, item:int):
	index, seq, items = iseqitems
	if -len(items) <= index < len(items):
		copy = items[:] ; copy[index] = item
		assert check_seq(seq.set(index, item)) == copy
	else:
		with pytest.raises(IndexError):
			seq.set(index, item)

@given(indexseqs(count=2), st.lists(st.integers()))
@check_garbage
def test_set_slice(iseqitems:IndexSeq, update:list):
	start, stop, seq, items = iseqitems
	copy = items[:] ; copy[start:] = update
	assert check_seq(seq.set(slice(start, None), update)) == copy
	copy = items[:] ; copy[:stop] = update
	assert check_seq(seq.set(slice(None, stop), update)) == copy
	copy = items[:] ; copy[start:stop] = update
	assert check_seq(seq.set(slice(start, stop), update)) == copy

@given(indexseqs(count=2))
@check_garbage
def test_set_slice_reversed(iseqitems:IndexSeq):
	start, stop, seq, items = iseqitems
	update = [RefInt(1 - 2 * x) for x in items[start::-1]]
	copy = items[:] ; copy[start::-1] = update
	assert check_seq(seq.set(slice(start, None, -1), update)) == copy
	update = [RefInt(1 - 2 * x) for x in items[:stop:-1]]
	copy = items[:] ; copy[:stop:-1] = update
	assert check_seq(seq.set(slice(None, stop, -1), update)) == copy
	update = [RefInt(1 - 2 * x) for x in items[start:stop:-1]]
	copy = items[:] ; copy[start:stop:-1] = update
	assert check_seq(seq.set(slice(start, stop, -1), update)) == copy

@given(indexseqs(count=3))
@check_garbage
def test_set_slice_step(iseqitems:IndexSeq):
	start, stop, step, seq, items = iseqitems
	hypothesis.assume(step != 0)
	update = [RefInt(1 - 2 * x) for x in items[::step]]
	copy = items[:] ; copy[::step] = update
	assert check_seq(seq.set(slice(None, None, step), update)) == copy
	update = [RefInt(1 - 2 * x) for x in items[start::step]]
	copy = items[:] ; copy[start::step] = update
	assert check_seq(seq.set(slice(start, None, step), update)) == copy
	update = [RefInt(1 - 2 * x) for x in items[:stop:step]]
	copy = items[:] ; copy[:stop:step] = update
	assert check_seq(seq.set(slice(None, stop, step), update)) == copy
	update = [RefInt(1 - 2 * x) for x in items[start:stop:step]]
	copy = items[:] ; copy[start:stop:step] = update
	assert check_seq(seq.set(slice(start, stop, step), update)) == copy

@given(psequences(), st.lists(st.integers()))
@check_garbage
def test_mset(seqitems:PSequence, updates:list):
	seq, items = seqitems
	hypothesis.assume(len(items) > 0)
	if len(updates) % 2 == 1:
		updates = updates[:-1]
	copy, sets = items[:], []
	for i in range(0, len(updates), 2):
		updates[i] %= len(items)
		idx, val = updates[i], updates[i + 1]
		copy[idx] = val
		sets.append((idx, val))
	assert check_seq(seq.mset(*updates)) == copy
	assert check_seq(seq.mset(*sets)) == copy

@given(indexseqs(), st.integers())
@check_garbage
def test_insert(iseqitems:IndexSeq, item:int):
	index, seq, items = iseqitems
	copy = items[:] ; copy.insert(index, item)
	assert check_seq(seq.insert(index, item)) == copy

@given(indexseqs())
@check_garbage
def test_delete_single(iseqitems:IndexSeq):
	index, seq, items = iseqitems
	if -len(items) <= index < len(items):
		copy = items[:] ; del copy[index]
		assert check_seq(seq.delete(index)) == copy
	else:
		with pytest.raises(IndexError):
			seq.delete(index)

@given(indexseqs(count=2))
@check_garbage
def test_delete_slice(iseqitems:IndexSeq):
	start, stop, seq, items = iseqitems
	copy = items[:] ; del copy[start:]
	assert check_seq(seq.delete(slice(start, None))) == copy
	copy = items[:] ; del copy[:stop]
	assert check_seq(seq.delete(slice(None, stop))) == copy
	copy = items[:] ; del copy[start:stop]
	assert check_seq(seq.delete(slice(start, stop))) == copy

@given(indexseqs(count=2))
@check_garbage
def test_delete_slice_reversed(iseqitems:IndexSeq):
	start, stop, seq, items = iseqitems
	copy = items[:] ; del copy[start::-1]
	assert check_seq(seq.delete(slice(start, None, -1))) == copy
	copy = items[:] ; del copy[:stop:-1]
	assert check_seq(seq.delete(slice(None, stop, -1))) == copy
	copy = items[:] ; del copy[start:stop:-1]
	assert check_seq(seq.delete(slice(start, stop, -1))) == copy

@given(indexseqs(count=3))
@check_garbage
def test_delete_slice_step(iseqitems:IndexSeq):
	start, stop, step, seq, items = iseqitems
	hypothesis.assume(step != 0)
	copy = items[:] ; del copy[::step]
	assert check_seq(seq.delete(slice(None, None, step))) == copy
	copy = items[:] ; del copy[start::step]
	assert check_seq(seq.delete(slice(start, None, step))) == copy
	copy = items[:] ; del copy[:stop:step]
	assert check_seq(seq.delete(slice(None, stop, step))) == copy
	copy = items[:] ; del copy[start:stop:step]
	assert check_seq(seq.delete(slice(start, stop, step))) == copy

@given(psequences())
@check_garbage
def test_reverse(seqitems:PSequence):
	seq, items = seqitems
	assert check_seq(seq.reverse()) == items[::-1]

@given(indexseqs())
@check_garbage
def test_splitat(iseqitems:IndexSeq):
	index, seq, items = iseqitems
	left, right = seq.splitat(index)
	assert check_seq(left) == items[:index]
	assert check_seq(right) == items[index:]

@given(indexseqs())
@check_garbage
def test_chunksof(iseqitems:IndexSeq):
	chunk, seq, items = iseqitems
	chunk = chunk % max(1, len(items)) + 1
	subseqs = check_seq(seq.chunksof(chunk))
	subseqs = [tuple(check_seq(s)) for s in subseqs]
	expect = list(zip(*([iter(items)] * chunk)))
	rest = items[len(items) - len(items) % chunk:]
	if rest: expect.append(tuple(rest))
	assert subseqs == expect

@given(indexseqs(count=2))
@check_garbage
def test_slice(iseqitems:IndexSeq):
	start, stop, seq, items = iseqitems
	assert check_seq(seq[start:]) == items[start:]
	assert check_seq(seq[:stop]) == items[:stop]
	assert check_seq(seq[start:stop]) == items[start:stop]

@given(indexseqs(count=2))
@check_garbage
def test_slice_reversed(iseqitems:IndexSeq):
	start, stop, seq, items = iseqitems
	assert check_seq(seq[start::-1]) == items[start::-1]
	assert check_seq(seq[:stop:-1]) == items[:stop:-1]
	assert check_seq(seq[start:stop:-1]) == items[start:stop:-1]

@given(indexseqs(count=3))
@check_garbage
def test_slice_step(iseqitems:IndexSeq):
	start, stop, step, seq, items = iseqitems
	hypothesis.assume(step != 0)
	assert check_seq(seq[::step]) == items[::step]
	assert check_seq(seq[start::step]) == items[start::step]
	assert check_seq(seq[:stop:step]) == items[:stop:step]
	assert check_seq(seq[start:stop:step]) == items[start:stop:step]

@given(psequences())
@check_garbage
def test_reduce(seqitems:PSequence):
	seq, items = seqitems
	assert check_seq(pickle.loads(pickle.dumps(seq))) == items

@given(psequences())
@check_garbage
def test_hash(seqitems:PSequence):
	seq, items = seqitems
	assert hash(seq) == hash(psequence(items))

# }}}

# {{{ test_iter

@given(psequences())
@check_garbage
def test_iter(seqitems:PSequence):
	seq, items = seqitems
	iseq = iter(seq)
	for item in items:
		val = next(iseq)
		assert val == item
	with pytest.raises(StopIteration):
		next(iseq)

@given(psequences())
@check_garbage
def test_reversed(seqitems:PSequence):
	seq, items = seqitems
	iseq = reversed(seq)
	for item in reversed(items):
		val = next(iseq)
		assert val == item
	with pytest.raises(StopIteration):
		next(iseq)

# }}}

# {{{ test_evolver

@given(psequences())
@check_garbage
def test_evolver(seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	assert check_seq(evo.persistent()) == check_seq(seq)

@given(psequences())
@check_garbage
def test_evolver_bool(seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	assert bool(evo) == bool(items)

@given(psequences())
@check_garbage
def test_evolver_length(seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	assert len(evo) == len(items)

@given(psequences())
@check_garbage
def test_evolver_tolist(seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	assert evo.tolist() == list(items)

@given(psequences())
@check_garbage
def test_evolver_totuple(seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	assert evo.totuple() == tuple(items)

@given(psequences())
@check_garbage
def test_evolver_repr(seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	r = repr(evo)
	assert r.startswith('psequence')
	assert check_seq(eval(r)) == items

@given(psequences(), psequences())
@check_garbage
def test_evolver_compare(seqitems1:PSequence, seqitems2:PSequence):
	seq1, items1 = seqitems1 ; seq2, items2 = seqitems2
	evo1 = seq1.evolver() ; evo2 = seq2.evolver()
	assert evo1 == evo1 ; assert evo2 == evo2
	assert evo1 == seq1 ; assert evo2 == seq2
	assert (evo1 == evo2) == (items1 == items2) == (evo1 == items2) \
		== (items1 == evo2) == (evo1 == seq2) == (seq1 == evo2)
	assert (evo1 != evo2) == (items1 != items2) == (evo1 != items2) \
		== (items1 != evo2) == (evo1 != seq2) == (seq1 != evo2)
	assert (evo1 <= evo2) == (items1 <= items2) == (evo1 <= items2) \
		== (items1 <= evo2) == (evo1 <= seq2) == (seq1 <= evo2)
	assert (evo1 >= evo2) == (items1 >= items2) == (evo1 >= items2) \
		== (items1 >= evo2) == (evo1 >= seq2) == (seq1 >= evo2)
	assert (evo1 <  evo2) == (items1 <  items2) == (evo1 <  items2) \
		== (items1 <  evo2) == (evo1 <  seq2) == (seq1 <  evo2)
	assert (evo1 >  evo2) == (items1 >  items2) == (evo1 >  items2) \
		== (items1 >  evo2) == (evo1 >  seq2) == (seq1 >  evo2)

@given(psequences())
@check_garbage
def test_evolver_viewleft(seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	if items:
		head, tail = evo.viewleft()
		assert head == items[0]
		assert check_seq(tail) == items[1:]
		assert check_seq(evo) == items
	else:
		with pytest.raises(IndexError):
			evo.viewleft()

@given(psequences())
@check_garbage
def test_evolver_viewright(seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	if items:
		init, last = evo.viewright()
		assert last == items[-1]
		assert check_seq(init) == items[:-1]
		assert check_seq(evo) == items
	else:
		with pytest.raises(IndexError):
			evo.viewleft()

@given(indexseqs(count=2, scale=1))
@check_garbage
def test_evolver_view(iseqitems:IndexSeq):
	n1, n2, seq, items = iseqitems
	evo = seq.evolver()
	if items:
		m1, m2 = n1 % len(items), n2 % len(items)
		left, item, right = evo.view(n1)
		assert check_seq(left) == items[:m1]
		assert item == items[m1]
		assert check_seq(right) == items[m1+1:]
		if m1 != m2:
			if m1 > m2: n1, n2, m1, m2 = n2, n1, m2, m1
			left, item1, mid, item2, right = evo.view(n1, n2)
			assert check_seq(left) == items[:m1]
			assert item1 == items[m1]
			assert check_seq(mid) == items[m1+1:m2]
			assert item2 == items[m2]
			assert check_seq(right) == items[m2+1:]
	else:
		with pytest.raises(IndexError):
			seq.view(0)

@given(psequences())
@check_garbage
def test_evolver_peekleft(seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	if items:
		assert evo.left == items[0]
	else:
		with pytest.raises(IndexError):
			evo.left

@given(psequences())
@check_garbage
def test_evolver_peekright(seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	if items:
		assert evo.right == items[-1]
	else:
		with pytest.raises(IndexError):
			evo.right

@given(psequences())
@check_garbage
def test_evolver_popleft(seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	if items:
		assert evo.popleft() == items[0]
		assert check_seq(evo) == items[1:]
	else:
		with pytest.raises(IndexError):
			evo.popleft()

@given(psequences())
@check_garbage
def test_evolver_popright(seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	if items:
		assert evo.popright() == items[-1]
		assert check_seq(evo) == items[:-1]
	else:
		with pytest.raises(IndexError):
			evo.popright()

@given(indexseqs())
@check_garbage
def test_evolver_pop(iseqitems:IndexSeq):
	index, seq, items = iseqitems
	evo = seq.evolver()
	if items:
		assert evo.pop() == items[-1]
		assert check_seq(evo) == items[:-1]
	else:
		with pytest.raises(IndexError):
			evo.pop()
	evo = seq.evolver()
	if -len(items) <= index < len(items):
		assert evo.pop(index) == items.pop(index)
		assert check_seq(evo) == items
	else:
		with pytest.raises(IndexError):
			evo.pop(index)

@given(st.integers(), psequences())
@check_garbage
def test_evolver_appendleft(item:int, seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	evo.appendleft(item)
	assert check_seq(evo) == [item] + items

@given(st.integers(), psequences())
@check_garbage
def test_evolver_appendright(item:int, seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	evo.append(item)
	assert check_seq(evo) == items + [item]
	evo = seq.evolver()
	evo.appendright(item)
	assert check_seq(evo) == items + [item]

@given(psequences(), psequences())
@check_garbage
def test_evolver_extendleft(seqitems1:PSequence, seqitems2:PSequence):
	seq1, items1 = seqitems1
	seq2, items2 = seqitems2
	expect = items2 + items1
	evo = seq1.evolver()
	evo.extendleft(seq2)
	assert check_seq(evo) == expect
	evo = seq1.evolver()
	evo.extendleft(seq2.evolver())
	assert check_seq(evo) == expect
	evo = seq1.evolver()
	evo.extendleft(items2)
	assert check_seq(evo) == expect

@given(psequences(), psequences())
@check_garbage
def test_evolver_extendright(seqitems1:PSequence, seqitems2:PSequence):
	seq1, items1 = seqitems1
	seq2, items2 = seqitems2
	expect = items1 + items2
	evo = seq1.evolver()
	evo.extend(seq2)
	assert check_seq(evo) == expect
	evo = seq1.evolver()
	evo.extendright(seq2)
	assert check_seq(evo) == expect
	evo = seq1.evolver()
	evo.extendright(seq2.evolver())
	assert check_seq(evo) == expect
	evo = seq1.evolver()
	evo.extendright(items2)
	assert check_seq(evo) == expect

@given(psequences(max_depth=2), st.integers(-20, 100))
@hypothesis.settings(deadline=None)
@check_garbage
def test_evolver_repeat(seqitems:PSequence, times:int):
	seq, items = seqitems
	expect = items * times
	evo = seq.evolver()
	assert check_seq(evo * times) == expect
	assert check_seq(evo) == items
	evo *= times
	assert check_seq(evo) == expect

@given(psequences(elements=st.integers(0, 100)), st.integers(0, 100))
@check_garbage
def test_evolver_contains(seqitems:PSequence, item:int):
	seq, items = seqitems
	evo = seq.evolver()
	assert (item in evo) == (item in items)

@given(psequences(elements=st.integers(0, 20)), st.integers(0, 20))
@check_garbage
def test_evolver_index(seqitems:PSequence, item:int):
	seq, items = seqitems
	evo = seq.evolver()
	if item in items:
		assert evo.index(item) == items.index(item)
	else:
		with pytest.raises(ValueError):
			evo.index(item)

@given(psequences(elements=st.integers(0, 20)), st.integers(0, 20))
@check_garbage
def test_evolver_remove(seqitems:PSequence, item:int):
	seq, items = seqitems
	evo = seq.evolver()
	if item in items:
		copy = items[:] ; copy.remove(item)
		evo.remove(item)
		assert check_seq(evo) == copy
	else:
		with pytest.raises(ValueError):
			evo.remove(item)

@given(psequences(elements=st.integers(0, 10)), st.integers(0, 10))
@check_garbage
def test_evolver_count(seqitems:PSequence, item:int):
	seq, items = seqitems
	evo = seq.evolver()
	assert evo.count(item) == items.count(item)

@given(psequences())
@check_garbage
def test_evolver_sort(seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	evo.sort()
	assert check_seq(evo) == sorted(items)

@given(psequences())
@check_garbage
def test_evolver_copy(seqitems:PSequence):
	seq, items = seqitems
	hypothesis.assume(len(items))
	evo1 = seq.evolver()
	evo2 = evo1.copy()
	evo2[0] *= 2
	assert check_seq(evo1) == items
	items[0] *= 2
	assert check_seq(evo2) == items

@given(psequences())
@check_garbage
def test_evolver_clear(seqitems:PSequence):
	seq, items = seqitems
	hypothesis.assume(len(items))
	evo = seq.evolver()
	evo.clear()
	assert check_seq(evo) == []

@given(indexseqs())
@check_garbage
def test_evolver_get(iseqitems:IndexSeq):
	index, seq, items = iseqitems
	evo = seq.evolver()
	if -len(items) <= index < len(items):
		assert evo[index] == items[index]
	else:
		with pytest.raises(IndexError):
			evo[index]

@given(indexseqs(), st.integers())
@check_garbage
def test_evolver_set_single(iseqitems:IndexSeq, item:int):
	index, seq, items = iseqitems
	if -len(items) <= index < len(items):
		copy = items[:] ; copy[index] = item
		evo = seq.evolver() ; evo.set(index, item)
		assert check_seq(seq.set(index, item)) == copy
		evo = seq.evolver() ; evo[index] = item
		assert check_seq(seq.set(index, item)) == copy
	else:
		evo = seq.evolver()
		with pytest.raises(IndexError):
			evo.set(index, item)
		with pytest.raises(IndexError):
			evo[index] = item

@given(indexseqs(count=2), st.lists(st.integers()))
@check_garbage
def test_evolver_set_slice(iseqitems:IndexSeq, update:list):
	start, stop, seq, items = iseqitems
	# [start:]
	copy = items[:] ; copy[start:] = update
	evo = seq.evolver() ; evo.set(slice(start, None), update)
	assert check_seq(evo) == copy
	evo = seq.evolver() ; evo[start:] = update
	assert check_seq(evo) == copy
	# [:stop]
	copy = items[:] ; copy[:stop] = update
	evo = seq.evolver() ; evo.set(slice(None, stop), update)
	assert check_seq(evo) == copy
	evo = seq.evolver() ; evo[:stop] = update
	assert check_seq(evo) == copy
	# [start:stop]
	copy = items[:] ; copy[start:stop] = update
	evo = seq.evolver() ; evo.set(slice(start, stop), update)
	assert check_seq(evo) == copy
	evo = seq.evolver() ; evo[start:stop] = update
	assert check_seq(evo) == copy

@given(indexseqs(count=2))
@check_garbage
def test_evolver_set_slice_reversed(iseqitems:IndexSeq):
	start, stop, seq, items = iseqitems
	# [start::-1]
	update = [RefInt(1 - 2 * x) for x in items[start::-1]]
	copy = items[:] ; copy[start::-1] = update
	evo = seq.evolver() ; evo.set(slice(start, None, -1), update)
	assert check_seq(evo) == copy
	evo = seq.evolver() ; evo[start::-1] = update
	assert check_seq(evo) == copy
	# [:stop:-1]
	update = [RefInt(1 - 2 * x) for x in items[:stop:-1]]
	copy = items[:] ; copy[:stop:-1] = update
	evo = seq.evolver() ; evo.set(slice(None, stop, -1), update)
	assert check_seq(evo) == copy
	evo = seq.evolver() ; evo[:stop:-1] = update
	assert check_seq(evo) == copy
	# [start:stop:-1]
	update = [RefInt(1 - 2 * x) for x in items[start:stop:-1]]
	copy = items[:] ; copy[start:stop:-1] = update
	evo = seq.evolver() ; evo.set(slice(start, stop, -1), update)
	assert check_seq(evo) == copy
	evo = seq.evolver() ; evo[start:stop:-1] = update
	assert check_seq(evo) == copy

@given(indexseqs(count=3))
@check_garbage
def test_evolver_set_slice_step(iseqitems:IndexSeq):
	start, stop, step, seq, items = iseqitems
	hypothesis.assume(step != 0)
	# [start::step]
	update = [RefInt(1 - 2 * x) for x in items[start::step]]
	copy = items[:] ; copy[start::step] = update
	evo = seq.evolver() ; evo.set(slice(start, None, step), update)
	assert check_seq(evo) == copy
	evo = seq.evolver() ; evo[start::step] = update
	assert check_seq(evo) == copy
	# [:stop:step]
	update = [RefInt(1 - 2 * x) for x in items[:stop:step]]
	copy = items[:] ; copy[:stop:step] = update
	evo = seq.evolver() ; evo.set(slice(None, stop, step), update)
	assert check_seq(evo) == copy
	evo = seq.evolver() ; evo[:stop:step] = update
	assert check_seq(evo) == copy
	# [start:stop:step]
	update = [RefInt(1 - 2 * x) for x in items[start:stop:step]]
	copy = items[:] ; copy[start:stop:step] = update
	evo = seq.evolver() ; evo.set(slice(start, stop, step), update)
	assert check_seq(evo) == copy
	evo = seq.evolver() ; evo[start:stop:step] = update
	assert check_seq(evo) == copy

@given(psequences(), st.lists(st.integers()))
@check_garbage
def test_evolver_mset(seqitems:PSequence, updates:list):
	seq, items = seqitems
	hypothesis.assume(len(items) > 0)
	if len(updates) % 2 == 1:
		updates = updates[:-1]
	copy, sets = items[:], []
	for i in range(0, len(updates), 2):
		updates[i] %= len(items)
		idx, val = updates[i], updates[i + 1]
		copy[idx] = val
		sets.append((idx, val))
	evo = seq.evolver()
	evo.mset(*updates)
	assert check_seq(evo) == copy
	evo = seq.evolver()
	evo.mset(*sets)
	assert check_seq(evo) == copy

@given(indexseqs(), st.integers())
@check_garbage
def test_evolver_insert(iseqitems:IndexSeq, item:int):
	index, seq, items = iseqitems
	copy = items[:] ; copy.insert(index, item)
	evo = seq.evolver() ; evo.insert(index, item)
	assert check_seq(evo) == copy

@given(indexseqs())
@check_garbage
def test_evolver_delete_single(iseqitems:IndexSeq):
	index, seq, items = iseqitems
	if -len(items) <= index < len(items):
		copy = items[:] ; del copy[index]
		evo = seq.evolver() ; evo.delete(index)
		assert check_seq(evo) == copy
		evo = seq.evolver() ; del evo[index]
		assert check_seq(evo) == copy
	else:
		with pytest.raises(IndexError):
			evo = seq.evolver() ; evo.delete(index)
		with pytest.raises(IndexError):
			evo = seq.evolver() ; del evo[index]

@given(indexseqs(count=2))
@check_garbage
def test_evolver_delete_slice(iseqitems:IndexSeq):
	start, stop, seq, items = iseqitems
	copy = items[:] ; del copy[start:]
	evo = seq.evolver() ; del evo[start:]
	assert check_seq(evo) == copy
	copy = items[:] ; del copy[:stop]
	evo = seq.evolver() ; del evo[:stop]
	assert check_seq(evo) == copy
	copy = items[:] ; del copy[start:stop]
	evo = seq.evolver() ; del evo[start:stop]
	assert check_seq(evo) == copy

@given(indexseqs(count=2))
@check_garbage
def test_evolver_delete_slice_reversed(iseqitems:IndexSeq):
	start, stop, seq, items = iseqitems
	copy = items[:] ; del copy[start::-1]
	evo = seq.evolver() ; del evo[start::-1]
	assert check_seq(evo) == copy
	copy = items[:] ; del copy[:stop:-1]
	evo = seq.evolver() ; del evo[:stop:-1]
	assert check_seq(evo) == copy
	copy = items[:] ; del copy[start:stop:-1]
	evo = seq.evolver() ; del evo[start:stop:-1]
	assert check_seq(evo) == copy

@given(indexseqs(count=3))
@check_garbage
def test_evolver_delete_slice_step(iseqitems:IndexSeq):
	start, stop, step, seq, items = iseqitems
	hypothesis.assume(step != 0)
	copy = items[:] ; del copy[::step]
	evo = seq.evolver() ; del evo[::step]
	assert check_seq(evo) == copy
	copy = items[:] ; del copy[start::step]
	evo = seq.evolver() ; del evo[start::step]
	assert check_seq(evo) == copy
	copy = items[:] ; del copy[:stop:step]
	evo = seq.evolver() ; del evo[:stop:step]
	assert check_seq(evo) == copy
	copy = items[:] ; del copy[start:stop:step]
	evo = seq.evolver() ; del evo[start:stop:step]
	assert check_seq(evo) == copy

@given(psequences())
@check_garbage
def test_evolver_reverse(seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	evo.reverse()
	assert check_seq(evo) == items[::-1]

@given(indexseqs())
@check_garbage
def test_evolver_splitat(iseqitems:IndexSeq):
	index, seq, items = iseqitems
	evo = seq.evolver()
	left, right = evo.splitat(index)
	assert check_seq(left) == items[:index]
	assert check_seq(right) == items[index:]

@given(indexseqs(count=2))
@check_garbage
def test_evolver_slice(iseqitems:IndexSeq):
	start, stop, seq, items = iseqitems
	evo = seq.evolver()
	assert check_seq(evo[start:]) == items[start:]
	assert check_seq(evo[:stop]) == items[:stop]
	assert check_seq(evo[start:stop]) == items[start:stop]

@given(indexseqs(count=2))
@check_garbage
def test_evolver_slice_reversed(iseqitems:IndexSeq):
	start, stop, seq, items = iseqitems
	evo = seq.evolver()
	assert check_seq(evo[start::-1]) == items[start::-1]
	assert check_seq(evo[:stop:-1]) == items[:stop:-1]
	assert check_seq(evo[start:stop:-1]) == items[start:stop:-1]

@given(indexseqs(count=3))
@check_garbage
def test_evolver_slice_step(iseqitems:IndexSeq):
	start, stop, step, seq, items = iseqitems
	hypothesis.assume(step != 0)
	evo = seq.evolver()
	assert check_seq(evo[::step]) == items[::step]
	assert check_seq(evo[start::step]) == items[start::step]
	assert check_seq(evo[:stop:step]) == items[:stop:step]
	assert check_seq(evo[start:stop:step]) == items[start:stop:step]

@given(psequences())
@check_garbage
def test_evolver_reduce(seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	assert check_seq(pickle.loads(pickle.dumps(evo))) == items

@given(psequences())
@check_garbage
def test_evolver_hash(seqitems:PSequence):
	seq, items = seqitems
	evo = seq.evolver()
	assert hash(seq) == hash(psequence(items))

@given(indexseqs(), st.integers())
@check_garbage
def test_lenses(iseqitems:IndexSeq, item:int):
	index, seq, items = iseqitems
	getter = lens[index].get()
	setter = lens[index].set(item)
	remove = lens.Contains(item).set(False)
	adder = lens.Contains(item).set(True)
	each = lens.Each().modify(lambda x: x * 2)
	if -len(items) <= index < len(items):
		assert getter(seq) == getter(items)
		assert check_seq(setter(seq)) == setter(items[:])
	else:
		with pytest.raises(IndexError):
			assert getter(seq)
		with pytest.raises(IndexError):
			assert setter(seq)
	assert check_seq(remove(seq)) == remove(items[:])
	assert check_seq(adder(seq)) == adder(items[:])
	assert check_seq(each(seq)) == each(items[:])
	assert check_seq(seq) == items

# }}}

# vim: set foldmethod=marker:
