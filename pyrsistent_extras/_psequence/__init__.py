from __future__ import annotations
from collections.abc import Sequence, Hashable, MutableSequence
from typing import TypeVar, Tuple, Optional, Iterable

import os
import platform
import builtins

from .._utility import sphinx_build, try_c_ext

use_c_ext = False
# Use the C extension as underlying implementation if it is available
if try_c_ext: # pragma: no cover
	try:
		from ._c_ext import PSequence, Evolver # type: ignore
		use_c_ext = True
	except ImportError as err:
		import warnings
		warnings.warn('failed to import C extension for PSequence', ImportWarning)

if not use_c_ext:
	from ._python import PSequence, Evolver

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
