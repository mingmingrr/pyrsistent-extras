from __future__ import annotations
from typing import Sequence, MutableSequence, Hashable, \
	Any, Iterator, Iterable, TypeVar, Union, \
	List, Tuple, Optional, overload, cast

import enum
import itertools
import builtins

from ._base import PSequenceBase, PSequenceEvolverBase
from .._util import compare_iter, check_index, sphinx_build

T = TypeVar('T')

class PSequence(PSequenceBase[T]):
	# Support structure for PSequence.

	# Fingertrees, digits, and nodes are all represented using the
	# same class for easier implementation.

	# Empty fingertrees are PSequence(type=Tree, size=0, items=[])
	# Single fingertrees are PSequence(type=Tree, size=N, items=[node])
	# Deep fingertrees are PSequence(type=Tree, size=N, items=[left,middle,right])

	# Value-type nodes (node1) are PSequence(type=Node, size=1, items=[value])

	__doc__ = PSequenceBase.__doc__

	__slots__ = ('_type', '_size', '_items')

	if not sphinx_build:
		_type: PSequence._Type
		_size: int
		_items: Tuple[PSequence[T], ...]

	class _Type(enum.Enum):
		Node = 0
		Digit = 1
		Tree = 2

	def __new__(cls, _type, _size, _items):
		self = super(PSequence, cls).__new__(cls)
		self._type = _type
		self._size = _size
		self._items = _items
		return self

	@staticmethod
	def _node1(value):
		return PSequence(PSequence._Type.Node, 1, (value,))
	@staticmethod
	def _node(size, *items):
		return PSequence(PSequence._Type.Node, size, items)
	@staticmethod
	def _nodeS(*items):
		size = sum(i._size for i in items)
		return PSequence(PSequence._Type.Node, size, items)

	@staticmethod
	def _digit(size, *items):
		return PSequence(PSequence._Type.Digit, size, items)
	@staticmethod
	def _digitS(*items):
		size = sum(i._size for i in items)
		return PSequence(PSequence._Type.Digit, size, items)

	@staticmethod
	def _single(item):
		return PSequence(PSequence._Type.Tree, item._size, (item,))
	@staticmethod
	def _deep(size, left, middle, right):
		return PSequence(PSequence._Type.Tree, size, (left, middle, right))
	@staticmethod
	def _deepS(left, middle, right):
		size = left._size + middle._size + right._size
		return PSequence(PSequence._Type.Tree, size, (left, middle, right))

	def _isnode1(self):
		return self._size == 1 and self._type == PSequence._Type.Node

	def _appendright(self, item):
		if self._size == 0:
			return PSequence._single(item)
		if len(self._items) == 1:
			return PSequence._deep(self._size + item._size,
				PSequence._digit(self._size, self._items[0]),
				EMPTY_SEQUENCE,
				PSequence._digit(item._size, item))
		left, middle, right = self._items
		if len(right._items) < 4:
			return PSequence._deep(self._size + item._size,
				left, middle,
				PSequence._digit(right._size + item._size, *right._items, item))
		return PSequence._deep(self._size + item._size,
			left,
			middle._appendright(PSequence._nodeS(*right._items[:3])),
			PSequence._digitS(right._items[3], item))

	def appendright(self, value:T) -> PSequence[T]:
		return self._appendright(PSequence._node1(value))

	append = appendright

	def _appendleft(self, item):
		if self._size == 0:
			return PSequence._single(item)
		if len(self._items) == 1:
			return PSequence._deep(self._size + item._size,
				PSequence._digit(item._size, item),
				EMPTY_SEQUENCE,
				PSequence._digit(self._size, self._items[0]))
		left, middle, right = self._items
		if len(left._items) < 4:
			return PSequence._deep(self._size + item._size,
				PSequence._digit(left._size + item._size, item, *left._items),
				middle, right)
		return PSequence._deep(self._size + item._size,
			PSequence._digitS(item, left._items[0]),
			middle._appendleft(PSequence._nodeS(*left._items[1:])),
			right)

	def appendleft(self, value:T) -> PSequence[T]:
		return self._appendleft(PSequence._node1(value))

	@property
	def right(self) -> T:
		if self._size == 0:
			raise IndexError('peek from empty sequence')
		if len(self._items) == 1:
			return cast(T, self._items[0]._items[0])
		return cast(T, self._items[2]._items[-1]._items[0])

	@property
	def left(self) -> T:
		if self._size == 0:
			raise IndexError('peek from empty sequence')
		if len(self._items) == 1:
			return cast(T, self._items[0]._items[0])
		return cast(T, self._items[0]._items[0]._items[0])

	def _pullright(self, left):
		if self._size == 0:
			return PSequence._fromnodes(left._size, left._items)
		init, last = self._viewright()
		return PSequence._deep(self._size + left._size,
			left, init, PSequence._digit(last._size, *last._items))

	def _viewright(self):
		if len(self._items) == 1:
			return EMPTY_SEQUENCE, self._items[0]
		left, middle, right = self._items
		*init, last = right._items
		if not init: return middle._pullright(left), last
		init = PSequence._deep(self._size - last._size, left, middle,
			PSequence._digit(right._size - last._size, *init))
		return init, last

	def viewright(self) -> Tuple[PSequence[T], T]:
		if self._size == 0:
			raise IndexError('peek from empty sequence')
		init, last =  self._viewright()
		return init, last._items[0]

	def _pullleft(self, right):
		if self._size == 0:
			return PSequence._fromnodes(right._size, right._items)
		head, tail = self._viewleft()
		return PSequence._deep(self._size + right._size,
			PSequence._digit(head._size, *head._items), tail, right)

	def _viewleft(self):
		if len(self._items) == 1:
			return self._items[0], EMPTY_SEQUENCE
		left, middle, right = self._items
		head, *tail = left._items
		if not tail: return head, middle._pullleft(right)
		return head, PSequence._deep(self._size - head._size,
			PSequence._digit(left._size - head._size, *tail),
			middle, right)

	def viewleft(self) -> Tuple[T, PSequence[T]]:
		if self._size == 0:
			raise IndexError('peek from empty sequence')
		head, tail =  self._viewleft()
		return head._items[0], tail

	def view(self, *index:int) -> Tuple[Union[T, PSequence[T]], ...]:
		items: List[Union[T, PSequence[T]]] = []
		last, rest = 0, self
		for idx in index:
			idx = self._checkindex(idx)
			if idx < last: raise IndexError('indices must be in sorted order')
			left, item, rest = rest._splitview(idx - last)
			items.append(left)
			items.append(item._items[0])
			last = idx + 1
		items.append(rest)
		return tuple(items)

	def _checkindex(self, index):
		idx = index
		if index < 0: idx += self._size
		if not (0 <= idx < self._size):
			raise IndexError('index out of range: {}'.format(index))
		return idx

	def _splitindex(self, index):
		size = 0
		for mid, item in enumerate(self._items):
			size += item._size
			if size > index: break
		return (mid, item, size - item._size, self._items[:mid],
			self._size - size, self._items[mid+1:])

	def _splitview(self, index):
		if len(self._items) == 1:
			return EMPTY_SEQUENCE, \
				self._items[0], \
				EMPTY_SEQUENCE
		left, middle, right = self._items
		if index < left._size:
			mid, item, sizeL, itemsL, sizeR, itemsR = left._splitindex(index)
			left1 = PSequence._fromnodes(sizeL, itemsL)
			right1 = middle._pullleft(right) if not itemsR else \
				PSequence._deepS(PSequence._digitS(*itemsR), middle, right)
			return left1, item, right1
		index -= left._size
		if index < middle._size:
			left1, midT, right1 = middle._splitview(index)
			index -= left1._size
			mid, item, sizeL, itemsL, sizeR, itemsR = midT._splitindex(index)
			left2 = left1._pullright(left) if not itemsL else \
				PSequence._deepS(left, left1, PSequence._digit(sizeL, *itemsL))
			right2 = right1._pullleft(right) if not itemsR else \
				PSequence._deepS(PSequence._digit(sizeR, *itemsR), right1, right)
			return left2, item, right2
		index -=  middle._size
		mid, item, sizeL, itemsL, sizeR, itemsR = right._splitindex(index)
		left1 = middle._pullright(left) if not itemsL else \
			PSequence._deepS(left, middle, PSequence._digitS(*itemsL))
		right1 = PSequence._fromnodes(sizeR, itemsR)
		return left1, item, right1

	def splitat(self, index:int) -> Tuple[PSequence[T], PSequence[T]]:
		try: index = check_index(self._size, index)
		except IndexError:
			if index < 0: return EMPTY_SEQUENCE, self
			return self, EMPTY_SEQUENCE
		left, mid, right = self._splitview(index)
		return left, right._appendleft(mid)

	@staticmethod
	def _fromnodes(size, nodes):
		if len(nodes) == 0: return EMPTY_SEQUENCE
		if len(nodes) == 1: return PSequence._single(nodes[0])
		if len(nodes) <= 8:
			mid = len(nodes) // 2
			return PSequence._deep(size,
				PSequence._digitS(*nodes[:mid]),
				EMPTY_SEQUENCE,
				PSequence._digitS(*nodes[mid:]))
		left = PSequence._digitS(*nodes[:3])
		right = PSequence._digitS(*nodes[-3:])
		if len(nodes) % 3 == 0:
			most, rest = nodes[3:-3], []
		elif len(nodes) % 3 == 1:
			most, rest = nodes[3:-7], [nodes[-7:-5], nodes[-5:-3]]
		else:
			most, rest = nodes[3:-5], [nodes[-5:-3]]
		most = list(zip(*([iter(most)]*3)))
		merged = [PSequence._nodeS(*ns) for ns in most + rest]
		middle = PSequence._fromnodes(size - left._size - right._size, merged)
		return PSequence._deep(size, left, middle, right)

	def _takeleft(self, index):
		if len(self._items) == 1:
			return self._items[0], EMPTY_SEQUENCE
		left, middle, right = self._items
		if index < left._size:
			mid, item, sizeL, itemsL, sizeR, itemsR = left._splitindex(index)
			return item, PSequence._fromnodes(sizeL, itemsL)
		index -= left._size
		if index < middle._size:
			node, left1 = middle._takeleft(index)
			mid, item, sizeL, itemsL, sizeR, itemsR = node._splitindex(index - left1._size)
			if not itemsL: return item, left1._pullright(left)
			return item, PSequence._deepS(left, left1,
				PSequence._digit(sizeL, *itemsL))
		index -= middle._size
		mid, item, sizeL, itemsL, sizeR, itemsR = right._splitindex(index)
		if not itemsL: return item, middle._pullright(left)
		return item, PSequence._deepS(left, middle,
			PSequence._digit(sizeL, *itemsL))

	def _takeL(self, count):
		if count <= 0: return EMPTY_SEQUENCE
		if count >= self._size: return self
		return self._takeleft(count)[1]

	def _takeright(self, index):
		if len(self._items) == 1:
			return self._items[0], EMPTY_SEQUENCE
		left, middle, right = self._items
		if index < right._size:
			mid, item, sizeL, itemsL, sizeR, itemsR = \
				right._splitindex(right._size - index - 1)
			return item, PSequence._fromnodes(sizeR, itemsR)
		index -= right._size
		if index < middle._size:
			node, right1 = middle._takeright(index)
			mid, item, sizeL, itemsL, sizeR, itemsR = \
				node._splitindex(node._size - index + right1._size - 1)
			if not itemsR: return item, right1._pullleft(right)
			return item, PSequence._deepS(
				PSequence._digit(sizeR, *itemsR),
				right1, right)
		index -= middle._size
		mid, item, sizeL, itemsL, sizeR, itemsR = \
			left._splitindex(left._size - index - 1)
		if not itemsR: return item, middle._pullleft(right)
		return item, PSequence._deepS(
			PSequence._digit(sizeR, *itemsR), middle, right)

	def _takeR(self, count):
		if count <= 0: return EMPTY_SEQUENCE
		if count >= self._size: return self
		return self._takeright(count)[1]

	def _extend(self, other):
		if self._size == 0: return other
		if other._size == 0: return self
		if len(self._items) == 1: return other._appendleft(self._items[0])
		if len(other._items) == 1: return self._appendright(other._items[0])
		left1, middle1, right1 = self._items
		left2, middle2, right2 = other._items
		nodes = right1._items + left2._items
		if len(nodes) % 3 == 0:
			most, rest = nodes, []
		elif len(nodes) % 3 == 1:
			most, rest = nodes[:-4], [nodes[-4:-2], nodes[-2:]]
		else:
			most, rest = nodes[:-2], [nodes[-2:]]
		most = list(zip(*([iter(most)]*3)))
		for ns in most + rest:
			middle1 = middle1._appendright(PSequence._nodeS(*ns))
		return PSequence._deep(self._size + other._size,
			left1, middle1._extend(middle2), right2)

	def extendright(self, other:Union[PSequence[T], Iterable[T]]) -> PSequence[T]:
		return self._extend(PSequence._fromitems(other))

	extend = extendright
	__add__ = extendright #: :meta public:

	def extendleft(self, other:Union[PSequence[T], Iterable[T]]) -> PSequence[T]:
		return PSequence._fromitems(other)._extend(self)

	__radd__ = extendleft #: :meta public:

	def reverse(self) -> PSequence[T]:
		if self._isnode1(): return self
		return PSequence(self._type, self._size,
			tuple(i.reverse() for i in reversed(self._items)))

	@staticmethod
	def _sliceindices(slice, length):
		start, stop, step = slice.indices(length)
		if start < 0:
			start = -1 if step < 0 else 0
		elif start >= length:
			start = length - 1 if step < 0 else length
		if stop < 0:
			stop = -1 if step < 0 else 0
		elif stop >= length:
			stop = length - 1 if step < 0 else length
		count = 0
		if stop < start and step < 0:
			count = (start - stop - 1) // -step + 1
		elif start < stop and step > 0:
			count = (stop - start - 1) // step + 1
		return start, stop, step, count

	def _getitem(self, index):
		if len(self._items) == 1 and self._type == PSequence._Type.Node:
			return self._items[0]
		mid, item, sizeL, itemsL, sizeR, itemsR = self._splitindex(index)
		return item._getitem(index - sizeL)

	def _getslice(self, modulo, count, step, output):
		if count == 0: return modulo, count
		if self._size <= modulo: return modulo - self._size, count
		if len(self._items) == 1 and self._type == PSequence._Type.Node:
			output.append(self._items[0])
			return step, count - 1
		for item in self._items:
			modulo, count = item._getslice(modulo, count, step, output)
		return modulo, count

	@overload
	def __getitem__(self, index:int) -> T: ...
	@overload
	def __getitem__(self, index:slice) -> PSequence[T]: ...
	def __getitem__(self, index):
		if isinstance(index, slice):
			start, stop, step, count = PSequence._sliceindices(index, self._size)
			if count <= 0: return EMPTY_SEQUENCE
			if step < 0: start, stop = start + (count - 1) * step, start + 1
			if abs(step) == 1:
				tree = self
				if stop < self._size: tree = tree._takeL(stop)
				if start > 0: tree = tree._takeR(stop - start)
			else:
				output = []
				modulo, count = self._getslice(start, count, abs(step) - 1, output)
				tree = PSequence._fromitems(output)
			return tree if step > 0 else tree.reverse()
		index = check_index(self._size, index)
		return self._getitem(index)

	def _setitem(self, index, value):
		if self._isnode1(): return PSequence._node1(value)
		items = list(self._items)
		for n, item in enumerate(items):
			if index < item._size: break
			index -= item._size
		items[n] = item._setitem(index, value)
		return PSequence(self._type, self._size, tuple(items))

	def _setslice(self, modulo, count, step, values):
		if count == 0: return self, modulo, count
		if self._size <= modulo: return self, modulo - self._size, count
		if len(self._items) == 1 and self._type == PSequence._Type.Node:
			return PSequence._node1(next(values)), step, count - 1
		items = []
		for item in self._items:
			item, modulo, count = item._setslice(modulo, count, step, values)
			items.append(item)
		return PSequence(self._type, self._size, tuple(items)), modulo, count

	@overload
	def set(self, index:int, value:T) -> PSequence[T]: ...
	@overload
	def set(self, index:slice, value:Iterable[T]) -> PSequence[T]: ...
	def set(self, index, value):
		if isinstance(index, slice):
			start, stop, step, count = self._sliceindices(index, self._size)
			if step == 1:
				mid = PSequence._fromitems(value)
				return self._takeL(start) + mid + \
					self._takeR(self._size - max(start, stop))
			if count == 0: return self
			if step < 0: start, stop = start + (count - 1) * step, start + 1
			try:
				len(value)
			except TypeError:
				value = list(value)
			if len(value) != count:
				raise ValueError('attempt to assign sequence of size '
				 + '{} to extended slice of size {}'.format(self._size, count))
			return self._setslice(start, count, abs(step) - 1,
				iter(value) if step > 0 else reversed(value))[0]
		index = check_index(self._size, index)
		return self._setitem(index, value)

	def _mset(self, index, pairs):
		if not pairs: return index + self._size, self
		target = pairs[-1][0]
		if index + self._size <= target:
			return index + self._size, self
		if self._isnode1(): return index + 1, PSequence._node1(pairs.pop()[1])
		items = []
		for item in self._items:
			index, item = item._mset(index, pairs)
			items.append(item)
		return index, PSequence(self._type, self._size, tuple(items))

	def mset(self, *items:Union[int,T,Tuple[int,T]]) -> PSequence[T]:
		pairs: List[Tuple[int,T]] = []
		args = iter(items)
		for arg in args:
			if isinstance(arg, tuple):
				index, value = arg
			elif isinstance(arg, int):
				index, value = arg, next(args)
			else:
				raise TypeError('expected int or tuple but got {}'.format(type(arg)))
			pairs.append((check_index(self._size, index), value))
		key = lambda x: x[0]
		pairs = [(index, list(group)[-1][1]) for index, group in
			itertools.groupby(sorted(pairs, key=key, reverse=True), key=key)]
		return self._mset(0, pairs)[1]

	def _mergeleftnode(self, item):
		if item is None: return (self,)
		if len(self._items) == 2:
			return (PSequence._node(self._size + item._size, item, *self._items),)
		return (PSequence._nodeS(item, self._items[0]),
			PSequence._nodeS(self._items[1], self._items[2]))

	def _mergerightnode(self, item):
		if item is None: return (self,)
		if len(self._items) == 2:
			return (PSequence._node(self._size + item._size, *self._items, item),)
		return (PSequence._nodeS(self._items[0], self._items[1]),
			PSequence._nodeS(self._items[2], item))

	def _deleteitem(self, index):
		if self._isnode1(): return False, None
		mid, item, sizeL, itemsL, sizeR, itemsR = self._splitindex(index)
		full, meld = item._deleteitem(index - sizeL)
		msize = 0 if meld is None else meld._size
		size = self._size - item._size + msize
		if full: return True, PSequence(self._type, size, itemsL + (meld,) + itemsR)
		if len(self._items) == 1: return False, meld
		if self._type != PSequence._Type.Tree:
			if meld is None:
				if self._type == PSequence._Type.Node and len(self._items) == 2:
					return (False,) + itemsL + itemsR
				if self._type == PSequence._Type.Digit and len(self._items) == 1:
					return False, None
			if itemsR: itemsR = itemsR[0]._mergeleftnode(meld) + itemsR[1:]
			else: itemsL = itemsL[:-1] + itemsL[-1]._mergerightnode(meld)
			items = itemsL + itemsR
			if self._type == PSequence._Type.Node and len(items) == 1:
				return (False,) + items
			return True, PSequence(self._type, size, itemsL + itemsR)
		left, middle, right = self._items
		if mid == 0:
			if middle._size == 0:
				return True, PSequence._fromnodes(size,
					right._items[0]._mergeleftnode(meld) + right._items[1:])
			head, tail = middle._viewleft()
			leftT = PSequence._digit(head._size + msize,
				*head._items[0]._mergeleftnode(meld), *head._items[1:])
			return True, PSequence._deep(size, leftT, tail, right)
		if mid == 2:
			if middle._size == 0:
				return True, PSequence._fromnodes(size,
					left._items[:-1] + left._items[-1]._mergerightnode(meld))
			init, last = middle._viewright()
			rightT = PSequence._digit(last._size + msize,
				*last._items[:-1], *last._items[-1]._mergerightnode(meld))
			return True, PSequence._deep(size, left, init, rightT)
		meld = tuple() if meld is None else (meld,)
		if len(right._items) < 4:
			return True, PSequence._deep(size, left,
				EMPTY_SEQUENCE,
				PSequence._digitS(*meld, *right._items))
		return True, PSequence._deep(size, left,
			PSequence._single(PSequence._nodeS(*meld, *right._items[:2])),
			PSequence._digitS(*right._items[2:]))

	def _deleteslice(self, start, stop, step, count):
		acc, _, rest = self._splitview(start)
		step = abs(step) - 1
		for _ in range(count - 1):
			chunk, _, rest = rest._splitview(step)
			acc += chunk
		return acc + rest

	@overload
	def delete(self, index:int) -> PSequence[T]: ...
	@overload
	def delete(self, index:slice) -> PSequence[T]: ...
	def delete(self, index) -> PSequence[T]:
		if isinstance(index, slice):
			start, stop, step, count = self._sliceindices(index, self._size)
			if count == 0: return self
			if step < 0: start, stop = start + (count - 1) * step, start + 1
			if abs(step) == 1: return self._takeL(start) + \
				self._takeR(self._size - max(start, stop))
			return self._deleteslice(start, stop, step, count)
		index = check_index(self._size, index)
		full, meld = self._deleteitem(index)
		if not full: return EMPTY_SEQUENCE
		return meld

	def _insert(self, index, value):
		if self._isnode1(): return value, self
		mid, item, sizeL, itemsL, sizeR, itemsR = self._splitindex(index)
		meld, extra = item._insert(index - sizeL, value)
		size = self._size + value._size
		if extra is None: return PSequence(self._type,
			size, itemsL + (meld,) + itemsR), None
		if self._type != PSequence._Type.Tree:
			items = itemsL + (meld, extra) + itemsR
			if self._type == PSequence._Type.Node and len(self._items) == 3:
				return PSequence._nodeS(*items[:2]), PSequence._nodeS(*items[2:])
			if self._type == PSequence._Type.Digit and len(self._items) == 4:
				return items, items[-1]
			return PSequence(self._type, size, items), None
		if len(self._items) == 1:
			return PSequence._deep(size,
				PSequence._digitS(meld),
				EMPTY_SEQUENCE,
				PSequence._digitS(extra)), None
		left, middle, right = self._items
		if mid == 0: return PSequence._deep(size,
			PSequence._digitS(*meld[:2]),
			middle._appendleft(PSequence._nodeS(*meld[2:])),
			right), None
		return PSequence._deep(size, left,
			middle._appendright(PSequence._nodeS(*meld[:3])),
			PSequence._digitS(*meld[3:])), None

	def insert(self, index:int, value:T) -> PSequence[T]:
		try: index = check_index(self._size, index)
		except IndexError:
			if index < 0: return self.appendleft(value)
			return self.appendright(value)
		return self._insert(index, PSequence._node1(value))[0]

	def remove(self, value:T) -> PSequence[T]:
		return self.delete(self.index(value))

	def transform(self, *transformations) -> PSequence[T]:
		from pyrsistent._transformations import transform
		return transform(self, transformations)

	def index(self, value, start:int=0, stop:int=cast(int,None)) -> int:
		if stop is None: stop = self._size
		for n, x in enumerate(self[start:stop]):
			if value == x: return n + start
		raise ValueError('value not in sequence');

	def count(self, value:T) -> int:
		count = 0
		for x in self:
			if value == x:
				count += 1
		return count

	def chunksof(self, size:int) -> PSequence[Sequence[T]]:
		acc = []
		while self._size != 0:
			chunk, self = self.splitat(size)
			acc.append(chunk)
		return PSequence._fromitems(cast(List[Sequence[T]], acc))

	def __reduce__(self):
		return PSequence._fromitems, (self.tolist(),)

	def __hash__(self) -> int:
		r'''
		Calculate the hash of the sequence.

		:math:`O(n)`

		>>> x1 = psequence([1,2,3,4])
		>>> x2 = psequence([1,2,3,4])
		>>> hash(x1) == hash(x2)
		True
		'''
		return hash(self.totuple())

	def _tolist(self, acc):
		if self._isnode1():
			acc.append(self._items[0])
		else:
			for item in self._items:
				item._tolist(acc)
		return acc

	def tolist(self) -> List[T]:
		return self._tolist([])

	def totuple(self) -> Tuple[T, ...]:
		return tuple(self.tolist())

	def __mul__(self, times:int) -> PSequence[T]:
		if times <= 0: return EMPTY_SEQUENCE
		acc, exp = EMPTY_SEQUENCE, self
		while times != 0:
			if times % 2 == 1:
				acc += exp
			exp = exp + exp
			times //= 2
		return acc

	__rmul__ = __mul__

	def __len__(self) -> int:
		return self._size

	def __eq__(self, other) -> bool:
		result = compare_iter(self, other, True)
		if result is NotImplemented: return NotImplemented
		return result == 0
	def __ne__(self, other) -> bool:
		result = compare_iter(self, other, True)
		if result is NotImplemented: return NotImplemented
		return result != 0
	def __gt__(self, other) -> bool:
		result = compare_iter(self, other, False)
		if result is NotImplemented: return NotImplemented
		return result > 0
	def __ge__(self, other) -> bool:
		result = compare_iter(self, other, False)
		if result is NotImplemented: return NotImplemented
		return result >= 0
	def __lt__(self, other) -> bool:
		result = compare_iter(self, other, False)
		if result is NotImplemented: return NotImplemented
		return result < 0
	def __le__(self, other) -> bool:
		result = compare_iter(self, other, False)
		if result is NotImplemented: return NotImplemented
		return result <= 0

	def __repr__(self) -> str:
		return 'psequence({})'.format(list(self))

	__str__ = __repr__

	def sort(self, *args, **kwargs) -> PSequence[T]:
		xs = self.tolist()
		xs.sort(*args, **kwargs)
		return PSequence._fromitems(xs)

	def _totree(self):
		if self._isnode1(): return 'Node', 1, self._items[0]
		return (self._type.name, self._size,
			*(i._totree() for i in self._items))

	@staticmethod
	def _fromtree(tuples):
		ptype, size, *items = tuples
		ptype = PSequence._Type[ptype]
		if ptype == PSequence._Type.Node and size == 1:
			return PSequence._node1(items[0])
		return PSequence(ptype, size,
			tuple(PSequence._fromtree(i) for i in items))

	@staticmethod
	def _refcount():
		return 0, 0, 0

	def evolver(self) -> Evolver[T]:
		return Evolver(self)

	def __iter__(self) -> Iterator[T]:
		if self._isnode1():
			yield cast(T, self._items[0])
			return
		for item in self._items:
			yield from item

	def __reversed__(self) -> Iterator[T]:
		if self._isnode1():
			yield cast(T, self._items[0])
			return
		for item in reversed(self._items):
			yield from reversed(item)

	@staticmethod
	def _fromitems(iterable:Optional[Iterable[T]]=None) -> PSequence[T]:
		if iterable is None: return EMPTY_SEQUENCE
		if isinstance(iterable, Evolver): return iterable._seq
		if isinstance(iterable, PSequence): return iterable
		nodes = [PSequence._node1(i) for i in iterable]
		return PSequence._fromnodes(len(nodes), nodes)

