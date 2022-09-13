from __future__ import annotations

from typing import Collection, Iterable, Iterator, \
	ClassVar, TypeVar, Generic, Optional, Tuple, Any, Union, cast
from abc import abstractmethod

from .util import Comparable

T = TypeVar('T')
K = TypeVar('K', bound=Comparable)
V = TypeVar('V')

class Branch(Generic[K,V]):
	__slots__ = ('tree', 'next')

	tree: Tree[K,V]
	next: Optional[Branch[K,V]]

	def __new__(cls, tree:Tree[K,V], next:Optional[Branch[K,V]]):
		self = super().__new__(cls)
		self.tree = tree
		self.next = next
		return self

	def _check(self:Optional[Branch[K,V]], key:K, order:int) -> int:
		if self is None:
			assert order == -1
			return 0
		else:
			tsize = self.tree._check(key, order)
			bsize = Branch._check(self.next, key, order - 1)
			return tsize + bsize

	def pprint(self:Optional[Branch[K,V]], indent:int):
		if self is None: return
		self.tree.pprint(indent)
		Branch.pprint(self.next, indent)

class Tree(Generic[K,V]):
	__slots__ = ('key', 'value', 'branch')

	key: K
	value: V
	branch: Optional[Branch[K,V]]

	def __new__(cls, key:K, value:V, branch:Optional[Branch[K,V]]):
		self = super().__new__(cls)
		self.key = key
		self.value = value
		self.branch = branch
		return self

	def _check(self, key:K, order:int) -> int:
		assert self.key >= key
		assert self.order() == order
		size = Branch._check(self.branch, self.key, order - 1)
		return size + 1

	def merge(self, other:Optional[Tree[K,V]]) -> Tree[K,V]:
		if other is None: return self
		if self.key > other.key:
			self, other = other, self
		return Tree(self.key, self.value,
			Branch(other, self.branch))

	def pprint(self:Optional[Tree[K,V]], indent:int):
		if self is None: return
		print('  ' * indent, 'Tree', self.key, self.value)
		Branch.pprint(self.branch, indent + 1)

	def order(self) -> int:
		order, branch = 0, self.branch
		while branch is not None:
			order, branch = order + 1, branch.next
		return order

class Forest(Generic[K,V]):
	__slots__ = ('order', 'tree', 'next')

	order: int
	tree: Tree[K,V]
	next: Optional[Forest[K,V]]

	def __new__(cls, order:int, tree:Tree[K,V], next:Optional[Forest[K,V]]):
		self = super().__new__(cls)
		self.order = order
		self.tree = tree
		self.next = next
		return self

	def _check(self:Optional[Forest[K,V]], key:K) -> int:
		if self is None: return 0
		tsize = self.tree._check(key, self.order)
		fsize = Forest._check(self.next, key)
		return tsize + fsize

	def insert(self:Optional[Forest[K,V]], order:int, tree:Tree[K,V]) -> Forest[K,V]:
		if self is None:
			return Forest(order, tree, None)
		if order < self.order:
			return Forest(order, tree, self)
		if order > self.order:
			return Forest(self.order, self.tree,
				Forest.insert(self.next, order, tree))
		return Forest.insert(self.next, order + 1, self.tree.merge(tree))

	def pprint(self:Optional[Forest[K,V]], indent:int):
		if self is None: return
		print('  ' * indent, f'Forest r{self.order}')
		self.tree.pprint(indent + 1)
		Forest.pprint(self.next, indent)

	def _extract(self:Forest[K,V]) \
			-> Tuple[int,Optional[Branch[K,V]],K,V,Optional[Forest[K,V]]]:
		if self.next is None:
			return self.order - 1, self.tree.branch, \
				self.tree.key, self.tree.value, None
		order, branch, key, value, forest = self.next._extract()
		if self.tree.key < key:
			return self.order - 1, self.tree.branch, \
				self.tree.key, self.tree.value, self.next
		while order >= self.order:
			assert branch is not None
			forest = Forest.insert(forest, order, branch.tree)
			order, branch = order - 1, branch.next
		return order, branch, key, value, \
			Forest.insert(forest, self.order, self.tree)

	def extract(self:Forest[K,V]) -> Tuple[K,V,Optional[Forest[K,V]]]:
		order, branch, key, value, forest = self._extract()
		while branch is not None:
			forest = Forest.insert(forest, order, branch.tree)
			order, branch = order - 1, branch.next
		return key, value, forest

	def merge(self:Optional[Forest[K,V]], other:Optional[Forest[K,V]]) \
			-> Optional[Forest[K,V]]:
		if self is None: return other
		if other is None: return self
		if self.order < other.order:
			return Forest(self.order, self.tree,
				Forest.merge(self.next, other))
		if self.order > other.order:
			return Forest(other.order, other.tree,
				Forest.merge(other.next, self))
		forest = Forest.merge(self.next, other.next)
		return Forest.insert(forest, self.order + 1,
			self.tree.merge(other.tree))

