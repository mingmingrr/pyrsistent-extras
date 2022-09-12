from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, TypeVar, Generic, Optional, Any, Union, cast
from collections.abc import Collection, Iterable, Iterator
from abc import abstractmethod

from .util import Comparable

T = TypeVar('T')
K = TypeVar('K', bound=Comparable)
V = TypeVar('V')

@dataclass(slots=True, frozen=True)
class Branch(Generic[K,V]):
	tree: Tree[K,V]
	next: Optional[Branch[K,V]]

	def check(self:Optional[Branch[K,V]], key:K, order:int) -> int:
		if self is None:
			assert order == -1
			return 0
		else:
			tsize = self.tree.check(key, order)
			bsize = Branch.check(self.next, key, order - 1)
			return tsize + bsize

	def pprint(self:Optional[Branch[K,V]], indent:int):
		if self is None: return
		self.tree.pprint(indent)
		Branch.pprint(self.next, indent)

@dataclass(slots=True, frozen=True)
class Tree(Generic[K,V]):
	key: K
	value: V
	branch: Optional[Branch[K,V]]

	def check(self, key:K, order:int) -> int:
		assert self.key >= key
		assert self.order() == order
		size = Branch.check(self.branch, self.key, order - 1)
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

@dataclass(slots=True, frozen=True)
class Forest(Generic[K,V]):
	order: int
	tree: Tree[K,V]
	next: Optional[Forest[K,V]]

	def check(self:Optional[Forest[K,V]], key:K) -> int:
		if self is None: return 0
		tsize = self.tree.check(key, self.order)
		fsize = Forest.check(self.next, key)
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

	def extract(self:Forest[K,V]) \
			-> tuple[int,Optional[Branch[K,V]],K,V,Optional[Forest[K,V]]]:
		if self.next is None:
			return self.order - 1, self.tree.branch, \
				self.tree.key, self.tree.value, None
		order, branch, key, value, forest = self.next.extract()
		if self.tree.key < key:
			return self.order - 1, self.tree.branch, \
				self.tree.key, self.tree.value, self.next
		while order >= self.order:
			assert branch is not None
			forest = Forest.insert(forest, order, branch.tree)
			order, branch = order - 1, branch.next
		return order, branch, key, value, \
			Forest.insert(forest, self.order, self.tree)

	def extract1(self:Forest[K,V]) -> tuple[K,V,Optional[Forest[K,V]]]:
		order, branch, key, value, forest = self.extract()
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
	def __init__(self, queue:Queue[K,V], sorted:bool):
		self.queue = queue
		self.sorted = sorted

	def __contains__(self, item):
		return any(item == i for i in self)

	def __len__(self):
		return self.queue.size

	def _iter_unsorted(self) -> Iterator[tuple[K,V]]:
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

	def _iter_sorted(self) -> Iterator[tuple[K,V]]:
		queue = self.queue
		while queue.size > 0:
			key, value, queue = queue.extract()
			yield key, value

	def _iter(self) -> Iterator[tuple[K,V]]:
		if self.sorted:
			return self._iter_sorted()
		return self._iter_unsorted()

	@abstractmethod
	def __iter__(self) -> Iterator[T]:
		pass

class QueueItems(QueueView[tuple[K,V],K,V]):
	def __iter__(self) -> Iterator[tuple[K,V]]:
		return super()._iter()

class QueueKeys(QueueView[K,K,V]):
	def __iter__(self) -> Iterator[K]:
		return (k for k, v in super()._iter())

class QueueValues(QueueView[V,K,V]):
	def __iter__(self) -> Iterator[V]:
		return (v for k, v in super()._iter())

@dataclass(slots=True, frozen=True)
class Queue(Generic[K,V]):
	size: int
	key: K
	value: V
	forest: Optional[Forest[K,V]]

	def check(self):
		if self.size == 0:
			assert self.key is None
			assert self.value is None
			assert self.forest is None
		else:
			size = Forest.check(self.forest, self.key)
			assert self.size == size + 1

	@staticmethod
	def empty() -> Queue[Any,Any]:
		return Queue(0, None, None, None)

	def insert(self, key:K, value:V=cast(V,None)) -> Queue[K,V]:
		if self.size == 0:
			return Queue(1, key, value, None)
		if key < self.key:
			k1, v1, k2, v2 = key, value, self.key, self.value
		else:
			k2, v2, k1, v1 = key, value, self.key, self.value
		return Queue(self.size + 1, k1, v1,
			Forest.insert(self.forest, 0, Tree(k2, v2, None)))

	def _pprint(self):
		print('Queue', self.size, self.key, self.value)
		Forest.pprint(self.forest, 0)

	def extract(self) -> tuple[K,V,Queue[K,V]]:
		if self.size == 0:
			raise IndexError('extract from empty queue')
		if self.forest is None:
			return self.key, self.value, Queue.empty()
		key, value, forest = self.forest.extract1()
		return self.key, self.value, Queue(self.size - 1, key, value, forest)

	def merge(self, other:Queue[K,V]) -> Queue[K,V]:
		if self.size == 0: return other
		if other.size == 0: return self
		if self.key >= other.key:
			self, other = other, self
		forest = Forest.merge(self.forest, other.forest)
		forest = Forest.insert(forest, 0, Tree(other.key, other.value, None))
		return Queue(self.size + other.size, self.key, self.value, forest)

	def peek(self):
		if self.size == 0:
			raise IndexError('min of empty queue')
		return self.key, self.value

	def __len__(self):
		return self.size

	def __add__(self, other:Union[Queue[K,V],Iterable[tuple[K,V]]]) -> Queue[K,V]:
		if isinstance(other, Queue):
			return self.merge(other)
		for key, value in other:
			self = self.insert(key, value)
		return self

	def __contains__(self, key):
		return key in QueueKeys(self, False)

	def items(self, sorted=True):
		return QueueItems(self, sorted)

	def keys(self, sorted=True):
		return QueueKeys(self, sorted)

	def values(self, sorted=True):
		return QueueValues(self, sorted)

def queue(items:Optional[Iterable[tuple[K,V]]]=None) -> Queue[K,V]:
	if items is None:
		return Queue.empty()
	if isinstance(items, Queue):
		return items
	size, forest = 0, None
	for key, value in items:
		forest = Forest.insert(forest, 0, Tree(key, value, None))
		size += 1
	if forest is None:
		return Queue.empty()
	key, value, forest = forest.extract1()
	return Queue(size, key, value, forest)

def q(*items:tuple[K,V]) -> Queue[K,V]:
	return queue(items)

Collection.register(Queue)

__all__ = ('q', 'queue', 'Queue')

