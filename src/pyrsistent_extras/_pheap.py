from __future__ import annotations
from typing import Collection, Iterable, Iterator, Hashable, ClassVar, \
	TypeVar, Generic, Optional, Callable, Tuple, Any, Union, cast, overload
from abc import abstractmethod

import itertools
import operator
import builtins

from ._utility import Comparable, compare_next, compare_iter, sphinx_build

T = TypeVar('T')
K = TypeVar('K', bound=Comparable)
V = TypeVar('V')

class Tree(Generic[K,V]):
	# binomial tree with child nodes stored as a linked list

	# a "classic" binomial tree looks like the left
	# this implementation looks like the right
	#       A           A
	#     / | \        /
	#   B   F  H      B--F--H
	#  / \  |        /   |
	# C   D G       C--D G
	# |             |
	# E             E

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

class PHeapView(Generic[K,V,T], Collection[T]):
	__slots__ = ('_heap', '_sorted')

	if not sphinx_build:
		_heap: PHeap[K,V]
		_sorted: bool

	def __new__(cls, _heap, _sorted):
		self = super().__new__(cls)
		self._heap = _heap
		self._sorted = _sorted
		return self

	def __contains__(self, item):
		r'''
		Check if the item is in the heap

		:math:`O(n)` or :math:`O(n\log{n})`

		>>> 1 in pminheap([(1,'a'), (2,'b'), (3,'c')]).keys()
		True
		>>> 'a' in pminheap([(1,'a'), (2,'b'), (3,'c')]).values()
		True
		>>> (1, 'a') in pminheap([(1,'a'), (2,'b'), (3,'c')]).items()
		True
		'''
		return any(item == i for i in self)

	def __len__(self):
		r'''
		Get the size of the heap

		:math:`O(1)`

		>>> len(pminheap([(1,'a'), (2,'b'), (3,'c')]).keys())
		3
		>>> len(pminheap([(1,'a'), (2,'b'), (3,'c')]).values())
		3
		>>> len(pminheap([(1,'a'), (2,'b'), (3,'c')]).items())
		3
		'''
		return self._heap._size

	def _iter_unsorted(self) -> Iterator[Tuple[K,V]]:
		if self._heap._size == 0: return
		yield self._heap._key, self._heap._value
		forest = self._heap._forest
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
		heap = self._heap
		while heap._size > 0:
			key, value, heap = heap.pop()
			yield key, value

	def _iter(self) -> Iterator[Tuple[K,V]]:
		if self._sorted:
			return self._iter_sorted()
		return self._iter_unsorted()

	@abstractmethod
	def __iter__(self) -> Iterator[T]:
		r'''
		Iterate through the heap view

		:math:`O(n)` or :math:`O(n\log{n})`

		>>> list(pminheap([(1,'a'), (2,'b'), (3,'c')]).keys())
		[1, 2, 3]
		>>> list(pminheap([(1,'a'), (2,'b'), (3,'c')]).values())
		['a', 'b', 'c']
		>>> list(pminheap([(1,'a'), (2,'b'), (3,'c')]).items())
		[(1, 'a'), (2, 'b'), (3, 'c')]
		'''
		return NotImplemented

class PHeapKeys(PHeapView[K,V,K]):
	def __iter__(self) -> Iterator[K]:
		return (k for k, v in super()._iter())

class PHeapValues(PHeapView[K,V,V]):
	def __iter__(self) -> Iterator[V]:
		return (v for k, v in super()._iter())

class PHeapItems(PHeapView[K,V,Tuple[K,V]]):
	def __iter__(self) -> Iterator[Tuple[K,V]]:
		return super()._iter()

