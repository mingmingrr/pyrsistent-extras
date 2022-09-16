from __future__ import annotations

from typing import Collection, Iterable, Iterator, Hashable, \
	ClassVar, TypeVar, Generic, Optional, Callable, Tuple, Any, Union, cast
from abc import abstractmethod

import itertools
import operator

from .util import Comparable, compare_single, compare_next, compare_iter

T = TypeVar('T')
K = TypeVar('K', bound=Comparable)
V = TypeVar('V')

class Tree(Generic[K,V]):
	__slots__ = ('_key', '_value', '_child', '_sibling')

	_key: K
	_value: V
	_child: Optional[Tree[K,V]]
	_sibling: Optional[Tree[K,V]]

	def __new__(cls, key:K, value:V,
			child:Optional[Tree[K,V]], sibling:Optional[Tree[K,V]]):
		self = super().__new__(cls)
		self._key = key
		self._value = value
		self._child = child
		self._sibling = sibling
		return self

	def merge(self, other:Optional[Tree[K,V]], down:bool) -> Tree[K,V]:
		if other is None: return self
		if (self._key < other._key) == down:
			self, other = other, self
		assert self._sibling is None
		assert other._sibling is None
		other = Tree(other._key, other._value, other._child, self._child)
		return Tree(self._key, self._value, other, None)

class Forest(Generic[K,V]):
	__slots__ = ('_order', '_tree', '_next')

	_order: int
	_tree: Tree[K,V]
	_next: Optional[Forest[K,V]]

	def __new__(cls, order:int, tree:Tree[K,V], next:Optional[Forest[K,V]]):
		self = super().__new__(cls)
		self._order = order
		self._tree = tree
		self._next = next
		return self

	def push(self:Optional[Forest[K,V]], down:bool,
			order:int, tree:Tree[K,V]) -> Forest[K,V]:
		if self is None:
			return Forest(order, tree, None)
		if order < self._order:
			return Forest(order, tree, self)
		if order > self._order:
			return Forest(self._order, self._tree,
				Forest.push(self._next, down, order, tree))
		return Forest.push(self._next, down, order + 1,
			self._tree.merge(tree, down))

	def popbranch(self:Forest[K,V], down:bool) \
			-> Tuple[int,Optional[Tree[K,V]],K,V,Optional[Forest[K,V]]]:
		assert self._tree._sibling is None
		if self._next is None:
			return self._order - 1, self._tree._child, \
				self._tree._key, self._tree._value, None
		order, branch, key, value, forest = self._next.popbranch(down)
		if (self._tree._key < key) != down:
			return self._order - 1, self._tree._child, \
				self._tree._key, self._tree._value, self._next
		while order >= self._order:
			assert branch is not None
			tree = Tree(branch._key, branch._value, branch._child, None)
			forest = Forest.push(forest, down, order, tree)
			order, branch = order - 1, branch._sibling
		return order, branch, key, value, \
			Forest.push(forest, down, self._order, self._tree)

	def pop(self:Forest[K,V], down:bool) -> Tuple[K,V,Optional[Forest[K,V]]]:
		order, branch, key, value, forest = self.popbranch(down)
		while branch is not None:
			tree = Tree(branch._key, branch._value, branch._child, None)
			forest = Forest.push(forest, down, order, tree)
			order, branch = order - 1, branch._sibling
		return key, value, forest

	def merge(self:Optional[Forest[K,V]], other:Optional[Forest[K,V]],
			down:bool) -> Optional[Forest[K,V]]:
		if self is None: return other
		if other is None: return self
		if self._order < other._order:
			return Forest(self._order, self._tree,
				Forest.merge(self._next, other, down))
		if self._order > other._order:
			return Forest(other._order, other._tree,
				Forest.merge(other._next, self, down))
		forest = Forest.merge(self._next, other._next, down)
		return Forest.push(forest, down, self._order + 1,
			self._tree.merge(other._tree, down))

