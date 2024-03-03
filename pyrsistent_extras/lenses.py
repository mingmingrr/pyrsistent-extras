from __future__ import annotations

from typing import *

from ._utility import Comparable

from ._pheap import PMinHeap, pminheap, PMaxHeap, pmaxheap
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
	return psequence(i for i in self if item != i)
@hooks.from_iter.register(PSequence)
def _psequence_from_iter(self:PSequence[T], items:Iterator[T]) -> PSequence[T]:
	return psequence(items)

@hooks.contains_add.register(PMinHeap)
def _pminheap_contains_add(self:PMinHeap[K,None], key:K) -> PMinHeap[K,None]:
	return cast(PMinHeap, self.push(key, None))
@hooks.contains_remove.register(PMinHeap)
def _pminheap_contains_remove(self:PMinHeap[K,Any], key:K) -> PMinHeap[K,Any]:
	return pminheap((k, v) for k, v in self.items() if key != k)
@hooks.to_iter.register(PMinHeap)
def _pminheap_to_iter(self:PMinHeap[K,V]) -> Iterator[Tuple[K,V]]:
	return iter(self.items())
@hooks.from_iter.register(PMinHeap)
def _pminheap_from_iter(self:PMinHeap[Any,Any], items:Iterator[Tuple[K,V]]) -> PMinHeap[K,V]:
	return pminheap(items)

@hooks.contains_add.register(PMaxHeap)
def _pmaxheap_contains_add(self:PMaxHeap[K,None], key:K) -> PMaxHeap[K,None]:
	return cast(PMaxHeap, self.push(key, None))
@hooks.contains_remove.register(PMaxHeap)
def _pmaxheap_contains_remove(self:PMaxHeap[K,Any], key:K) -> PMaxHeap[K,Any]:
	return pmaxheap((k, v) for k, v in self.items() if key != k)
@hooks.to_iter.register(PMaxHeap)
def _pmaxheap_to_iter(self:PMaxHeap[K,V]) -> Iterator[Tuple[K,V]]:
	return iter(self.items())
@hooks.from_iter.register(PMaxHeap)
def _pmaxheap_from_iter(self:PMaxHeap[Any,Any], items:Iterator[Tuple[K,V]]) -> PMaxHeap[K,V]:
	return pmaxheap(items)