class PHeap(Generic[K,V], Collection[K], Hashable):
	r'''
	Persistent heap

	Meant for cases where a priority queue is needed.

	Do not instantiate directly, instead use the factory
	functions :func:`hl` or :func:`pminheap` to create a min-heap,
	and :func:`hg` or :func:`pmaxheap` to create a max-heap.

	The :class:`PMinHeap` and :class:`PMaxHeap` implements
	the :class:`python:typing.Container` protocol
	and is :class:`python:typing.Hashable`.

	The implementation is a binomial heap.
	Merge/pop operations are :math:`O(\log{n})`,
	and peek/push operations are :math:`O(1)`.
	Operations are not stable:
	values pushed with the same key
	may be popped in a different order.

	The following are examples of some common operations on persistent heaps:

	>>> heap1 = pminheap([(1,'a'), (2,'b')])
	>>> heap1
	pminheap([(1, 'a'), (2, 'b')])
	>>> heap2 = heap1.push(3,'c')
	>>> heap2
	pminheap([(1, 'a'), (2, 'b'), (3, 'c')])
	>>> heap3 = heap1 + heap2
	>>> heap3
	pminheap([(1, 'a'), (1, 'a'), (2, 'b'), (2, 'b'), (3, 'c')])
	>>> key, value, heap4 = heap3.pop()
	>>> (key, value)
	(1, 'a')
	>>> heap4
	pminheap([(1, 'a'), (2, 'b'), (2, 'b'), (3, 'c')])
	'''

	__slots__ = ('_size', '_key', '_value', '_forest')

	if not sphinx_build:
		_size: int
		_key: K
		_value: V
		_forest: Optional[Forest[K,V]]

	_name: ClassVar[str] = cast(Any, None)
	_down: ClassVar[bool] = cast(Any, None)
	_empty: ClassVar[PHeap[Any,Any]] = cast(Any, None)

	def __new__(cls, _size, _key, _value, _forest):
		self = super().__new__(cls)
		self._size = _size
		self._key = _key
		self._value = _value
		self._forest = _forest
		return self

	@overload
	def push(self:PHeap[K,None], key:K) -> PHeap[K,None]: ...
	@overload
	def push(self:PHeap[K,V], key:K, value:V) -> PHeap[K,V]: ...
	def push(self, key, value=None):
		r'''
		Inserts a value with the specified key

		amortized :math:`O(1)`, worst case :math:`O(\log{n})`

		>>> pminheap([(1,'a'), (2,'b')]).push(3,'c')
		pminheap([(1, 'a'), (2, 'b'), (3, 'c')])
		>>> pmaxheap([(1,'a'), (2,'b')]).push(3,'c')
		pmaxheap([(3, 'c'), (2, 'b'), (1, 'a')])
		'''
		if self._size == 0:
			return type(self)(1, key, value, None)
		if (key < self._key) != self._down:
			k1, v1, k2, v2 = key, value, self._key, self._value
		else:
			k2, v2, k1, v1 = key, value, self._key, self._value
		return type(self)(self._size + 1, k1, v1,
			Forest.push(self._forest, self._down, 0, Tree(k2, v2, None, None)))

	def pop(self) -> Tuple[K,V,PHeap[K,V]]:
		r'''
		Remove and return the min/max item

		:math:`O(\log{n})`

		:raises IndexError: if the heap is empty

		>>> pminheap([(1,'a'), (2,'b'), (3,'c')]).pop()
		(1, 'a', pminheap([(2, 'b'), (3, 'c')]))
		>>> pmaxheap([(1,'a'), (2,'b'), (3,'c')]).pop()
		(3, 'c', pmaxheap([(2, 'b'), (1, 'a')]))
		>>> pminheap([]).pop()
		Traceback (most recent call last):
		...
		IndexError: ...
		'''
		if self._size == 0:
			raise IndexError('pop from empty heap')
		if self._forest is None:
			return self._key, self._value, self._empty
		key, value, forest = self._forest.pop(self._down)
		return self._key, self._value, type(self)(self._size - 1, key, value, forest)

	def merge(self, other:PHeapLike[K,V]) -> PHeap[K,V]:
		r'''
		Return the union of the two heaps

		amortized :math:`O(\log(\min(n,m)))`,
		worst-case :math:`O(\log(\max(n,m)))`

		>>> pminheap([(1,'a'), (3,'c')]) + pminheap([(2,'b'), (4,'d')])
		pminheap([(1, 'a'), (2, 'b'), (3, 'c'), (4, 'd')])
		>>> pmaxheap([(1,'a'), (3,'c')]) + pmaxheap([(2,'b'), (4,'d')])
		pmaxheap([(4, 'd'), (3, 'c'), (2, 'b'), (1, 'a')])
		'''
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
	__or__ = merge

	def peek(self) -> Tuple[K,V]:
		r'''
		Find the min/max element

		:math:`O(1)`

		:raises IndexError: if the heap is empty

		>>> pminheap([(1,'a'), (2,'b'), (3,'c')]).peek()
		(1, 'a')
		>>> pmaxheap([(1,'a'), (2,'b'), (3,'c')]).peek()
		(3, 'c')
		>>> pminheap().peek()
		Traceback (most recent call last):
		...
		IndexError: ...
		'''
		if self._size == 0:
			raise IndexError('min of empty heap')
		return self._key, self._value

	def __len__(self) -> int:
		r'''
		Get the size of the heap

		:math:`O(1)`

		>>> len(pminheap([(1,'a'), (2,'b'), (3,'c')]))
		3
		'''
		return self._size

	def __bool__(self) -> bool:
		return self._size != 0

	def __contains__(self, key) -> bool:
		return key in PHeapKeys(self, False)

	def __repr__(self) -> str:
		return '{}({})'.format(self._name, list(self.items()))

	def items(self, sorted:bool=True) -> PHeapItems[K,V]:
		r'''
		Create a view of the heap's items

		:math:`O(1)`

		Iterating over the entire heap is :math:`O(n\log{n})` for
		``sorted=True`` and :math:`O(n)` for ``sorted=False``.

		Similar to :meth:`python:dict.items`.

		See :class:`PHeapView`.

		>>> list(pminheap([(1,'a'), (2,'b'), (3,'c')]).items())
		[(1, 'a'), (2, 'b'), (3, 'c')]
		>>> list(pmaxheap([(1,'a'), (2,'b'), (3,'c')]).items())
		[(3, 'c'), (2, 'b'), (1, 'a')]
		'''
		return PHeapItems(self, sorted)

	def keys(self, sorted:bool=True) -> PHeapKeys[K,V]:
		r'''
		Create a view of the heap's keys

		:math:`O(1)`

		Iterating over the entire heap is :math:`O(n\log{n})` for
		``sorted=True`` and :math:`O(n)` for ``sorted=False``.

		Similar to :meth:`python:dict.keys`.

		See :class:`PHeapView`.

		>>> list(pminheap([(1,'a'), (2,'b'), (3,'c')]).keys())
		[1, 2, 3]
		>>> list(pmaxheap([(1,'a'), (2,'b'), (3,'c')]).keys())
		[3, 2, 1]
		'''
		return PHeapKeys(self, sorted)

	def values(self, sorted:bool=True) -> PHeapValues[K,V]:
		r'''
		Create a view of the heap's values

		:math:`O(1)`

		Iterating over the entire heap is :math:`O(n\log{n})` for
		``sorted=True`` and :math:`O(n)` for ``sorted=False``.

		Similar to :meth:`python:dict.values`.

		See :class:`PHeapView`.

		>>> list(pminheap([(1,'a'), (2,'b'), (3,'c')]).values())
		['a', 'b', 'c']
		>>> list(pmaxheap([(1,'a'), (2,'b'), (3,'c')]).values())
		['c', 'b', 'a']
		'''
		return PHeapValues(self, sorted)

	def __iter__(self) -> Iterator[K]:
		r'''
		Iterate through the heap's keys

		:math:`O(1)`

		Iterating over the entire heap is :math:`O(n\log{n})`

		See :meth:`keys`.

		>>> list(pminheap([(1,'a'), (2,'b'), (3,'c')]).keys())
		[1, 2, 3]
		>>> list(pmaxheap([(1,'a'), (2,'b'), (3,'c')]).keys())
		[3, 2, 1]
		'''
		return iter(PHeapKeys(self, True))

	@classmethod
	def _fromitems(cls, items:PHeapLike[K,V]) -> PHeap[K,V]:
		if isinstance(items, PHeap):
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

	def _compare(self, other:PHeap[K,V], equality:bool) -> int:
		if not isinstance(other, PHeap):
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

	def __eq__(self, other) -> bool:
		r'''
		Return self == other

		:math:`O(n\log{n})` if values are comparable

		:math:`O(n\log{n}+g^2)` if values are not comparable,
		where `g` is the number of values with the same key

		>>> xs = pminheap([(1,'a'), (2,'b'), (3,'c')])
		>>> xs == pminheap([(1,'a'), (2,'b'), (3,'c')])
		True
		>>> xs == pminheap([(2,'b'), (3,'c'), (4,'d')])
		False
		'''
		result = self._compare(other, True)
		if result is NotImplemented: return NotImplemented
		return result == 0

	def __ne__(self, other) -> bool:
		r'''
		Return self != other

		:math:`O(n\log{n})` if values are comparable

		:math:`O(n\log{n}+g^2)` if values are not comparable,
		where `g` is the number of values with the same key

		>>> xs = pminheap([(1,'a'), (2,'b'), (3,'c')])
		>>> xs != pminheap([(1,'a'), (2,'b'), (3,'c')])
		False
		>>> xs != pminheap([(2,'b'), (3,'c'), (4,'d')])
		True
		'''
		result = self._compare(other, True)
		if result is NotImplemented: return NotImplemented
		return result != 0

	def __gt__(self, other) -> bool:
		r'''
		Return self > other

		:math:`O(n\log{n})`

		:raises TypeError: if values are not comparable

		>>> xs = pminheap([(1,'a'), (2,'b'), (3,'c')])
		>>> xs > pminheap([(1,'a'), (2,'b'), (3,'c')])
		False
		>>> xs > pminheap([(2,'b'), (3,'c'), (4,'d')])
		False
		>>> xs > pminheap([(0,'z'), (1,'a'), (2,'b')])
		True
		'''
		result = self._compare(other, False)
		if result is NotImplemented: return NotImplemented
		return result > 0

	def __ge__(self, other) -> bool:
		r'''
		Return self >= other

		:math:`O(n\log{n})`

		:raises TypeError: if values are not comparable

		>>> xs = pminheap([(1,'a'), (2,'b'), (3,'c')])
		>>> xs >= pminheap([(1,'a'), (2,'b'), (3,'c')])
		True
		>>> xs >= pminheap([(2,'b'), (3,'c'), (4,'d')])
		False
		>>> xs >= pminheap([(0,'z'), (1,'a'), (2,'b')])
		True
		'''
		result = self._compare(other, False)
		if result is NotImplemented: return NotImplemented
		return result >= 0

	def __lt__(self, other) -> bool:
		r'''
		Return self < other

		:math:`O(n\log{n})`

		:raises TypeError: if values are not comparable

		>>> xs = pminheap([(1,'a'), (2,'b'), (3,'c')])
		>>> xs < pminheap([(1,'a'), (2,'b'), (3,'c')])
		False
		>>> xs < pminheap([(2,'b'), (3,'c'), (4,'d')])
		True
		>>> xs < pminheap([(0,'z'), (1,'a'), (2,'b')])
		False
		'''
		result = self._compare(other, False)
		if result is NotImplemented: return NotImplemented
		return result < 0

	def __le__(self, other) -> bool:
		r'''
		Return self <= other

		:math:`O(n\log{n})`

		:raises TypeError: if values are not comparable

		>>> xs = pminheap([(1,'a'), (2,'b'), (3,'c')])
		>>> xs <= pminheap([(1,'a'), (2,'b'), (3,'c')])
		True
		>>> xs <= pminheap([(2,'b'), (3,'c'), (4,'d')])
		True
		>>> xs <= pminheap([(0,'z'), (1,'a'), (2,'b')])
		False
		'''
		result = self._compare(other, False)
		if result is NotImplemented: return NotImplemented
		return result <= 0

	def __hash__(self) -> int:
		r'''
		Calculate the hash of the heap.

		:math:`O(n)`

		:raises TypeError: if values are not comparable

		>>> x1 = pminheap([(1,'a'), (2,'b'), (3,'c')])
		>>> x2 = pminheap([(1,'a'), (2,'b'), (3,'c')])
		>>> hash(x1) == hash(x2)
		True
		'''
		h = hash(self._name)
		for k, vs in itertools.groupby(self.items(), key=operator.itemgetter(0)):
			h = hash((h, k, tuple(sorted(vs))))
		return h

	def __reduce__(self):
		r'''
		Support method for :mod:`python:pickle`

		:math:`O(n)`

		>>> import pickle
		>>> pickle.loads(pickle.dumps(pminheap([(1,'a'), (2,'b'), (3,'c')])))
		pminheap([(1, 'a'), (2, 'b'), (3, 'c')])
		'''
		return globals()[self._name], (tuple(self.items(False)),)

PHeapLike = Union[PHeap[K,V],Iterable[Tuple[K,V]]]

class PMinHeap(PHeap[K,V]):
	__doc__ = PHeap.__doc__
	_name: ClassVar[str] = 'pminheap'
	_down: ClassVar[bool] = False
	_empty: ClassVar[PMinHeap[Any,Any]] = cast(Any, None)
PMinHeap._empty = PMinHeap(0, None, None, None) # type: ignore

def pminheap(items:PHeapLike[K,V]=PMinHeap._empty) -> PMinHeap[K,V]:
	r'''
	Create a :class:`PMinHeap` from the given items

	:math:`O(n)`

	>>> pminheap()
	pminheap([])
	>>> pminheap([(1,'a'), (2,'b'), (3,'c')])
	pminheap([(1, 'a'), (2, 'b'), (3, 'c')])
	'''
	return cast(PMinHeap, PMinHeap._fromitems(items))

@overload
def pminheap_fromkeys(items:Iterable[K]) -> PMinHeap[K,None]: ...
@overload
def pminheap_fromkeys(items:Iterable[K], value:V) -> PMinHeap[K,V]: ...
def pminheap_fromkeys(items, value=None):
	r'''
	Create a :class:`PMinHeap` using a default value

	:math:`O(n)`

	>>> pminheap.fromkeys([1, 2, 3])
	pminheap([(1, None), (2, None), (3, None)])
	>>> pminheap.fromkeys([1, 2, 3], value='a')
	pminheap([(1, 'a'), (2, 'a'), (3, 'a')])
	'''
	return pminheap((item, value) for item in items)
setattr(pminheap, 'fromkeys', pminheap_fromkeys)

def hl(*items:Tuple[K,V]) -> PMinHeap[K,V]:
	'''
	Shorthand for :func:`pminheap`

	Mnemonic: Heap Less-than

	>>> hl((1,'a'), (2,'b'), (3,'c'))
	pminheap([(1, 'a'), (2, 'b'), (3, 'c')])
	'''
	return pminheap(items)

class PMaxHeap(PHeap[K,V]):
	__doc__ = PHeap.__doc__
	_name: ClassVar[str] = 'pmaxheap'
	_down: ClassVar[bool] = True
	_empty: ClassVar[PMaxHeap[Any,Any]] = cast(Any, None)
PMaxHeap._empty = PMaxHeap(0, None, None, None) # type: ignore

def pmaxheap(items:PHeapLike[K,V]=PMaxHeap._empty) -> PMaxHeap[K,V]:
	r'''
	Create a :class:`PMaxHeap` from the given items

	:math:`O(n)`

	>>> pmaxheap()
	pmaxheap([])
	>>> pmaxheap([(1,'a'), (2,'b'), (3,'c')])
	pmaxheap([(3, 'c'), (2, 'b'), (1, 'a')])
	'''
	return cast(PMaxHeap, PMaxHeap._fromitems(items))