class HeapView(Generic[T,K,V], Collection[T]):
	__slots__ = ('_queue', '_sorted')

	_queue: Heap[K,V]
	_sorted: bool

	def __new__(cls, queue:Heap[K,V], sorted:bool):
		self = super().__new__(cls)
		self._queue = queue
		self._sorted = sorted
		return self

	def __contains__(self, item):
		return any(item == i for i in self)

	def __len__(self):
		return self._queue._size

	def _iter_unsorted(self) -> Iterator[Tuple[K,V]]:
		if self._queue._size == 0: return
		yield self._queue._key, self._queue._value
		forest = self._queue._forest
		stack:list[Tree[K,V]] = []
		while forest is not None:
			stack.append(forest._tree)
			while stack:
				item = stack.pop()
				if isinstance(item, Tree):
					yield item._key, item._value
					if item._sibling is not None:
						stack.append(item._sibling)
					if item._child is not None:
						stack.append(item._child)
			forest = forest._next

	def _iter_sorted(self) -> Iterator[Tuple[K,V]]:
		queue = self._queue
		while queue._size > 0:
			key, value, queue = queue.pop()
			yield key, value

	def _iter(self) -> Iterator[Tuple[K,V]]:
		if self._sorted:
			return self._iter_sorted()
		return self._iter_unsorted()

	@abstractmethod
	def __iter__(self) -> Iterator[T]: # pragma: no cover
		return NotImplemented

class HeapItems(HeapView[Tuple[K,V],K,V]):
	def __iter__(self) -> Iterator[Tuple[K,V]]:
		return super()._iter()

class HeapKeys(HeapView[K,K,V]):
	def __iter__(self) -> Iterator[K]:
		return (k for k, v in super()._iter())

class HeapValues(HeapView[V,K,V]):
	def __iter__(self) -> Iterator[V]:
		return (v for k, v in super()._iter())

class Heap(Generic[K,V], Collection[K], Hashable):
	__slots__ = ('_size', '_key', '_value', '_forest')

	_size: int
	_key: K
	_value: V
	_forest: Optional[Forest[K,V]]

	_name: ClassVar[str] = cast(Any, None)
	_down: ClassVar[bool] = cast(Any, None)
	_empty: ClassVar[Heap[Any,Any]] = cast(Any, None)

	def __new__(cls, size:int, key:K, value:V, forest:Optional[Forest[K,V]]):
		self = super().__new__(cls)
		self._size = size
		self._key = key
		self._value = value
		self._forest = forest
		return self

	def push(self, key:K, value:V=cast(V,None)) -> Heap[K,V]:
		if self._size == 0:
			return type(self)(1, key, value, None)
		if (key < self._key) != self._down:
			k1, v1, k2, v2 = key, value, self._key, self._value
		else:
			k2, v2, k1, v1 = key, value, self._key, self._value
		return type(self)(self._size + 1, k1, v1,
			Forest.push(self._forest, self._down, 0, Tree(k2, v2, None, None)))

	def pop(self) -> Tuple[K,V,Heap[K,V]]:
		if self._size == 0:
			raise IndexError('pop from empty heap')
		if self._forest is None:
			return self._key, self._value, self._empty
		key, value, forest = self._forest.pop(self._down)
		return self._key, self._value, type(self)(self._size - 1, key, value, forest)

	def merge(self, other:HeapLike[K,V]) -> Heap[K,V]:
		other = self._fromitems(other)
		if self._size == 0: return other
		if other._size == 0: return self
		if (self._key < other._key) == self._down:
			self, other = other, self
		forest = Forest.merge(self._forest, other._forest, self._down)
		forest = Forest.push(forest, self._down, 0,
			Tree(other._key, other._value, None, None))
		return type(self)(self._size + other._size, self._key, self._value, forest)

	__add__ = merge

	def peek(self):
		if self._size == 0:
			raise IndexError('min of empty heap')
		return self._key, self._value

	def __len__(self):
		return self._size

	def __bool__(self):
		return self._size != 0

	def __contains__(self, key):
		return key in HeapKeys(self, False)

	def __repr__(self):
		return '{}({})'.format(self._name, list(self.items()))

	def items(self, sorted:bool=True):
		return HeapItems(self, sorted)

	def keys(self, sorted:bool=True):
		return HeapKeys(self, sorted)

	def values(self, sorted:bool=True):
		return HeapValues(self, sorted)

	def __iter__(self):
		return iter(HeapKeys(self))

	@classmethod
	def _fromitems(cls, items:HeapLike[K,V]) -> Heap[K,V]:
		if isinstance(items, Heap):
			if items._down == cls._down: return items
			return cls._fromitems(items.items(sorted=False))
		size, forest = 0, None
		for key, value in items:
			forest = Forest.push(forest, cls._down, 0,
				Tree(key, value, None, None))
			size += 1
		if forest is None:
			return cls._empty
		key, value, forest = forest.pop(cls._down)
		return cls(size, key, value, forest)

	def _iter_sort_values(self) -> Iterator[Tuple[K,V]]:
		for k, vs in itertools.groupby(self.items(), key=operator.itemgetter(0)):
			yield from sorted(vs, key=operator.itemgetter(1))

	def _iter_group_values(self) -> Iterator[Tuple[K,Iterator[Tuple[K,V]]]]:
		return itertools.groupby(self.items(), key=operator.itemgetter(0))

	def _compare(self, other:Heap[K,V], equality:bool) -> int:
		if not isinstance(other, Heap):
			return NotImplemented
		if self._down != other._down:
			return NotImplemented
		if equality:
			if self is other:
				return 0
			if len(self) != len(other):
				return 1
		try:
			return compare_iter(self._iter_sort_values(),
				other._iter_sort_values(), equality)
		except TypeError as err:
			if not equality: raise
		xiter = self._iter_group_values()
		yiter = other._iter_group_values()
		while True:
			n = compare_next(xiter, yiter)
			if isinstance(n, int): return n
			if n[0][0] != n[1][0]: return 1
			xvalues = [v for _, v in n[0][1]]
			yvalues = [v for _, v in n[1][1]]
			if len(xvalues) != len(yvalues): return 1
			for x in xvalues:
				try:
					yvalues.remove(x)
				except ValueError:
					return 1
			assert not yvalues

	def __eq__(self, other):
		result = self._compare(other, True)
		if result is NotImplemented: return result
		return result == 0
	def __ne__(self, other):
		result = self._compare(other, True)
		if result is NotImplemented: return result
		return result != 0
	def __gt__(self, other):
		result = self._compare(other, False)
		if result is NotImplemented: return result
		return result > 0
	def __ge__(self, other):
		result = self._compare(other, False)
		if result is NotImplemented: return result
		return result >= 0
	def __lt__(self, other):
		result = self._compare(other, False)
		if result is NotImplemented: return result
		return result < 0
	def __le__(self, other):
		result = self._compare(other, False)
		if result is NotImplemented: return result
		return result <= 0

	def __hash__(self):
		h = hash(self._name)
		for k, vs in itertools.groupby(self.items(), key=operator.itemgetter(0)):
			h = hash((h, k, tuple(sorted(vs))))
		return h

	def __reduce__(self):
		return globals()[self._name], (tuple(self.items(False)),)

