from collections.abc import Sequence, Hashable, MutableSequence
import os
import platform

use_c_ext = False
# Use the C extension as underlying implementation if it is available
if platform.python_implementation() == 'CPython' \
		and not os.environ.get('PYRSISTENT_NO_C_EXTENSION'): # pragma: no cover
	try:
		from ._c_ext import psequence, PSequence, Evolver # type: ignore
		use_c_ext = True
	except ImportError as err:
		import warnings
		warnings.warn('failed to import C extension for PSequence', ImportWarning)

if not use_c_ext:
	from ._python import psequence, PSequence, Evolver

Sequence.register(PSequence)
Hashable.register(PSequence)
MutableSequence.register(Evolver)

def sq(*elements):
	'''
	Shorthand for :func:`psequence`

	>>> sq(1,2,3,4)
	psequence([1, 2, 3, 4])
	'''
	return psequence(elements)

__all__ = ('sq', 'psequence', 'PSequence')