@overload
def pmaxheap_fromkeys(items:Iterable[K]) -> PMaxHeap[K,None]: ...
@overload
def pmaxheap_fromkeys(items:Iterable[K], value:V) -> PMaxHeap[K,V]: ...
def pmaxheap_fromkeys(items, value=None):
	r'''
	Create a :class:`PMaxHeap` using a default value

	:math:`O(n)`

	>>> pmaxheap.fromkeys([1, 2, 3])
	pmaxheap([(3, None), (2, None), (1, None)])
	>>> pmaxheap.fromkeys([1, 2, 3], value='a')
	pmaxheap([(3, 'a'), (2, 'a'), (1, 'a')])
	'''
	return pmaxheap((item, value) for item in items)
setattr(pmaxheap, 'fromkeys', pmaxheap_fromkeys)

def hg(*items:Tuple[K,V]) -> PMaxHeap[K,V]:
	'''
	Shorthand for :func:`pmaxheap`

	Mnemonic: Heap Greater-than

	>>> hg((1,'a'), (2,'b'), (3,'c'))
	pmaxheap([(3, 'c'), (2, 'b'), (1, 'a')])
	'''
	return pmaxheap(items)

__all__: Tuple[str, ...] = \
	('hl', 'pminheap', 'PMinHeap', 'hg', 'pmaxheap', 'PMaxHeap')
if sphinx_build: __all__ += ('PHeapView',)
