from pyrsistent_extras.pheap import \
	hl, pminheap, PMinHeap, hg, pmaxheap, PMaxHeap

import hypothesis
from hypothesis import given, strategies as st

import pickle
import pytest
import bisect

def pitems(keys=st.integers(), values=st.integers()):
	return st.tuples(keys, values)

def makeheaps(funcs):
	def inner(unique=False, keys=st.integers(), values=st.integers(), **kwargs):
		if unique: # pragma: no cover
			kwargs['unique'] = True
			kwargs['unique_by'] = lambda xs: xs[0]
		lists = st.lists(pitems(keys, values), **kwargs)
		return st.builds(lambda f, xs: (f(xs), list(sorted(xs))), funcs, lists)
	return inner

pmaxheaps = makeheaps(st.just(pmaxheap))
pminheaps = makeheaps(st.just(pminheap))
pheaps = makeheaps(st.one_of(st.just(pminheap), st.just(pmaxheap)))

def pheappairs(heaps):
	return st.one_of(st.tuples(heaps(pminheaps), heaps(pminheaps)),
		st.tuples(heaps(pmaxheaps), heaps(pmaxheaps)))

class PrettyHeap: # pragma: no cover
	def __init__(self, heap):
		self.heap = heap
	@staticmethod
	def tree(tree, depth, acc):
		if tree is None: return
		acc.append('{}Tree {} {}'.format('  ' * depth, tree._key, tree._value))
		PrettyHeap.tree(tree._child, depth + 1, acc)
		PrettyHeap.tree(tree._sibling, depth, acc)
	@staticmethod
	def forest(forest, acc):
		if forest is None: return
		acc.append('  Forest {}'.format(forest._order))
		PrettyHeap.tree(forest._tree, 2, acc)
		PrettyHeap.forest(forest._next, acc)
	def __repr__(self):
		acc = ['{} {} {} {}'.format(
			type(self.heap).__name__,
			self.heap._size,
			self.heap._key,
			self.heap._value)]
		PrettyHeap.forest(self.heap._forest, acc)
		return '\n'.join(acc)

def check_tree(tree, down, tip, order, acc):
	'''
	check invariants of Tree
	'''
	if tree is None: return 0
	if down: assert tree._key <= tip
	else: assert tree._key >= tip
	acc.append((tree._key, tree._value))
	if order == 0:
		assert tree._child is None
		assert tree._sibling is None
	else:
		assert tree._child is not None
	size1 = check_tree(tree._child, down, tree._key, order - 1, acc)
	size2 = check_tree(tree._sibling, down, tip, order - 1, acc)
	return size1 + size2 + 1

def check_forest(forest, down, tip, acc):
	'''
	check invariants of Forest
	'''
	if forest is None: return 0
	assert forest._tree._sibling is None
	size = check_tree(forest._tree, down, tip, forest._order, acc)
	assert size == (1 << forest._order)
	size += check_forest(forest._next, down, tip, acc)
	return size

def check_heap(heap):
	'''
	check invariants of Heap
	'''
	assert isinstance(heap, (PMinHeap, PMaxHeap))
	assert heap._down == isinstance(heap, PMaxHeap)
	if heap._size == 0:
		assert heap._key is None
		assert heap._value is None
		assert heap._forest is None
		return []
	acc = [(heap._key, heap._value)]
	size = check_forest(heap._forest, heap._down, heap._key, acc)
	assert size + 1 == heap._size
	return list(sorted(acc))

@given(pheaps(min_size=20))
def test_types(heapitems):
	heap, items = heapitems
	assert isinstance(heap, (PMinHeap, PMaxHeap))
	assert type(items) is list
	if items:
		key, value = items[0]
		assert type(key) is int
		assert type(value) is int
	assert check_heap(heap) == items

@given(st.lists(pitems()))
def test_hl_hg(items):
	assert check_heap(hg(*items)) == check_heap(pmaxheap(items))
	assert check_heap(hl(*items)) == check_heap(pminheap(items))