class Evolver(PSequenceEvolverBase[T]):
	__doc__ = PSequenceEvolverBase.__doc__

	__slots__ = ('_seq',)

	if not sphinx_build:
		_seq: PSequence[T]

	def __init__(self, _seq):
		self._seq = _seq

	def persistent(self):
		return self._seq

	def __repr__(self):
		return repr(self._seq) + '.evolver()'

	__str__ = __repr__

	@property
	def left(self) -> T:
		return self._seq.left

	@property
	def right(self) -> T:
		return self._seq.right

	def popleft(self) -> T:
		value, self._seq = self._seq.viewleft()
		return value

	def popright(self) -> T:
		self._seq, value = self._seq.viewright()
		return value

	@overload
	def pop(self, index:Optional[int]=None) -> T: ...
	@overload
	def pop(self, index:slice) -> PSequence[T]: ...
	def pop(self, index=None):
		if index is None: return self.popright()
		value = self[index]
		self.delete(index)
		return value

	def copy(self) -> Evolver[T]:
		return self._seq.evolver()

	evolver = copy

	def clear(self) -> Evolver[T]:
		self._seq = EMPTY_SEQUENCE
		return self

	def __iadd__(self, other:Union[PSequence[T], Iterable[T]]) -> Evolver[T]:
		self._seq = self._seq + other
		return self

	def __imul__(self, other:int) -> Evolver[T]:
		self._seq = self._seq * other
		return self

	# methods that query the sequence
	def tolist(self) -> List[T]:
		return self._seq.tolist()
	def totuple(self) -> Tuple[T, ...]:
		return self._seq.totuple()
	def chunksof(self, size:int) -> PSequence[Sequence[T]]:
		return self._seq.chunksof(size)
	def count(self, value:T) -> int:
		return self._seq.count(value)
	def index(self, value, start:int=0, stop:int=cast(int,None)) -> int:
		return self._seq.index(value, start, stop)
	def splitat(self, index:int) -> Tuple[PSequence[T], PSequence[T]]:
		return self._seq.splitat(index)
	def view(self, *index:int) -> Tuple[Union[T, PSequence[T]], ...]:
		return self._seq.view(*index)
	def viewleft(self) -> Tuple[T, PSequence[T]]:
		return self._seq.viewleft()
	def viewright(self) -> Tuple[PSequence[T], T]:
		return self._seq.viewright()
	def __eq__(self, other) -> bool:
		return self._seq.__eq__(other)
	def __ne__(self, other) -> bool:
		return self._seq.__ne__(other)
	def __ge__(self, other) -> bool:
		return self._seq.__ge__(other)
	def __gt__(self, other) -> bool:
		return self._seq.__gt__(other)
	def __le__(self, other) -> bool:
		return self._seq.__le__(other)
	def __lt__(self, other) -> bool:
		return self._seq.__lt__(other)
	def __reduce__(self):
		return self._seq.__reduce__()
	@overload
	def __getitem__(self, index:int) -> T: ...
	@overload
	def __getitem__(self, index:slice) -> PSequence[T]: ...
	def __getitem__(self, index):
		return self._seq.__getitem__(index)
	def __len__(self) -> int:
		return self._seq.__len__()
	def __iter__(self) -> Iterator[T]:
		return self._seq.__iter__()
	def __reversed__(self) -> Iterator[T]:
		return self._seq.__reversed__()
	def _totree(self):
		return self._seq._totree()

	# methods that create a new evolver
	def __mul__(self, times:int) -> Evolver[T]:
		return Evolver(self._seq.__mul__(times))
	__rmul__ = __mul__
	def __add__(self, other:Union[PSequence[T], Iterable[T]]) -> Evolver[T]:
		return Evolver(self._seq.__add__(other))
	__radd__ = __add__

	# methods that modify the evolver
	def reverse(self) -> Evolver[T]:
		self._seq = self._seq.reverse()
		return self
	def transform(self, *transformations) -> Evolver[T]:
		self._seq = self._seq.transform(*transformations)
		return self
	def appendleft(self, value:T) -> Evolver[T]:
		self._seq = self._seq.appendleft(value)
		return self
	def appendright(self, value:T) -> Evolver[T]:
		self._seq = self._seq.appendright(value)
		return self
	append = appendright
	def extendleft(self, other:Union[PSequence[T], Iterable[T]]) -> Evolver[T]:
		self._seq = self._seq.extendleft(other)
		return self
	def extendright(self, other:Union[PSequence[T], Iterable[T]]) -> Evolver[T]:
		self._seq = self._seq.extendright(other)
		return self
	extend = extendright
	@overload
	def set(self, index:int, value:T) -> Evolver[T]: ...
	@overload
	def set(self, index:slice, value:Iterable[T]) -> Evolver[T]: ...
	def set(self, index, value):
		self._seq = self._seq.set(index, value)
		return self
	__setitem__ = set
	def mset(self, *items:Union[int,T,Tuple[int,T]]) -> Evolver[T]:
		self._seq = self._seq.mset(*items)
		return self
	def insert(self, index:int, value:T) -> Evolver[T]:
		self._seq = self._seq.insert(index, value)
		return self
	@overload
	def delete(self, index:int) -> Evolver[T]: ...
	@overload
	def delete(self, index:slice) -> Evolver[T]: ...
	def delete(self, index):
		self._seq = self._seq.delete(index)
		return self
	__delitem__ = delete
	def remove(self, value:T) -> Evolver[T]:
		self._seq = self._seq.remove(value)
		return self
	def sort(self, *args, **kwargs) -> Evolver[T]:
		self._seq = self._seq.sort(*args, **kwargs)
		return self

EMPTY_SEQUENCE: PSequence[Any] = PSequence(PSequence._Type.Tree, 0, tuple())

# for doctest
def psequence(*args, **kwargs):
	from pyrsistent_extras import psequence as pseq
	return pseq(*args, **kwargs)

__all__ = ('PSequence', 'Evolver')
