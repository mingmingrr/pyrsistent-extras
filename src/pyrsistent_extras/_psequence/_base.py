from __future__ import annotations
from typing import Sequence, Generic, Iterable, Iterator, TypeVar, Union, \
	List, Tuple, Optional, overload
from abc import ABCMeta, abstractmethod

T = TypeVar('T')

# Notable differences from the Haskell and
# Hinze/Patterson implementation include:
# - the Measure typeclass is stored as the field "size"
# - the Node and Element types are merged into a single type,
#   with "size = 1" for Elements and "size > 1" for Nodes
# - the Digit and Node types are converted from sum types to
#   a single product type, storing child Nodes in the field "items"
# - the Digit type stores its size
# - in the C implementation, the Deep constructor is converted into its
#   own type to avoid packing FingerTree with three extra pointers
# - indexing by negative indices operates on items starting from the right

class PSequence(Generic[T]):
	r'''
	Persistent sequence

	Meant for cases where you need random access and fast merging/splitting.

	Tries to follow the same naming conventions
	as the built in list/deque where feasible.

	Do not instantiate directly, instead use the factory
	functions :func:`sq` or :func:`psequence` to create an instance.

	The :class:`PSequence` implements the :class:`python:typing.Sequence`
	protocol and is :class:`python:typing.Hashable`.

	Most operations are a constant factor (around 2x-3x) slower than the
	equivalent list operation. However, some are asymptotically faster:

		- inserting or deleting an item at either end is :math:`O(1)`
		- inserting or deleting an item in the middle is :math:`O(\log{n})`
		- slicing a continguous chunk is :math:`O(\log{n})`
		- merging two sequences is :math:`O(\log{n})`
		- repeating a sequence :math:`k` times is :math:`O(\log{k}\log{n})`
		  and takes :math:`O(\log{k}\log{n})` space

	The implementation uses 2-3 finger trees annotated with sizes
	based on Haskell's `Data.Sequence <https://hackage.haskell.org/package/
	containers-0.6.6/docs/Data-Sequence.html>`_ from the package `containers 
	<https://hackage.haskell.org/package/containers-0.6.6>`_,
	which is described in

		Ralf Hinze and Ross Paterson,
		"Finger trees: a simple general-purpose data structure",
		Journal of Functional Programming 16:2 (2006) pp 197-217.
		http://www.staff.city.ac.uk/~ross/papers/FingerTree.html

	The following are examples of some common operations on persistent sequences:

	>>> seq1 = psequence([1, 2, 3])
	>>> seq1
	psequence([1, 2, 3])
	>>> seq2 = seq1.append(4)
	>>> seq2
	psequence([1, 2, 3, 4])
	>>> seq3 = seq1 + seq2
	>>> seq3
	psequence([1, 2, 3, 1, 2, 3, 4])
	>>> seq1
	psequence([1, 2, 3])
	>>> seq3[3]
	1
	>>> seq3[2:5]
	psequence([3, 1, 2])
	>>> seq1.set(1, 99)
	psequence([1, 99, 3])
	'''

	@abstractmethod
	def __eq__(self, other) -> bool:
		r'''
		Return self == other

		:math:`O(n)`

		>>> psequence([1,2,3]) == psequence([1,2,3])
		True
		>>> psequence([1,2,3]) == psequence([2,3,4])
		False
		'''

	@abstractmethod
	def __ne__(self, other) -> bool:
		r'''
		Return self != other

		:math:`O(n)`

		>>> psequence([1,2,3]) != psequence([1,2,3])
		False
		>>> psequence([1,2,3]) != psequence([2,3,4])
		True
		'''

	@abstractmethod
	def __le__(self, other) -> bool:
		r'''
		Return self <= other

		:math:`O(n)`

		>>> psequence([1,2,3]) <= psequence([1,2,3])
		True
		>>> psequence([1,2,3]) <= psequence([2,3,4])
		True
		>>> psequence([1,2,3]) <= psequence([0,1,2])
		False
		'''

	@abstractmethod
	def __lt__(self, other) -> bool:
		r'''
		Return self < other

		:math:`O(n)`

		>>> psequence([1,2,3]) < psequence([1,2,3])
		False
		>>> psequence([1,2,3]) < psequence([2,3,4])
		True
		>>> psequence([1,2,3]) < psequence([0,1,2])
		False
		'''

	@abstractmethod
	def __ge__(self, other) -> bool:
		r'''
		Return self >= other

		:math:`O(n)`

		>>> psequence([1,2,3]) >= psequence([1,2,3])
		True
		>>> psequence([1,2,3]) >= psequence([2,3,4])
		False
		>>> psequence([1,2,3]) >= psequence([0,1,2])
		True
		'''

	@abstractmethod
	def __gt__(self, other) -> bool:
		r'''
		Return self > other

		:math:`O(n)`

		>>> psequence([1,2,3]) > psequence([1,2,3])
		False
		>>> psequence([1,2,3]) > psequence([2,3,4])
		False
		>>> psequence([1,2,3]) > psequence([0,1,2])
		True
		'''

	@abstractmethod
	def extendleft(self, other:Union[PSequence[T], Iterable[T]]) -> PSequence[T]:
		r'''
		Concatenate two sequences

		:math:`O(\log(\min(n,k)))` extend with :class:`PSequence`

		:math:`O(\log{n}+k)` extend with iterable

		>>> psequence([1,2]).extendleft([3,4])
		psequence([3, 4, 1, 2])
		'''

	@abstractmethod
	def extendright(self, other:Union[PSequence[T], Iterable[T]]) -> PSequence[T]:
		r'''
		Concatenate two sequences

		:math:`O(\log(\min(n,k)))` extend with PSequence

		:math:`O(\log{n}+k)` extend with iterable

		>>> psequence([1,2]).extend([3,4])
		psequence([1, 2, 3, 4])
		>>> psequence([1,2]).extendright([3,4])
		psequence([1, 2, 3, 4])
		>>> psequence([1,2]) + [3,4]
		psequence([1, 2, 3, 4])
		'''

	extend = extendright

	def __add__(self, other:Union[PSequence[T], Iterable[T]]) -> PSequence[T]:
		r'''
		Concatenate two sequences

		:math:`O(\log(\min(n,k)))` extend with PSequence

		:math:`O(\log{n}+k)` extend with iterable

		>>> psequence([1,2]) + psequence([3,4])
		psequence([1, 2, 3, 4])
		>>> psequence([1,2]) + [3,4]
		psequence([1, 2, 3, 4])
		'''
		return self.extendright(other)

	@overload
	def __getitem__(self, index:int) -> T: ...
	@overload
	def __getitem__(self, index:slice) -> PSequence[T]: ...
	@abstractmethod
	def __getitem__(self, index):
		r'''
		Get the element(s) at the specified position(s)

		Time complexities for `n[i]`:

		- :math:`O(\log(\min(i,n−i)))` getting a single item.
		- :math:`O(\log(\max(i,m)))` getting a contiguous slice.
		- :math:`O(\log{n}+m)` getting a non-contiguous slice.

		:raises IndexError: if the index is out of bounds

		>>> psequence([1,2,3,4])[2]
		3
		>>> psequence([1,2,3,4,5])[1:4]
		psequence([2, 3, 4])
		>>> psequence([1,2,3,4])[5]
		Traceback (most recent call last):
		...
		IndexError: ...
		'''

	@overload
	def set(self, index:int, value:T) -> PSequence[T]: ...
	@overload
	def set(self, index:slice, value:Iterable[T]) -> PSequence[T]: ...
	@abstractmethod
	def set(self, index, value):
		r'''
		Replace the element(s) at the specified position(s)

		Time complexities for `n.set(i,x)`:

		- :math:`O(\log(\min(i,n−i)))` replacing a single item.
		- :math:`O(\log(\max(n,x)))` replacing a contiguous slice.
		- :math:`O(x)` replacing a non-contiguous slice.

		:raises IndexError: if the index is out of bounds

		>>> psequence([1,2,3,4]).set(2, 0)
		psequence([1, 2, 0, 4])
		>>> psequence([1,2,3,4,5]).set(slice(1,4), [-1,-2,-3])
		psequence([1, -1, -2, -3, 5])
		>>> psequence([1,2,3,4]).set(5, 0)
		Traceback (most recent call last):
		...
		IndexError: ...
		'''

	@abstractmethod
	def mset(self, *values:Tuple[int,T]) -> PSequence[T]:
		r'''
		Replace multiple elements

		:math:`O(k\log{n}+k\log{k})`

		:raises IndexError: if any index is out of bounds

		>>> psequence([1,2,3,4]).mset(2, 0, 3, 5)
		psequence([1, 2, 0, 5])
		>>> psequence([1,2,3,4]).mset((2, 0), (3, 5))
		psequence([1, 2, 0, 5])
		>>> psequence([1,2,3,4]).mset(5, 0)
		Traceback (most recent call last):
		...
		IndexError: ...
		'''

	@abstractmethod
	def insert(self, index:int, value:T) -> PSequence[T]:
		r'''
		Insert an element at the specified position

		:math:`O(\log(\min(i,n−i)))`

		>>> psequence([1,2,3,4]).insert(2, 0)
		psequence([1, 2, 0, 3, 4])
		>>> psequence([1,2,3,4]).insert(-10, 0)
		psequence([0, 1, 2, 3, 4])
		>>> psequence([1,2,3,4]).insert(10, 0)
		psequence([1, 2, 3, 4, 0])
		'''

	@overload
	def delete(self, index:int) -> PSequence[T]: ...
	@overload
	def delete(self, index:slice) -> PSequence[T]: ...
	@abstractmethod
	def delete(self, index) -> PSequence[T]:
		r'''
		Delete the element(s) at the specified position(s)

		Time complexities for `n.delete(i)`:

		- :math:`O(\log(\min(i,n−i)))` deleting a single item.
		- :math:`O(\log{n})` deleting a contiguous slice.
		- :math:`O(\frac{n}{k}\log{k})` deleting a non-contiguous slice.

		:raises IndexError: if the index is out of bounds

		>>> psequence([1,2,3,4]).delete(2)
		psequence([1, 2, 4])
		>>> psequence([1,2,3,4,5]).delete(slice(1,4))
		psequence([1, 5])
		>>> psequence([1,2,3,4]).delete(5)
		Traceback (most recent call last):
		...
		IndexError: ...
		'''

	@abstractmethod
	def remove(self, value:T) -> PSequence[T]:
		r'''
		Remove an element by value

		:math:`O(n)`

		:raises ValueError: if the value is not in the sequence

		>>> psequence([1,2,3,4]).remove(2)
		psequence([1, 3, 4])
		>>> psequence([1,2,3,4]).remove(0)
		Traceback (most recent call last):
		...
		ValueError: ...
		'''

	@abstractmethod
	def __mul__(self, times:int) -> PSequence[T]:
		r'''
		Repeat the sequence k times

		:math:`O(\log{n}\log{k})`

		>>> psequence([1,2,3]) * 3
		psequence([1, 2, 3, 1, 2, 3, 1, 2, 3])
		>>> 3 * psequence([1,2,3])
		psequence([1, 2, 3, 1, 2, 3, 1, 2, 3])
		'''

	__rmul__ = __mul__

	@abstractmethod
	def __iter__(self) -> Iterator[T]:
		r'''
		Create an iterator

		:math:`O(1)`

		Iterating the entire sequence is :math:`O(n)`.

		>>> i = iter(psequence([1,2,3]))
		>>> next(i)
		1
		>>> next(i)
		2
		>>> next(i)
		3
		>>> next(i)
		Traceback (most recent call last):
		...
		StopIteration
		'''

	@abstractmethod
	def __reversed__(self) -> Iterator[T]:
		r'''
		Create a reverse iterator

		:math:`O(1)`

		Iterating the entire sequence is :math:`O(n)`.

		>>> i = reversed(psequence([1,2,3]))
		>>> next(i)
		3
		>>> next(i)
		2
		>>> next(i)
		1
		>>> next(i)
		Traceback (most recent call last):
		...
		StopIteration
		'''

	@abstractmethod
	def __len__(self) -> int:
		r'''
		Get the length of the sequence

		:math:`O(1)`

		>>> len(psequence([1,2,3,4]))
		4
		'''

	@abstractmethod
	def __reduce__(self):
		r'''
		Support method for :mod:`python:pickle`

		:math:`O(n)`

		>>> import pickle
		>>> pickle.loads(pickle.dumps(psequence([1,2,3,4])))
		psequence([1, 2, 3, 4])
		'''

	@abstractmethod
	def __repr__(self) -> str:
		r'''
		Get a formatted string representation

		:math:`O(n)`

		>>> repr(psequence([1,2,3]))
		'psequence([1, 2, 3])'
		'''

	__str__ = __repr__

	@abstractmethod
	def appendleft(self, value:T) -> PSequence[T]:
		r'''
		Add an element to the left end

		:math:`O(1)`

		>>> psequence([1,2,3]).appendleft(0)
		psequence([0, 1, 2, 3])
		'''

	@abstractmethod
	def appendright(self, value:T) -> PSequence[T]:
		r'''
		Add an element to the right end

		:math:`O(1)`

		>>> psequence([1,2,3]).append(4)
		psequence([1, 2, 3, 4])
		>>> psequence([1,2,3]).appendright(4)
		psequence([1, 2, 3, 4])
		'''

	append = appendright

	@abstractmethod
	def count(self, value:T) -> int:
		r'''
		Count the number of times a value appears

		:math:`O(n)`

		>>> psequence([1,2,3,3,4]).count(3)
		2
		'''

	@abstractmethod
	def index(self, value, start:int=0, stop:int=0) -> int:
		r'''
		Find the first index of a value

		:math:`O(n)`

		:raises ValueError: if the value is not in the sequence

		>>> psequence([1,2,3,4]).index(3)
		2
		>>> psequence([]).index(3)
		Traceback (most recent call last):
		...
		ValueError: ...
		'''

	@abstractmethod
	def splitat(self, index:int) -> Tuple[PSequence[T], PSequence[T]]:
		r'''
		Split a sequence at a given position

		:math:`O(\log(\min(i,n−i)))`

		Equivalent to ``(seq.take(i), seq.drop(i))``.
		Does not raise :exc:`python:IndexError`, unlike :meth:`view`.

		>>> psequence([1,2,3,4]).splitat(2)
		(psequence([1, 2]), psequence([3, 4]))
		>>> psequence([1,2,3,4]).splitat(5)
		(psequence([1, 2, 3, 4]), psequence([]))
		>>> psequence([1,2,3,4]).splitat(-1)
		(psequence([1, 2, 3]), psequence([4]))
		>>> psequence([1,2,3,4]).splitat(-5)
		(psequence([]), psequence([1, 2, 3, 4]))
		'''

	@abstractmethod
	def chunksof(self, size:int) -> PSequence[Sequence[T]]:
		r'''
		Split the sequence into chunks

		:math:`O(\frac{n}{k}\log{n})`

		>>> psequence([1,2,3,4,5,6,7,8]).chunksof(3)
		psequence([psequence([1, 2, 3]), psequence([4, 5, 6]), psequence([7, 8])])
		'''

	@property
	@abstractmethod
	def left(self) -> T:
		r'''
		Extract the first element

		:math:`O(1)`

		:raises IndexError: if the sequence is empty

		>>> psequence([1,2,3,4]).left
		1
		>>> psequence([]).left
		Traceback (most recent call last):
		...
		IndexError: ...
		'''

	@property
	@abstractmethod
	def right(self) -> T:
		r'''
		Extract the last element

		:math:`O(1)`

		:raises IndexError: if the sequence is empty

		>>> psequence([1,2,3,4]).right
		4
		>>> psequence([]).right
		Traceback (most recent call last):
		...
		IndexError: ...
		'''

	@abstractmethod
	def viewleft(self) -> Tuple[T, PSequence[T]]:
		r'''
		Analyse the left end

		:math:`O(1)`

		:raises IndexError: if the sequence is empty

		>>> psequence([1,2,3,4]).viewleft()
		(1, psequence([2, 3, 4]))
		>>> psequence([]).viewleft()
		Traceback (most recent call last):
		...
		IndexError: ...
		'''

	@abstractmethod
	def viewright(self) -> Tuple[PSequence[T], T]:
		r'''
		Analyse the right end

		:math:`O(1)`

		:raises IndexError: if the sequence is empty

		>>> psequence([1,2,3,4]).viewright()
		(psequence([1, 2, 3]), 4)
		>>> psequence([]).viewright()
		Traceback (most recent call last):
		...
		IndexError: ...
		'''

	@abstractmethod
	def view(self, *index:int) -> Tuple[Union[T, PSequence[T]], ...]:
		r'''
		Split a sequence on the given position(s)

		:math:`O(k\log{n})`

		Useful for pattern matching:

		>>> # doctest: +SKIP
		... match seq.view(0, 1, 4):
		...   case (_, x0, _, x1, x_2_3, x4, _, rest):
		...     pass

		Equivalent to ``(seq[:i1], seq[i1], seq[i1+1:i2],
		seq[i2], seq[i2+1:i3], ..., seq[in+1:])``.

		:raises IndexError: if any index is out of bounds

		>>> psequence([1,2,3,4]).view(0)
		(psequence([]), 1, psequence([2, 3, 4]))
		>>> psequence([1,2,3,4]).view(1)
		(psequence([1]), 2, psequence([3, 4]))
		>>> psequence([1,2,3,4]).view(1, 3)
		(psequence([1]), 2, psequence([3]), 4, psequence([]))
		>>> psequence([1,2,3,4]).view(5)
		Traceback (most recent call last):
		...
		IndexError: ...
		'''

	@abstractmethod
	def reverse(self) -> PSequence[T]:
		r'''
		Reverse the sequence

		:math:`O(n)`

		>>> psequence([1,2,3,4]).reverse()
		psequence([4, 3, 2, 1])
		'''

	@abstractmethod
	def tolist(self) -> List[T]:
		r'''
		Convert the sequence to a :class:`python:list`

		:math:`O(n)`

		>>> psequence([1,2,3,4]).tolist()
		[1, 2, 3, 4]
		'''

	@abstractmethod
	def totuple(self) -> Tuple[T, ...]:
		r'''
		Convert the sequence to a :class:`python:tuple`

		:math:`O(n)`

		>>> psequence([1,2,3,4]).totuple()
		(1, 2, 3, 4)
		'''

	@abstractmethod
	def transform(self, transformations) -> PSequence[T]:
		r'''
		Apply one or more transformations

		>>> from pyrsistent import ny
		>>> psequence([1,2,3,4]).transform([ny], lambda x: x*2)
		psequence([2, 4, 6, 8])
		'''

	@abstractmethod
	def evolver(self) -> PSequenceEvolver[T]:
		r'''
		Create an :class:`Evolver`

		:math:`O(1)`
		'''

	@abstractmethod
	def sort(self, *args, **kwargs) -> PSequence[T]:
		r'''
		Creat a sorted copy of the sequence

		:math:`O(n\log{n})`

		Arguments are the same as :meth:`python:list.sort`.

		>>> psequence([3,1,4,2]).sort()
		psequence([1, 2, 3, 4])
		'''

	@staticmethod
	@abstractmethod
	def _fromitems(iterable:Optional[Iterable[T]]=None) -> PSequence[T]:
		pass