@given(pheaps())
def test_fromkeys(heapitems):
	heap, items = heapitems
	fromkeys = globals()[heap._name].fromkeys
	xs = check_heap(fromkeys(k for k, _ in items))
	assert xs == [(k, None) for k, _ in items]

@given(pheaps(), st.integers(), st.integers())
def test_push(heapitems, key, value):
	heap, items = heapitems
	bisect.insort(items, (key, value))
	assert check_heap(heap.push(key, value)) == items

@given(pheaps(), st.integers(), st.integers())
def test_pop(heapitems, key, value):
	heap, items = heapitems
	if items:
		key1, value1, heap1 = heap.pop()
		if isinstance(heap, PMaxHeap):
			key2, value2 = items[-1]
			items2 = items[:-1]
		else:
			key2, value2 = items[0]
			items2 = items[1:]
		assert key1 == key2
		assert [k for k, _ in check_heap(heap1)] == [k for k, _ in items2]
	else:
		with pytest.raises(IndexError):
			heap.pop()

@given(pheappairs(lambda heaps: heaps()))
def test_merge(args):
	heapitems1, heapitems2 = args
	heap1, items1 = heapitems1
	heap2, items2 = heapitems2
	items = list(sorted(items1 + items2))
	assert check_heap(heap1.merge(heap2)) == items
	assert check_heap(heap1 + heap2) == items

@given(pheaps(), st.integers())
def test_contains(heapitems, key):
	heap, items = heapitems
	assert (key in heap) == any(k == key for k, v in items)

@given(pheaps())
def test_len(heapitems):
	heap, items = heapitems
	assert len(heap) == len(items)

@given(pheappairs(lambda heaps:
	heaps(keys=st.integers(1,4), values=st.just(0))))
def test_compare_int(args):
	heapitems1, heapitems2 = args
	heap1, items1 = heapitems1
	heap2, items2 = heapitems2
	if heap1._down:
		assert heap2._down
		items1 = list(reversed(items1))
		items2 = list(reversed(items2))
	assert heap1 == heap1 ; assert heap2 == heap2
	assert (heap1 == heap2) == (items1 == items2)
	assert (heap1 != heap2) == (items1 != items2)
	assert (heap1 <= heap2) == (items1 <= items2)
	assert (heap1 >= heap2) == (items1 >= items2)
	assert (heap1 <  heap2) == (items1 <  items2)
	assert (heap1 >  heap2) == (items1 >  items2)

@given(pheappairs(lambda heaps:
	heaps(keys=st.integers(1,4), values=st.just(None))))
def test_compare_none(args):
	heapitems1, heapitems2 = args
	heap1, items1 = heapitems1
	heap2, items2 = heapitems2
	assert heap1 == heap1 ; assert heap2 == heap2
	assert (heap1 == heap2) == (items1 == items2)
	assert (heap1 != heap2) == (items1 != items2)

smallitems = pitems(keys=st.integers(1,4), values=st.integers(1,4))
@given(st.lists(smallitems), st.lists(smallitems))
def test_compare_dict(items1, items2):
	items1 = [(k, {v:None}) for k, v in sorted(items1)]
	items2 = [(k, {v:None}) for k, v in sorted(items2)]
	heap1, heap2 = pminheap(items1), pminheap(items2)
	assert heap1 == heap1 ; assert heap2 == heap2
	assert (heap1 == heap2) == (items1 == items2)
	assert (heap1 != heap2) == (items1 != items2)

@given(pheaps())
def test_hash(heapitems):
	heap1, items = heapitems
	heap2 = globals()[heap1._name](reversed(items))
	assert hash(heap1) == hash(heap2)

@given(pheaps())
def test_repr(heapitems):
	heap1, items = heapitems
	heap2 = eval(repr(heap1))
	assert type(heap1) == type(heap2)
	assert check_heap(heap2) == sorted(items)

@given(pheaps())
def test_reduce(heapitems):
	heap, items = heapitems
	assert check_heap(pickle.loads(pickle.dumps(heap))) == sorted(items)

# vim: set foldmethod=marker:
