from __future__ import annotations
from collections.abc import Sequence, Hashable, MutableSequence
from typing import TypeVar, Tuple, Optional, Iterable

import os
import platform
import builtins

from .._utility import sphinx_build, try_c_ext

from ._c_ext import PSequence, Evolver # type: ignore

T = TypeVar('T')

Sequence.register(PSequence)
Hashable.register(PSequence)
MutableSequence.register(Evolver)

def psequence(iterable:Optional[Iterable[T]]=None):
	r'''
	Create a :class:`PSequence` from the given items

	:math:`O(n)`

	>>> psequence()
	psequence([])
	>>> psequence([1,2,3,4])
	psequence([1, 2, 3, 4])
	'''
	return PSequence._fromitems(iterable)

def sq(*elements:T) -> PSequence[T]:
	'''
	Shorthand for :func:`psequence`

	>>> sq(1,2,3,4)
	psequence([1, 2, 3, 4])
	'''
	return psequence(elements)

__all__: Tuple[str, ...] = ('sq', 'psequence', 'PSequence')
if sphinx_build: __all__ += ('Evolver',)