class QueueView(Generic[T,K,V], Collection[T]):
	__slots__ = ('queue', 'sorted')

	queue: Queue[K,V]
	sorted: bool

	def __new__(cls, queue:Queue[K,V], sorted:bool):
		self = super().__new__(cls)
		self.queue = queue
		self.sorted = sorted
		return self

	def __contains__(self, item):
		return any(item == i for i in self)

	def __len__(self):
		return self.queue.size

	def _iter_unsorted(self) -> Iterator[Tuple[K,V]]:
		if self.queue.size == 0: return
		yield self.queue.key, self.queue.value
		forest = self.queue.forest
		stack:list[Union[Branch[K,V],Tree[K,V]]] = []
		while forest is not None:
			stack.append(forest.tree)
			while stack:
				item = stack.pop()
				if isinstance(item, Tree):
					yield item.key, item.value
					if item.branch is not None:
						stack.append(item.branch)
				else:
					if item.next is not None:
						stack.append(item.next)
					stack.append(item.tree)
			forest = forest.next

	def _iter_sorted(self) -> Iterator[Tuple[K,V]]:
		queue = self.queue
		while queue.size > 0:
			key, value, queue = queue.extract()
			yield key, value

	def _iter(self) -> Iterator[Tuple[K,V]]:
		if self.sorted:
			return self._iter_sorted()
		return self._iter_unsorted()

	@abstractmethod
	def __iter__(self) -> Iterator[T]:
		return NotImplemented

class QueueItems(QueueView[Tuple[K,V],K,V]):
	def __iter__(self) -> Iterator[Tuple[K,V]]:
		return super()._iter()

class QueueKeys(QueueView[K,K,V]):
	def __iter__(self) -> Iterator[K]:
		return (k for k, v in super()._iter())

class QueueValues(QueueView[V,K,V]):
	def __iter__(self) -> Iterator[V]:
		return (v for k, v in super()._iter())

class Queue(Generic[K,V]):
	__slots__ = ('down', 'size', 'key', 'value', 'forest')

	down: bool
	size: int
	key: K
	value: V
	forest: Optional[Forest[K,V]]

	def __new__(cls, down:bool, size:int,
			key:K, value:V, forest:Optional[Forest[K,V]]):
		self = super().__new__(cls)
		self.down = down
		self.size = size
		self.key = key
		self.value = value
		self.forest = forest
		return self

	def _check(self):
		if self.size == 0:
			assert self.key is None
			assert self.value is None
			assert self.forest is None
		else:
			size = Forest._check(self.forest, self.key)
			assert self.size == size + 1

	def insert(self, key:K, value:V=cast(V,None)) -> Queue[K,V]:
		if self.size == 0:
			return Queue(False, 1, key, value, None)
		if key < self.key:
			k1, v1, k2, v2 = key, value, self.key, self.value
		else:
			k2, v2, k1, v1 = key, value, self.key, self.value
		return Queue(False, self.size + 1, k1, v1,
			Forest.insert(self.forest, 0, Tree(k2, v2, None)))

	def _pprint(self):
		print('Queue', self.size, self.key, self.value)
		Forest.pprint(self.forest, 0)

	def extract(self) -> Tuple[K,V,Queue[K,V]]:
		if self.size == 0:
			raise IndexError('extract from empty queue')
		if self.forest is None:
			return self.key, self.value, _EMPTY_QUEUE
		key, value, forest = self.forest.extract()
		return self.key, self.value, Queue(False, self.size - 1, key, value, forest)

	def _merge(self, other:Queue[K,V]) -> Queue[K,V]:
		if self.size == 0: return other
		if other.size == 0: return self
		if self.key >= other.key:
			self, other = other, self
		forest = Forest.merge(self.forest, other.forest)
		forest = Forest.insert(forest, 0, Tree(other.key, other.value, None))
		return Queue(False, self.size + other.size, self.key, self.value, forest)

	def merge(self, other:Union[Queue[K,V],Iterable[Tuple[K,V]]]) -> Queue[K,V]:
		return self._merge(queue(other))

	__add__ = merge

	def peek(self):
		if self.size == 0:
			raise IndexError('min of empty queue')
		return self.key, self.value

	def __len__(self):
		return self.size

	def __contains__(self, key):
		return key in QueueKeys(self, False)

	def __repr__(self):
		return 'queue({})'.format(list(self.items()))

	def items(self, sorted=True):
		return QueueItems(self, sorted)

	def keys(self, sorted=True):
		return QueueKeys(self, sorted)

	def values(self, sorted=True):
		return QueueValues(self, sorted)

_EMPTY_QUEUE:Queue[Any,Any] = Queue(False, 0, None, None, None)

def queue(items:Union[Queue[K,V],Iterable[Tuple[K,V]]]=_EMPTY_QUEUE) -> Queue[K,V]:
	if isinstance(items, Queue):
		return items
	size, forest = 0, None
	for key, value in items:
		forest = Forest.insert(forest, 0, Tree(key, value, None))
		size += 1
	if forest is None:
		return _EMPTY_QUEUE
	key, value, forest = forest.extract()
	return Queue(False, size, key, value, forest)

def q(*items:Tuple[K,V]) -> Queue[K,V]:
	return queue(items)

__all__ = ('q', 'queue', 'Queue')