class PSequenceEvolver(PSequence[T]):
	r'''
	Evolver for :class:`PSequence`

	The evolver acts as a mutable view of the sequence with "transaction
	like" semantics. No part of the underlying sequence is updated, it is
	still fully immutable. Furthermore multiple evolvers created from the
	same psequence do not interfere with each other.

	You may want to use an evolver instead of working directly with
	:class:`PSequence` in the following cases:

	- Multiple updates are done to the same sequence and the
	  intermediate results are of no interest. In this case using an
	  evolver may be easier to work with.
	- You need to pass a sequence into a legacy function or a function
	  that you have no control over which performs in place mutations
	  of lists. In this case pass an evolver instance instead and then
	  create a new psequence from the evolver once the function returns.

	The following example illustrates a typical workflow when working with
	evolvers:

	Create the evolver and perform various mutating updates to it:

	>>> seq1 = psequence([1,2,3,4,5])
	>>> evo1 = seq1.evolver()
	>>> evo1[1] = 22
	>>> _ = evo1.append(6)
	>>> _ = evo1.extend([7,8,9])
	>>> evo1[8] += 1
	>>> evo1
	psequence([1, 22, 3, 4, 5, 6, 7, 8, 10]).evolver()

	The underlying psequence remains the same:

	>>> seq1
	psequence([1, 2, 3, 4, 5])

	The changes are kept in the evolver. An updated psequence can be
	created using the persistent() function on the evolver.

	>>> seq2 = evo1.persistent()
	>>> seq2
	psequence([1, 22, 3, 4, 5, 6, 7, 8, 10])

	The new psequence will share data with the original psequence in the
	same way that would have been done if only using operations on the
	sequence.

	>>> evo = psequence([1,2,3,4]).evolver()
	>>> evo[2] = 0
	>>> evo
	psequence([1, 2, 0, 4]).evolver()
	'''

	@abstractmethod
	def popleft(self) -> T:
		r'''
		Remove the leftmost element

		:math:`O(1)`

		:raises IndexError: if the sequence is empty

		>>> seq = psequence([1,2,3,4]).evolver()
		>>> seq.popleft()
		1
		>>> seq
		psequence([2, 3, 4]).evolver()
		>>> psequence([]).evolver().popleft()
		Traceback (most recent call last):
		...
		IndexError: ...
		'''

	@abstractmethod
	def popright(self) -> T:
		r'''
		Remove the rightmost element

		:math:`O(1)`

		:raises IndexError: if the sequence is empty

		>>> seq = psequence([1,2,3,4]).evolver()
		>>> seq.popright()
		4
		>>> seq
		psequence([1, 2, 3]).evolver()
		>>> psequence([]).evolver().popright()
		Traceback (most recent call last):
		...
		IndexError: ...
		'''

	@overload
	def pop(self, index:Optional[int]=None) -> T: ...
	@overload
	def pop(self, index:slice) -> PSequence[T]: ...
	@abstractmethod
	def pop(self, index=None):
		r'''
		Remove and return an element at the specified index

		See `PSequence.delete` and `list.pop`.

		:raises IndexError: if the sequence is empty or the index is out of bounds

		>>> seq = psequence([1,2,3,4]).evolver()
		>>> seq.pop()
		4
		>>> seq
		psequence([1, 2, 3]).evolver()
		>>> seq.pop(1)
		2
		>>> seq
		psequence([1, 3]).evolver()
		'''

	@abstractmethod
	def copy(self) -> PSequenceEvolver[T]:
		r'''
		Return a shallow copy of the sequence

		:math:`O(1)`

		>>> seq1 = psequence([1,2,3,4]).evolver()
		>>> seq2 = seq1.copy()
		>>> seq2[1] = 0
		>>> seq2
		psequence([1, 0, 3, 4]).evolver()
		>>> seq1
		psequence([1, 2, 3, 4]).evolver()
		'''

	@abstractmethod
	def clear(self) -> PSequenceEvolver[T]:
		r'''
		Remove all items from the sequence

		:math:`O(1)`

		>>> seq = psequence([1,2,3,4]).evolver()
		>>> _ = seq.clear()
		>>> seq
		psequence([]).evolver()
		'''

	@abstractmethod
	def persistent(self) -> PSequence[T]:
		r'''
		Extract the sequence from the evolver

		:math:`O(1)`

		>>> seq = psequence([1,2,3,4])
		>>> seq.evolver().persistent()
		psequence([1, 2, 3, 4])
		'''

	@staticmethod
	def _fromitems(iterable:Optional[Iterable[T]]=None) -> PSequence[T]:
		raise TypeError('PSequenceEvolver does not support _fromitems')

# for doctest
def psequence(*args, **kwargs):
	from pyrsistent_extras import psequence as pseq
	return pseq(*args, **kwargs)

__all__ = ('PSequence', 'PSequencePSequenceEvolver')
