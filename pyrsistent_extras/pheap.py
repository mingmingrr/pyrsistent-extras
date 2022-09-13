from __future__ import annotations

from typing import Collection, Iterable, Iterator, \
	ClassVar, TypeVar, Generic, Optional, Callable, Tuple, Any, Union, cast
from abc import abstractmethod

from .util import Comparable

T = TypeVar('T')
K = TypeVar('K', bound=Comparable)
V = TypeVar('V')

class Branch(Generic[K,V]):
	__slots__ = ('_tree', '_next')

	_tree: Tree[K,V]
	_next: Optional[Branch[K,V]]

	def __new__(cls, tree:Tree[K,V], next:Optional[Branch[K,V]]):
		self = super().__new__(cls)
		self._tree = tree
		self._next = next
		return self

	def _check(self:Optional[Branch[K,V]], key:K, order:int) -> int:
		if self is None:
			assert order == -1
			return 0
		else:
			tsize = self._tree._check(key, order)
			bsize = Branch._check(self._next, key, order - 1)
			return tsize + bsize

	def pprint(self:Optional[Branch[K,V]], indent:int):
		if self is None: return
		self._tree.pprint(indent)
		Branch.pprint(self._next, indent)

class Tree(Generic[K,V]):
	__slots__ = ('_key', '_value', '_branch')

	_key: K
	_value: V
	_branch: Optional[Branch[K,V]]

	def __new__(cls, key:K, value:V, branch:Optional[Branch[K,V]]):
		self = super().__new__(cls)
		self._key = key
		self._value = value
		self._branch = branch
		return self

	def _check(self, key:K, order:int) -> int:
		assert self._key >= key
		assert self.order() == order
		size = Branch._check(self._branch, self._key, order - 1)
		return size + 1

	def merge(self, other:Optional[Tree[K,V]], down:bool) -> Tree[K,V]:
		if other is None: return self
		if (self._key < other._key) == down:
			self, other = other, self
		return Tree(self._key, self._value,
			Branch(other, self._branch))

	def pprint(self:Optional[Tree[K,V]], indent:int):
		if self is None: return
		print('  ' * indent, 'Tree', self._key, self._value)
		Branch.pprint(self._branch, indent + 1)

	def order(self) -> int:
		order, branch = 0, self._branch
		while branch is not None:
			order, branch = order + 1, branch._next
		return order

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

	def _check(self:Optional[Forest[K,V]], key:K) -> int:
		if self is None: return 0
		tsize = self._tree._check(key, self._order)
		fsize = Forest._check(self._next, key)
		return tsize + fsize

	def insert(self:Optional[Forest[K,V]], down:bool,
			order:int, tree:Tree[K,V]) -> Forest[K,V]:
		if self is None:
			return Forest(order, tree, None)
		if order < self._order:
			return Forest(order, tree, self)
		if order > self._order:
			return Forest(self._order, self._tree,
				Forest.insert(self._next, down, order, tree))
		return Forest.insert(self._next, down, order + 1,
			self._tree.merge(tree, down))

	def pprint(self:Optional[Forest[K,V]], indent:int):
		if self is None: return
		print('  ' * indent, f'Forest r{self._order}')
		self._tree.pprint(indent + 1)
		Forest.pprint(self._next, indent)

	def _extract(self:Forest[K,V], down:bool) \
			-> Tuple[int,Optional[Branch[K,V]],K,V,Optional[Forest[K,V]]]:
		if self._next is None:
			return self._order - 1, self._tree._branch, \
				self._tree._key, self._tree._value, None
		order, branch, key, value, forest = self._next._extract(down)
		if (self._tree._key < key) != down:
			return self._order - 1, self._tree._branch, \
				self._tree._key, self._tree._value, self._next
		while order >= self._order:
			assert branch is not None
			forest = Forest.insert(forest, down, order, branch._tree)
			order, branch = order - 1, branch._next
		return order, branch, key, value, \
			Forest.insert(forest, down, self._order, self._tree)

	def extract(self:Forest[K,V], down:bool) -> Tuple[K,V,Optional[Forest[K,V]]]:
		order, branch, key, value, forest = self._extract(down)
		while branch is not None:
			forest = Forest.insert(forest, down, order, branch._tree)
			order, branch = order - 1, branch._next
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
		return Forest.insert(forest, down, self._order + 1,
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
		stack:list[Union[Branch[K,V],Tree[K,V]]] = []
		while forest is not None:
			stack.append(forest._tree)
			while stack:
				item = stack.pop()
				if isinstance(item, Tree):
					yield item._key, item._value
					if item._branch is not None:
						stack.append(item._branch)
				else:
					if item._next is not None:
						stack.append(item._next)
					stack.append(item._tree)
			forest = forest._next

	def _iter_sorted(self) -> Iterator[Tuple[K,V]]:
		queue = self._queue
		while queue._size > 0:
			key, value, queue = queue.extract()
			yield key, value

	def _iter(self) -> Iterator[Tuple[K,V]]:
		if self._sorted:
			return self._iter_sorted()
		return self._iter_unsorted()

	@abstractmethod
	def __iter__(self) -> Iterator[T]:
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

class Heap(Generic[K,V]):
	__slots__ = ('_size', '_key', '_value', '_forest')

	_size: int
	_key: K
	_value: V
	_forest: Optional[Forest[K,V]]

	_down: ClassVar[bool] = cast(Any, None)
	_empty: ClassVar[Heap[Any,Any]] = cast(Any, None)

	def __new__(cls, size:int, key:K, value:V, forest:Optional[Forest[K,V]]):
		self = super().__new__(cls)
		self._size = size
		self._key = key
		self._value = value
		self._forest = forest
		return self

	def _check(self):
		if self._size == 0:
			assert self._key is None
			assert self._value is None
			assert self._forest is None
		else:
			size = Forest._check(self._forest, self._key)
			assert self._size == size + 1

	def insert(self, key:K, value:V=cast(V,None)) -> Heap[K,V]:
		if self._size == 0:
			return type(self)(1, key, value, None)
		if (key < self._key) != self._down:
			k1, v1, k2, v2 = key, value, self._key, self._value
		else:
			k2, v2, k1, v1 = key, value, self._key, self._value
		return type(self)(self._size + 1, k1, v1,
			Forest.insert(self._forest, self._down, 0, Tree(k2, v2, None)))

	def _pprint(self):
		print('Heap', self._size, self._key, self._value)
		Forest.pprint(self._forest, 0)

	def extract(self) -> Tuple[K,V,Heap[K,V]]:
		if self._size == 0:
			raise IndexError('extract from empty heap')
		if self._forest is None:
			return self._key, self._value, self._empty
		key, value, forest = self._forest.extract(self._down)
		return self._key, self._value, type(self)(self._size - 1, key, value, forest)

	def _merge(self, other:Heap[K,V]) -> Heap[K,V]:
		if self._size == 0: return other
		if other._size == 0: return self
		if (self._key < other._key) == self._down:
			self, other = other, self
		forest = Forest.merge(self._forest, other._forest, self._down)
		forest = Forest.insert(forest, self._down, 0,
			Tree(other._key, other._value, None))
		return type(self)(self._size + other._size, self._key, self._value, forest)

	def merge(self, other:HeapLike[K,V]) -> Heap[K,V]:
		return self._merge(self._fromitems(other))

	__add__ = merge

	def peek(self):
		if self._size == 0:
			raise IndexError('min of empty heap')
		return self._key, self._value

	def __len__(self):
		return self._size

	def __contains__(self, key):
		return key in HeapKeys(self, False)

	def __repr__(self):
		name = 'maxheap' if self._down else 'minheap'
		return '{}({})'.format(name, list(self.items()))

	def items(self, sorted:bool=True):
		return HeapItems(self, sorted)

	def keys(self, sorted:bool=True):
		return HeapKeys(self, sorted)

	def values(self, sorted:bool=True):
		return HeapValues(self, sorted)

	@classmethod
	def _fromitems(cls, items:HeapLike[K,V]) -> Heap[K,V]:
		if isinstance(items, Heap):
			if isinstance(items, cls): return items
			return cls._fromitems(items.items())
		size, forest = 0, None
		for key, value in items:
			forest = Forest.insert(forest, cls._down, 0, Tree(key, value, None))
			size += 1
		if forest is None:
			return cls._empty
		key, value, forest = forest.extract(cls._down)
		return cls(size, key, value, forest)

HeapLike = Union[Heap[K,V],Iterable[Tuple[K,V]]]

class MinHeap(Heap[K,V]):
	_down: ClassVar[bool] = False
	_empty: ClassVar[MinHeap[Any,Any]] = cast(Any, None)
MinHeap._empty = MinHeap(0, None, None, None) # type: ignore

def minheap(items:HeapLike[K,V]=MinHeap._empty) -> Heap[K,V]:
	return MinHeap._fromitems(items)

def hl(*items:Tuple[K,V]) -> Heap[K,V]:
	return minheap(items)

class MaxHeap(Heap[K,V]):
	_down: ClassVar[bool] = True
	_empty: ClassVar[MaxHeap[Any,Any]] = cast(Any, None)
MaxHeap._empty = MaxHeap(0, None, None, None) # type: ignore

def maxheap(items:HeapLike[K,V]=MaxHeap._empty) -> Heap[K,V]:
	return MaxHeap._fromitems(items)

def hg(*items:Tuple[K,V]) -> Heap[K,V]:
	return minheap(items)

__all__ = ('hl', 'minheap', 'MinHeap', 'hg', 'maxheap', 'MaxHeap')
