from abc import abstractmethod
from typing import Any, Iterator, TypeVar, Union, Tuple, cast, overload, Iterable, Generic
from typing_extensions import Protocol

import builtins
import os

NOTHING = cast(Any, object())

class Comparable(Protocol):
	@abstractmethod
	def __lt__(self, other: Any) -> bool: ...
	@abstractmethod
	def __eq__(self, other: Any) -> bool: ...

K = TypeVar('K', bound=Comparable)
V = TypeVar('V')
T = TypeVar('T')

Kco = TypeVar('Kco', covariant=True, bound=Comparable)
Vco = TypeVar('Vco', covariant=True)

def compare_single(x:K, y:K, equality:bool) -> int:
	if x == y: return 0
	if equality or x < y: return -1
	return 1

def compare_next(xs:Iterator[Any], ys:Iterator[Any]) -> Union[int,Tuple[Any,Any]]:
	try:
		x = next(xs)
	except StopIteration:
		try:
			y = next(ys)
		except StopIteration:
			return 0
		else:
			return -1
	try:
		y = next(ys)
	except StopIteration:
		return 1
	return x, y

def compare_iter(xs:Any, ys:Any, equality:bool) -> int:
	if equality:
		if xs is ys: return 0
		try:
			xl, yl = len(xs), len(ys)
		except TypeError:
			pass
		else:
			if xl != yl: return 1
	try:
		xs, ys = iter(xs), iter(ys)
	except TypeError:
		return NotImplemented
	while True:
		n = compare_next(xs, ys)
		if isinstance(n, int): return n
		c = compare_single(*n, equality)
		if c != 0: return c

def check_index(length:int, index:int) -> int:
	idx = index
	if idx < 0:
		idx += length
	if not (0 <= idx < length):
		raise IndexError('index out of range: ' + str(index))
	return idx


@overload
def trace(x1: T, **kwargs: Any) -> T: ...
@overload
def trace(x1: Any, x2: T, **kwargs: Any) -> T: ...
@overload
def trace(x1: Any, x2: Any, x3: T, **kwargs: Any) -> T: ...
@overload
def trace(x1: Any, x2: Any, x3: Any, x4: T, **kwargs: Any) -> T: ...
@overload
def trace(x1: Any, x2: Any, x3: Any, x4: Any, x5: T, **kwargs: Any) -> T: ...
@overload
def trace(x1: Any, x2: Any, x3: Any, x4: Any, x5: Any,
	x6: T, **kwargs: Any) -> T: ...
@overload
def trace(x1: Any, x2: Any, x3: Any, x4: Any, x5: Any,
	x6: Any, x7: T, **kwargs: Any) -> T: ...
@overload
def trace(x1: Any, x2: Any, x3: Any, x4: Any, x5: Any,
	x6: Any, x7: Any, x8: T, **kwargs: Any) -> T: ...
@overload
def trace(x1: Any, x2: Any, x3: Any, x4: Any, x5: Any,
	x6: Any, x7: Any, x8: Any, x9: T, **kwargs: Any) -> T: ...
@overload
def trace(x1: Any, x2: Any, x3: Any, x4: Any, x5: Any,
	x6: Any, x7: Any, x8: Any, x9: Any, x10: T, **kwargs: Any) -> T: ...
def trace(*args: Any, **kwargs: Any):
	print(*args, **kwargs)
	return args[-1]

sphinx_build: bool = getattr(builtins, '__sphinx_build__', False)

try_c_ext: bool = not sphinx_build \
	and not os.environ.get('PYRSISTENT_NO_C_EXTENSION')

class HasItems(Protocol, Generic[Kco, Vco]):
	def _items(self) -> Iterable[tuple[Kco, Vco]]: ...

def keys_from_items(self: HasItems[K, V]):
	for k, _ in self._items(): # pyright: ignore [reportPrivateUsage]
		yield k

def values_from_items(self: HasItems[K, V]):
	for _, v in self._items(): # pyright: ignore [reportPrivateUsage]
		yield v

def items_from_items(self: HasItems[K, V]):
	return self._items() # pyright: ignore [reportPrivateUsage]
