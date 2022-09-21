from abc import abstractmethod
from typing import Any, Iterator, TypeVar, Optional, Union, Tuple, Callable
from typing_extensions import Protocol

import builtins
import platform
import os

class Comparable(Protocol):
	@abstractmethod
	def __lt__(self, other: Any) -> bool: ...
	@abstractmethod
	def __eq__(self, other: Any) -> bool: ...

K = TypeVar('K', bound=Comparable)

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
			if xl != yl: return 1
		except TypeError:
			pass
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

sphinx_build: bool = getattr(builtins, '__sphinx_build__', False)

try_c_ext: bool = not sphinx_build \
	and platform.python_implementation() == 'CPython' \
	and not os.environ.get('PYRSISTENT_NO_C_EXTENSION')

