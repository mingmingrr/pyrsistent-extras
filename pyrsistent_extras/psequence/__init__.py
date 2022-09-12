from collections.abc import Sequence, Hashable, MutableSequence
import os

use_c_ext = False
# Use the C extension as underlying implementation if it is available
if not os.environ.get('PYRSISTENT_NO_C_EXTENSION'): # pragma: no cover
	try:
		from .c_ext import psequence, PSequence, Evolver # type: ignore
		use_c_ext = True
	except ImportError as err:
		pass

if not use_c_ext:
	from .python import psequence, PSequence, Evolver

Sequence.register(PSequence)
Hashable.register(PSequence)
MutableSequence.register(Evolver)

def sq(*elements):
	return psequence(elements)

__all__ = ('psequence', 'PSequence', 'sq')
