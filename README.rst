Pyrsistent-Extras
=================

.. image:: https://github.com/mingmingrr/pyrsistent-extras/actions/workflows/tests.yaml/badge.svg
    :target: https://github.com/mingmingrr/pyrsistent-extras/actions/workflows/tests.yaml

Extra data structures for `pyrsistent <http://github.com/tobgu/pyrsistent>`_

Below are examples of common usage patterns for some of the structures and
features. More information and full documentation for all data structures is
available in the `documentation <http://pyrsistent-extras.readthedocs.org>`_.

- PSequence_
- PHeap_

PSequence
---------

Persistent sequences implemented with finger trees.
``O(log(n))`` merge/split/access and ``O(1)`` access at both ends.

::

    >>> from pyrsistent_extras import sq
    >>> seq1 = sq([1, 2, 3])
    >>> seq2 = seq1.append(4)
    >>> seq3 = seq1 + seq2
    >>> seq1
    psequence([1, 2, 3])
    >>> seq2
    psequence([1, 2, 3, 4])
    >>> seq3
    psequence([1, 2, 3, 1, 2, 3, 4])
    >>> seq3[3]
    1
    >>> seq3[2:5]
    psequence([3, 1, 2])
    >>> seq1.set(1, 99)
    psequence([1, 99, 3])


PHeap
-----

Persistent heaps implemented with binomial heaps.
``O(1)`` findMin/insert and ``O(log(n))`` merge/deleteMin.
Comes in two flavors: ``MinHeap`` and ``MaxHeap``.

::

    >>> from pyrsistent_extras import ml, mg
    >>> heap1 = ml([1, 2, 3])
    >>> heap2 = 