HeapLike = Union[Heap[K,V],Iterable[Tuple[K,V]]]

def fromkeys(func):
	def inner(items:Iterable[K]) -> Heap[K,None]:
		return func((item, None) for item in items)
	return inner

class PMinHeap(Heap[K,V]):
	_name: ClassVar[str] = 'pminheap'
	_down: ClassVar[bool] = False
	_empty: ClassVar[PMinHeap[Any,Any]] = cast(Any, None)
PMinHeap._empty = PMinHeap(0, None, None, None) # type: ignore

def pminheap(items:HeapLike[K,V]=PMinHeap._empty) -> Heap[K,V]:
	return PMinHeap._fromitems(items)
setattr(pminheap, 'fromkeys', fromkeys(pminheap))

def hl(*items:Tuple[K,V]) -> Heap[K,V]:
	return pminheap(items)

class PMaxHeap(Heap[K,V]):
	_name: ClassVar[str] = 'pmaxheap'
	_down: ClassVar[bool] = True
	_empty: ClassVar[PMaxHeap[Any,Any]] = cast(Any, None)
PMaxHeap._empty = PMaxHeap(0, None, None, None) # type: ignore

def pmaxheap(items:HeapLike[K,V]=PMaxHeap._empty) -> Heap[K,V]:
	return PMaxHeap._fromitems(items)
setattr(pmaxheap, 'fromkeys', fromkeys(pmaxheap))

def hg(*items:Tuple[K,V]) -> Heap[K,V]:
	return pmaxheap(items)

__all__ = ('hl', 'pminheap', 'PMinHeap', 'hg', 'pmaxheap', 'PMaxHeap')
