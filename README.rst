Pyrsistent-Extras
=================

|docs-badge| |coverage-badge| |tests-badge| |mypy-badge| |pypi-badge|

.. |docs-badge| image:: https://readthedocs.org/projects/pyrsistent-extras/badge/?version=latest
	:target: https://pyrsistent-extras.readthedocs.io/en/latest/?badge=latest
.. |coverage-badge| image:: https://coveralls.io/repos/github/mingmingrr/pyrsistent-extras/badge.svg?branch=main
	:target: https://coveralls.io/github/mingmingrr/pyrsistent-extras?branch=main
.. |tests-badge| image:: https://github.com/mingmingrr/pyrsistent-extras/actions/workflows/tests.yaml/badge.svg
	:target: https://github.com/mingmingrr/pyrsistent-extras/actions/workflows/tests.yaml
.. |mypy-badge| image:: https://github.com/mingmingrr/pyrsistent-extras/actions/workflows/mypy.yaml/badge.svg
	:target: https://github.com/mingmingrr/pyrsistent-extras/actions/workflows/mypy.yaml
.. |pypi-badge| image:: https://badge.fury.io/py/pyrsistent-extras.svg
	:target: https://badge.fury.io/py/pyrsistent-extras

Extra data structures for `pyrsistent <http://github.com/tobgu/pyrsistent>`_

Below are examples of common usage patterns for some of the structures and
features. More information and full documentation for all data structures is
available in the `documentation <http://pyrsistent-extras.readthedocs.org>`_.

PSequence
---------

Persistent sequences implemented with finger trees,
with :math:`O(\log{n})` merge/split/lookup
and :math:`O(1)` access at both ends.

.. code-block:: python

	>>> from pyrsistent_extras import psequence
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


PHeap
-----

Persistent heaps implemented with binomial heaps,
with :math:`O(1)` findMin/insert and :math:`O(\log{n})` merge/deleteMin.
Comes in two flavors: ``PMinHeap`` and ``PMaxHeap``.

.. code-block:: python

	>>> from pyrsistent_extras import pminheap
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

