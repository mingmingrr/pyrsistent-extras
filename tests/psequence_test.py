from __future__ import annotations
from typing import List

from pyrsistent_extras._psequence._cpp_ext import psequence, PSequence, sq, PSequenceEvolver
import pyrsistent_extras.lenses

from hypothesis import given, strategies as st

import operator
import pickle
import pytest
from lenses import lens

@given(st.lists(st.integers()))
def test_properties(items:List[int]):
	seq = psequence(items)
	evo = seq.evolver()
	assert isinstance(seq, PSequence)
	assert isinstance(evo, PSequenceEvolver)
	assert bool(seq) == bool(items)
	assert bool(evo) == bool(items)
	assert len(seq) == len(items)
	assert len(evo) == len(items)
	assert seq.tolist() == items
	assert evo.tolist() == items
	assert seq.totuple() == tuple(items)
	assert evo.totuple() == tuple(items)
	assert seq == sq(*items)
	assert evo == sq(*items)
	assert eval(repr(seq)) == seq
	assert eval(repr(evo)) == evo
	assert seq.sort() == sorted(items)
	copy = seq.evolver(); copy.sort()
	assert copy == sorted(items)
	assert seq.reverse() == items[::-1]
	copy = seq.evolver(); copy.reverse()
	assert copy == items[::-1]
	assert pickle.loads(pickle.dumps(seq)) == seq
	assert pickle.loads(pickle.dumps(evo)) == evo
	assert list(seq) == items
	assert list(evo) == items
	assert list(reversed(seq)) == items[::-1]
	assert list(reversed(evo)) == items[::-1]

@given(st.lists(st.integers()), st.lists(st.integers()))
def test_compare(items1:List[int], items2:List[int]):
	seq1, seq2 = psequence(items1), psequence(items2)
	evo1, evo2 = seq1.evolver(), seq2.evolver()
	for op in [operator.eq, operator.ne, operator.gt, operator.ge, operator.lt, operator.le]:
		assert len(set(op(x, y) for x in [seq1, evo1, items1] for y in [seq2, evo2, items2])) == 1

@given(st.lists(st.integers(),min_size=1), st.integers(), st.integers())
def test_view(items:List[int], n1:int, n2:int):
	seq = psequence(items)
	evo = seq.evolver()
	if items:
		assert seq.left == items[0]
		assert evo.left == items[0]
		assert seq.right == items[-1]
		assert evo.right == items[-1]
		assert seq.viewleft() == (items[0], items[1:])
		assert evo.viewleft() == (items[0], items[1:])
		assert seq.viewright() == (items[:-1], items[-1])
		assert evo.viewright() == (items[:-1], items[-1])
	else:
		with pytest.raises(IndexError): seq.left
		with pytest.raises(IndexError): evo.left
		with pytest.raises(IndexError): seq.right
		with pytest.raises(IndexError): evo.right
		with pytest.raises(IndexError): seq.viewleft()
		with pytest.raises(IndexError): evo.viewleft()
		with pytest.raises(IndexError): seq.viewright()
		with pytest.raises(IndexError): evo.viewright()
	m1, m2 = sorted(n % len(items) for n in [n1, n2])
	assert seq.view(m1) == [items[:m1], items[m1], items[m1+1:]]
	assert evo.view(m1) == [items[:m1], items[m1], items[m1+1:]]
	assert seq.splitat(m1) == (items[:m1], items[m1:])
	assert evo.splitat(m1) == (items[:m1], items[m1:])
	if m1 != m2:
		assert seq.view(m1, m2) == \
			[items[:m1], items[m1], items[m1+1:m2], items[m2], items[m2+1:]]
		assert evo.view(m1, m2) == \
			[items[:m1], items[m1], items[m1+1:m2], items[m2], items[m2+1:]]
		with pytest.raises(IndexError): seq.view(m2, m1)
		with pytest.raises(IndexError): evo.view(m2, m1)

@given(st.lists(st.integers()), st.integers(min_value=1, max_value=10))
def test_chunksof(items:List[int], size:int):
	chunks = psequence(items).chunksof(size)
	assert all(len(chunk) == size for chunk in chunks[:-1])
	assert sum(len(chunk) for chunk in chunks) == len(items)
	if chunks: assert sum(chunks[1:], start=chunks[0]) == items
	assert chunks == psequence(items).evolver().chunksof(size)

@given(st.lists(st.integers()), st.lists(st.integers()))
def test_extend(items1:List[int], items2:List[int]):
	seq1, seq2 = psequence(items1), psequence(items2)
	assert seq1 + seq2 == seq1.extend(seq2) == seq1.extendright(seq2) \
		== seq2.extendleft(seq1) == items1 + items2
	evo1 = seq1.evolver(); evo1.extend(seq2)
	assert evo1 == seq1.evolver() + seq2.evolver() == items1 + items2

@given(st.lists(st.integers()), st.integers(min_value=-2, max_value=10))
def test_repeat(items:List[int], value:int):
	seq = psequence(items)
	assert seq * value == items * value

@given(st.lists(st.integers(min_value=0, max_value=20)),
	st.integers(min_value=0, max_value=20))
