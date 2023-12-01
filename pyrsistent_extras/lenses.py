from __future__ import annotations

from typing import *

from ._util import Comparable, compare_next, compare_iter, \
	sphinx_build, trace, NOTHING, \
	keys_from_items, values_from_items, items_from_items

from ._pheap import PMinHeap, pminheap, PMaxHeap, pmaxheap
from ._psortedmap import PSortedMap, psortedmap
from ._psequence import PSequence, psequence

from lenses import hooks

T = TypeVar('T')
K = TypeVar('K', bound=Comparable)
V = TypeVar('V')

@hooks.setitem.register(PSequence)
def _psequence_setitem(self:PSequence[T], index:int, value:T) -> PSequence[T]:
	return self.set(index, value)
@hooks.contains_add.register(PSequence)
def _psequence_contains_add(self:PSequence[T], item:T) -> PSequence[T]:
	return self.append(item)
@hooks.contains_remove.register(PSequence)
def _psequence_contains_remove(self:PSequence[T], item:T) -> PSequence[T]:
	return self.remove(item)
@hooks.from_iter.register(PSequence)
def _psequence_contains_from_iter(items:Iterator[T]) -> PSequence[T]:
	return psequence(items)

@hooks.setitem.register(PMinHeap)
def _pminheap_setitem(self:PMinHeap[K,V], key:K, value:V) -> PMinHeap[K,V]:
	return self.push(key, value)
@hooks.contains_add.register(PMinHeap)
def _pminheap_contains_add(self:PMinHeap[K,None], key:K) -> PMinHeap[K,None]:
	return self.push(key, None)
@hooks.contains_remove.register(PMinHeap)
def _pminheap_contains_remove(self:PMinHeap[K,Any], key:K) -> PMinHeap[K,Any]:
	return pminheap((k, v) for k, v in self.items() if k != key)
@hooks.to_iter.register(PMinHeap)
def _pminheap_contains_to_iter(self:PMinHeap[K,V]) -> Iterator[Tuple[K,V]]:
	return iter(self.items())
@hooks.from_iter.register(PMinHeap)
def _pminheap_contains_from_iter(items:Iterator[Tuple[K,V]]) -> PMinHeap[K,V]:
	return pminheap(items)

@hooks.setitem.register(PMaxHeap)
def _pmaxheap_setitem(self:PMaxHeap[K,V], key:K, value:V) -> PMaxHeap[K,V]:
	return self.push(key, value)
@hooks.contains_add.register(PMaxHeap)
def _pmaxheap_contains_add(self:PMaxHeap[K,None], key:K) -> PMaxHeap[K,None]:
	return self.push(key, None)
@hooks.contains_remove.register(PMaxHeap)
def _pmaxheap_contains_remove(self:PMaxHeap[K,Any], key:K) -> PMaxHeap[K,Any]:
	return pmaxheap((k, v) for k, v in self.items() if k != key)
@hooks.to_iter.register(PMaxHeap)
def _pmaxheap_contains_to_iter(self:PMaxHeap[K,V]) -> Iterator[Tuple[K,V]]:
	return iter(self.items())
@hooks.from_iter.register(PMaxHeap)
def _pmaxheap_contains_from_iter(items:Iterator[Tuple[K,V]]) -> PMaxHeap[K,V]:
	return pmaxheap(items)

