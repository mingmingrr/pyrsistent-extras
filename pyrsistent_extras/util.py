from abc import abstractmethod
from typing import Any, Iterator, TypeVar, Optional
from typing_extensions import Protocol
import os

class Comparable(Protocol):
	@abstractmethod
	def __lt__(self, other: Any) -> bool: ...
	@abstractmethod
	def __gt__(self, other: Any) -> bool: ...
	@abstractmethod
	def __le__(self, other: Any) -> bool: ...
	@abstractmethod
	def __ge__(self, other: Any) -> bool: ...
	@abstractmethod
	def __eq__(self, other: Any) -> bool: ...
	@abstractmethod
	def __ne__(self, other: Any) -> bool: ...

T = TypeVar('T')
K = TypeVar('K', bound=Comparable)

def compare(xs:Any, ys:Any, equality:bool) -> int:
	if equality:
		if xs is ys:
			return 0
		try:
			xl, yl = len(xs), len(ys)
			if xl != yl:
				return 1
		except TypeError:
			pass
	xs, ys = iter(xs), iter(ys)
	while True:
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
		if x == y:
			continue
		if equality or x < y:
			return -1
		return 1