def test_query(items:List[int], value:int):
	seq = psequence(items)
	evo = seq.evolver()
	assert (value in seq) == (value in evo) == (value in items)
	assert seq.count(value) == evo.count(value) == items.count(value)
	if value in items:
		assert seq.index(value) == evo.index(value) == items.index(value)
		evo.remove(value); items.remove(value)
		assert seq.remove(value) == evo == items
	else:
		with pytest.raises(ValueError): seq.index(value)
		with pytest.raises(ValueError): evo.index(value)
		with pytest.raises(ValueError): seq.remove(value)
		with pytest.raises(ValueError): evo.remove(value)

@given(st.lists(st.integers(),min_size=1), st.integers(), st.integers())
def test_access(items:List[int], n1:int, n2:int):
	seq = psequence(items)
	evo = seq.evolver()
	m1, m2 = sorted(n % len(items) for n in [n1, n2])
	r1, r2 = (-len(items) + m for m in [m1, m2])
	# get
	assert seq[m1] == evo[m1] == seq[r1] == evo[r1] == items[m1]
	assert seq[m1:] == evo[m1:] == seq[r1:] == evo[r1:] == items[m1:]
	assert seq[:m1] == evo[:m1] == seq[:r1] == evo[:r1] == items[:m1]
	assert seq[m1:m2] == evo[m1:m2] == seq[r1:r2] == evo[r1:r2] \
		== seq[m1:r2] == evo[m1:r2] == seq[r1:m2] == evo[r1:m2] == items[m1:m2]
	assert seq[m1:m2:3] == evo[m1:m2:3] == seq[r1:r2:3] == evo[r1:r2:3] == items[m1:m2:3]
	# set
	copy = items.copy(); copy[m1] = m1
	evo = seq.evolver(); evo[m1] = m1
	assert seq.set(m1, m1) == seq.set(r1, m1) == evo == copy
	copy = items.copy(); values = range(m1, len(items)); copy[m1:] = values
	evo = seq.evolver(); values = range(m1, len(items)); evo[m1:] = values
	assert seq.set(slice(m1,None), values) == seq.set(slice(r1,None), values) == evo == copy
	copy = items.copy(); values = range(0, m1); copy[:m1] = values
	evo = seq.evolver(); values = range(0, m1); evo[:m1] = values
	assert seq.set(slice(None,m1), values) == seq.set(slice(None,r1), values) == evo == copy
	copy = items.copy(); values = range(m1, m2); copy[m1:m2] = values
	evo = seq.evolver(); values = range(m1, m2); evo[m1:m2] = values
	assert seq.set(slice(m1,m2), values) == seq.set(slice(r1,r2), values) \
		== seq.set(slice(m1,r2), values) == seq.set(slice(r1,m2), values) == evo == copy
	copy = items.copy(); values = range(m1, m2, 3); copy[m1:m2:3] = values
	evo = seq.evolver(); values = range(m1, m2, 3); evo[m1:m2:3] = values
	assert seq.set(slice(m1,m2,3), values) == seq.set(slice(r1,r2,3), values) == evo == copy
	# del
	copy = items.copy(); del copy[m1]
	evo = seq.evolver(); del evo[m1]
	assert seq.delete(m1) == seq.delete(r1) == evo == copy
	copy = items.copy(); del copy[m1:]
	evo = seq.evolver(); del evo[m1:]
	assert seq.delete(slice(m1,None)) == seq.delete(slice(r1,None)) == evo == copy
	copy = items.copy(); del copy[:m1]
	evo = seq.evolver(); del evo[:m1]
	assert seq.delete(slice(None,m1)) == seq.delete(slice(None,r1)) == evo == copy
	copy = items.copy(); del copy[m1:m2]
	evo = seq.evolver(); del evo[m1:m2]
	assert seq.delete(slice(m1,m2)) == seq.delete(slice(r1,r2)) \
		== seq.delete(slice(m1,r2)) == seq.delete(slice(r1,m2)) == evo == copy
	copy = items.copy(); del copy[m1:m2:3]
	evo = seq.evolver(); del evo[m1:m2:3]
	assert seq.delete(slice(m1,m2,3)) == seq.delete(slice(r1,r2,3)) == evo == copy
	# mset
	copy = items.copy(); copy[m1], copy[m2] = m1, m2
	evo = seq.evolver(); evo.mset(m1, m1, m2, m2)
	assert seq.mset(m1, m1, m2, m2) == seq.mset((m1, m1), (m2, m2)) \
		== seq.set(m1, m1).set(m2, m2) == evo == copy
	# insert
	copy = items.copy(); copy.insert(m1 + 1, m2 + 1); copy.insert(m1, m2)
	evo = seq.evolver(); evo.insert(m1 + 1, m2 + 1); evo.insert(m1, m2)
	assert seq.insert(m1 + 1, m2 + 1).insert(m1, m2) == evo == copy
	# append
	assert seq.append(m1) == seq.appendright(m1) == items + [m1]
	assert seq.appendleft(m1) == [m1] + items

@given(st.lists(st.integers(), min_size=1), st.integers(), st.integers())
def test_lenses(items:List[int], n1:int, n2:int):
	seq = psequence(items)
	m1, m2 = sorted(n % len(items) for n in [n1, n2])
	getter = lens[m1].get()
	setter = lens[m1].set(m2)
	remove = lens.Contains(m1).set(False)
	adder = lens.Contains(m1).set(True)
	each = lens.Each().modify(lambda x: x * 2)
	assert getter(seq) == getter(items)
	assert setter(seq) == setter(items.copy())
	assert remove(seq) == remove(items.copy())
	assert adder(seq) == adder(items.copy())
	assert each(seq) == each(items.copy())
