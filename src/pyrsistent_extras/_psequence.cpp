#include <sstream>
#include <iostream>
#include <functional>
#include <optional>
#include <algorithm>
#include <regex>

#include <nanobind/nanobind.h>
#include <nanobind/operators.h>
#include <nanobind/typing.h>
#include <nanobind/make_iterator.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/optional.h>

namespace nb = nanobind;
using namespace nb::literals;

std::ostream& operator <<(std::ostream& out, const nb::handle x)
	{ return out << nb::repr(x).c_str(); }

#include "_psequence.hpp"
#include "_utility.hpp"
#include "_nanobind.hpp"

namespace pyr = pyrsistent;
namespace pyr_nb = pyrsistent::nanobind;

using Sequence = pyr::Sequence<nb::object>;

struct Evolver { Sequence seq; };

NB_MODULE(_psequence, mod) {
	mod.attr("T") = nb::type_var("T");
	mod.attr("IndexLike") = "typing.Union[int,slice]";

	auto cls = nb::class_<Sequence>(mod, "PSequence", nb::is_generic(), R"(
		Persistent sequence

		Meant for cases where you need random access and fast merging/splitting.

		Tries to follow the same naming conventions
		as the built in list/deque where feasible.

		Do not instantiate directly, instead use the factory
		functions :func:`sq` or :func:`psequence` to create an instance.

		The :class:`PSequence` implements the :class:`python:typing.Sequence`
		protocol and is :class:`python:collections.abc.Hashable`.

		Most operations are a constant factor (around 2x-3x) slower than the
		equivalent list operation. However, some are asymptotically faster:

			- inserting or deleting an item at either end is :math:`O(1)`
			- inserting or deleting an item in the middle is :math:`O(\log{n})`
			- slicing a continguous chunk is :math:`O(\log{n})`
			- merging two sequences is :math:`O(\log{n})`
			- repeating a sequence :math:`k` times is :math:`O(\log{k}\log{n})`
				and takes :math:`O(\log{k}\log{n})` space

		The implementation uses 2-3 finger trees annotated with sizes
		based on Haskell's `Data.Sequence <https://hackage.haskell.org/package/
		containers-0.6.6/docs/Data-Sequence.html>`_ from the package `containers 
		<https://hackage.haskell.org/package/containers-0.6.6>`_,
		which is described in

			Ralf Hinze and Ross Paterson,
			"Finger trees: a simple general-purpose data structure",
			Journal of Functional Programming 16:2 (2006) pp 197-217.
			http://www.staff.city.ac.uk/~ross/papers/FingerTree.html

		The following are examples of some common operations on persistent sequences:

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
	)", nb::sig("class PSequence(collections.abc.Sequence[T], collections.abc.Hashable)"));
	cls.def(nb::init<>());

	cls.def("__eq__", &Sequence::template operator == <pyr_nb::object_view>, R"(
		Return self == other

		:math:`O(n)`

		>>> psequence([1,2,3]) == psequence([1,2,3])
		True
		>>> psequence([1,2,3]) == psequence([2,3,4])
		False
	)");
	cls.def("__ne__", &Sequence::template operator != <pyr_nb::object_view>, R"(
		Return self != other

		:math:`O(n)`

		>>> psequence([1,2,3]) != psequence([1,2,3])
		False
		>>> psequence([1,2,3]) != psequence([2,3,4])
		True
	)");
	cls.def("__lt__", &Sequence::template operator <  <pyr_nb::object_view>, R"(
		Return self < other

		:math:`O(n)`

		>>> psequence([1,2,3]) < psequence([1,2,3])
		False
		>>> psequence([1,2,3]) < psequence([2,3,4])
		True
		>>> psequence([1,2,3]) < psequence([0,1,2])
		False
	)");
	cls.def("__gt__", &Sequence::template operator >  <pyr_nb::object_view>, R"(
		Return self > other

		:math:`O(n)`

		>>> psequence([1,2,3]) > psequence([1,2,3])
		False
		>>> psequence([1,2,3]) > psequence([2,3,4])
		False
		>>> psequence([1,2,3]) > psequence([0,1,2])
		True
	)");
	cls.def("__le__", &Sequence::template operator <= <pyr_nb::object_view>, R"(
		Return self <= other

		:math:`O(n)`

		>>> psequence([1,2,3]) <= psequence([1,2,3])
		True
		>>> psequence([1,2,3]) <= psequence([2,3,4])
		True
		>>> psequence([1,2,3]) <= psequence([0,1,2])
		False
	)");
	cls.def("__ge__", &Sequence::template operator >= <pyr_nb::object_view>, R"(
		Return self >= other

		:math:`O(n)`

		>>> psequence([1,2,3]) >= psequence([1,2,3])
		True
		>>> psequence([1,2,3]) >= psequence([2,3,4])
		False
		>>> psequence([1,2,3]) >= psequence([0,1,2])
		True
	)");

	cls.def("extendright", [mod](const Sequence& xs, const nb::object& ys) {
		return xs.append(nb::cast<Sequence>(mod.attr("psequence")(ys)));
	}, R"(
		Concatenate two sequences

		:math:`O(\log(\min(n,k)))` extend with PSequence

		:math:`O(\log{n}+k)` extend with iterable

		>>> psequence([1,2]).extend([3,4])
		psequence([1, 2, 3, 4])
		>>> psequence([1,2]).extendright([3,4])
		psequence([1, 2, 3, 4])
		>>> psequence([1,2]) + [3,4]
		psequence([1, 2, 3, 4])
	)", nb::sig("def extendright(self, values: collections.abc.Iterable[T]) -> PSequence[T]"));

	cls.def("extendleft", [mod](const Sequence& xs, const nb::object ys) {
		return nb::cast<Sequence>(mod.attr("psequence")(ys)).append(xs);
	}, R"(
		Concatenate two sequences

		:math:`O(\log(\min(n,k)))` extend with :class:`PSequence`

		:math:`O(\log{n}+k)` extend with iterable

		>>> psequence([1,2]).extendleft([3,4])
		psequence([3, 4, 1, 2])
	)", nb::sig("def extendleft(self, values: collections.abc.Iterable[T]) -> PSequence[T]"));

	cls.def("extend", [](nb::object seq, nb::args args, nb::kwargs kwargs) {
		return seq.attr("extendright")(*args, **kwargs);
	}, nb::sig("def extend(self, values: collections.abc.Iterable[T]) -> PSequence[T]"),
		"Alias for :meth:`extendright`");
	cls.def("__add__", [](nb::object seq, nb::args args, nb::kwargs kwargs) {
		return seq.attr("extendright")(*args, **kwargs);
	}, nb::sig("def __add__(self, values: collections.abc.Iterable[T]) -> PSequence[T]"),
		"Alias for :meth:`extendright`");
	cls.def("__radd__", [](nb::object seq, nb::args args, nb::kwargs kwargs) {
		return seq.attr("extendleft")(*args, **kwargs);
	}, nb::sig("def __radd__(self, values: collections.abc.Iterable[T]) -> PSequence[T]"),
		"Alias for :meth:`extendleft`");

	cls.def("index", [](Sequence seq, nb::object value,
		Py_ssize_t start, std::optional<Py_ssize_t> stop
	) {
		if(start < 0) start = std::max<Py_ssize_t>(start + seq.size(), 0);
		seq = seq.drop_front(start);
		if(stop) seq = seq.take_front(std::max(start, *stop) - start);
		Py_ssize_t index = 0;
		for(auto x: seq)
			if(x.equal(value)) return index;
			else ++index;
		throw nb::value_error("value is not in sequence");
	}, "value"_a, "start"_a = 0, "stop"_a = nb::none(), R"(
		Find the first index of a value

		:math:`O(n)`

		:raises ValueError: if the value is not in the sequence

		>>> psequence([1,2,3,4]).index(3)
		2
		>>> psequence([]).index(3)
		Traceback (most recent call last):
		...
		ValueError: ...
	)", nb::sig("def index(self, value, start:int=0, stop:typing.Optional[int]=None) -> int"));

	cls.def("__getitem__", [](const Sequence& seq, Py_ssize_t index) {
		return seq.at(pyr::adjust_index<Py_ssize_t>(seq.size(), index));
	}, nb::sig("def __getitem__(self, index: int) -> T"));
	cls.def("__getitem__", [](const Sequence& seq, const nb::slice& slice) {
		auto [start, stop, step, count] = slice.compute(seq.size());
		return seq.at(start, stop, step);
	}, R"(
		Get the element(s) at the specified position(s)

		Time complexities for `n[i]`:

		- :math:`O(\log(\min(i,n−i)))` getting a single item.
		- :math:`O(\log(\max(i,m)))` getting a contiguous slice.
		- :math:`O(\log{n}+m)` getting a non-contiguous slice.

		:raises IndexError: if the index is out of bounds

		>>> psequence([1,2,3,4])[2]
		3
		>>> psequence([1,2,3,4])[-2]
		3
		>>> psequence([1,2,3,4,5])[1:4]
		psequence([2, 3, 4])
		>>> psequence([1,2,3,4,5])[-4:-1]
		psequence([2, 3, 4])
		>>> psequence([1,2,3,4,5])[1::2]
		psequence([2, 4])
		>>> psequence([1,2,3,4])[5]
		Traceback (most recent call last):
		...
		IndexError: ...
	)", nb::sig("def __getitem__(self, index: slice) -> PSequence[T]"));

	cls.def("set", [](const Sequence& seq, Py_ssize_t index, const nb::object& value) {
		return seq.set(pyr::adjust_index<Py_ssize_t>(seq.size(), index), value);
	}, nb::sig("def set(self, index: int, value: T) -> PSequence[T]"));
	cls.def("set", [mod](const Sequence& seq, const nb::slice& slice, const nb::object& values) {
		static const char errmsg[] = "assigning an incorrectly sized sequence to a slice";
		auto [start, stop, step, count] = slice.compute(seq.size());
		if(step == 1) return seq.set(start, stop,
			nb::cast<Sequence>(mod.attr("psequence")(values)));
		using Iter = pyr_nb::object_iterator<decltype(values.begin())>;
		return seq.set(start, stop, step, Iter(values.begin()), Iter(values.end()));
	}, R"(
		Replace the element(s) at the specified position(s)

		Time complexities for `n.set(i,x)`:

		- :math:`O(\log(\min(i,n−i)))` replacing a single item.
		- :math:`O(\log(\max(n,x)))` replacing a contiguous slice.
		- :math:`O(x)` replacing a non-contiguous slice.

		:raises IndexError: if the index is out of bounds

		>>> psequence([1,2,3,4]).set(2, 0)
		psequence([1, 2, 0, 4])
		>>> psequence([1,2,3,4,5]).set(slice(1,4), [-1,-2,-3])
		psequence([1, -1, -2, -3, 5])
		>>> psequence([1,2,3,4]).set(5, 0)
		Traceback (most recent call last):
		...
		IndexError: ...
	)", nb::sig("def set(self, index: slice, value: collections.abc.Iterable[T]) -> PSequence[T]"));

	cls.def("mset", [](Sequence seq, nb::args args) {
		for(auto arg = args.begin(); !(arg == args.end()); ++arg) {
			Py_ssize_t idx;
			if(nb::try_cast<Py_ssize_t>(*arg, idx)) {
				if(++arg == args.end()) throw nb::index_error
					("extra index without matching value");
				seq = seq.set(pyr::adjust_index<Py_ssize_t>
					(seq.size(), idx), nb::cast(*arg));
			} else {
				nb::tuple tp = nb::cast<nb::tuple>(*arg);
				seq = seq.set(pyr::adjust_index<Py_ssize_t>
					(seq.size(), nb::cast<Py_ssize_t>(tp[0])), tp[1]);
			}
		}
		return seq;
	}, R"(
		Replace multiple elements

		:math:`O(k\log{n})`

		:raises IndexError: if any index is out of bounds

		>>> psequence([1,2,3,4]).mset(2, 0, 3, 5)
		psequence([1, 2, 0, 5])
		>>> psequence([1,2,3,4]).mset((2, 0), (3, 5))
		psequence([1, 2, 0, 5])
		>>> psequence([1,2,3,4]).mset(2, 0, 3)
		Traceback (most recent call last):
		...
		IndexError: ...
		>>> psequence([1,2,3,4]).mset(5, 0)
		Traceback (most recent call last):
		...
		IndexError: ...
	)", nb::sig("def mset(self, *values: typing.Union[int,T,Tuple[int,T]]) -> PSequence[T]"));

	cls.def("insert", [](const Sequence& seq, Py_ssize_t index, const nb::object& value) {
		if(index < 0) index += seq.size();
		if(index < 0) return seq.push_front(value);
		if(index >= seq.size()) return seq.push_back(value);
		return seq.insert(index, value);
	}, R"(
		Insert an element at the specified position

		:math:`O(\log(\min(i,n−i)))`

		>>> psequence([1,2,3,4]).insert(2, 0)
		psequence([1, 2, 0, 3, 4])
		>>> psequence([1,2,3,4]).insert(-10, 0)
		psequence([0, 1, 2, 3, 4])
		>>> psequence([1,2,3,4]).insert(10, 0)
		psequence([1, 2, 3, 4, 0])
	)", nb::sig("def insert(self, index: int, value: T) -> PSequence[T]"));

	cls.def("delete", [](const Sequence& seq, Py_ssize_t index) {
		return seq.erase(pyr::adjust_index<Py_ssize_t>(seq.size(), index));
	}, nb::sig("def delete(self, index: int) -> PSequence[T]"));
	cls.def("delete", [](const Sequence& seq, const nb::slice& slice) {
		auto [start, stop, step, count] = slice.compute(seq.size());
		return seq.erase(start, stop, step);
	}, R"(
		Delete the element(s) at the specified position(s)

		Time complexities for `n.delete(i)`:

		- :math:`O(\log(\min(i,n−i)))` deleting a single item.
		- :math:`O(\log{n})` deleting a contiguous slice.
		- :math:`O(\frac{n}{k}\log{k})` deleting a non-contiguous slice.

		:raises IndexError: if the index is out of bounds

		>>> psequence([1,2,3,4]).delete(2)
		psequence([1, 2, 4])
		>>> psequence([1,2,3,4,5]).delete(slice(1,4))
		psequence([1, 5])
		>>> psequence([1,2,3,4]).delete(5)
		Traceback (most recent call last):
		...
		IndexError: ...
	)", nb::sig("def delete(self, index: slice) -> PSequence[T]"));

	cls.def("remove", [](Sequence seq, const nb::object& value) {
		Py_ssize_t index = nb::cast<Py_ssize_t>
			(nb::cast(seq).attr("index")(value));
		return seq.erase(index);
	}, R"(
		Remove the first occurance of value

		:math:`O(n)`

		:raises ValueError: if the value is not in the sequence

		>>> psequence([1,2,2,3,4]).remove(2)
		psequence([1, 2, 3, 4])
		>>> psequence([1,2,3,4]).remove(0)
		Traceback (most recent call last):
		...
		ValueError: ...
	)", nb::sig("def remove(self, value: T) -> PSequence[T]"));

	cls.def("__mul__", [](const Sequence& seq, Py_ssize_t times) {
		return seq.repeat(size_t(std::max(Py_ssize_t(0), times)));
	}, R"(
		Repeat the sequence k times

		:math:`O(\log{n}\log{k})`

		>>> psequence([1,2,3]) * 3
		psequence([1, 2, 3, 1, 2, 3, 1, 2, 3])
		>>> 3 * psequence([1,2,3])
		psequence([1, 2, 3, 1, 2, 3, 1, 2, 3])
	)", nb::sig("def __mul__(self, times: int) -> PSequence[T]"));
	cls.def("__rmul__", [](nb::object seq, nb::args args, nb::kwargs kwargs) {
		return seq.attr("__mul__")(*args, **kwargs);
	}, nb::sig("def __rmul__(self, times: int) -> PSequence[T]"),
		"Alias for :meth:`__mul__`");

	cls.def("__iter__", [](const Sequence& seq) {
		return nb::make_iterator(
			nb::type<Sequence>(), "Iterator",
			seq.begin(), seq.end());
	}, R"(
		Create an iterator

		:math:`O(1)`

		Iterating the entire sequence is :math:`O(n)`.

		>>> i = iter(psequence([1,2,3]))
		>>> next(i)
		1
		>>> next(i)
		2
		>>> next(i)
		3
		>>> next(i)
		Traceback (most recent call last):
		...
		StopIteration
	)", nb::sig("def __iter__(self) -> typing.Iterator[T]"));

	cls.def("__reversed__", [](const Sequence& seq) {
		return nb::make_iterator(
			nb::type<Sequence>(), "ReverseIterator",
			seq.rbegin(), seq.rend());
	}, R"(
		Create a reverse iterator

		:math:`O(1)`

		Iterating the entire sequence is :math:`O(n)`.

		>>> i = reversed(psequence([1,2,3]))
		>>> next(i)
		3
		>>> next(i)
		2
		>>> next(i)
		1
		>>> next(i)
		Traceback (most recent call last):
		...
		StopIteration
	)", nb::sig("def __reversed__(self) -> typing.Iterator[T]"));

	cls.def("__len__", &Sequence::size);

	cls.def("__setstate__", [mod](Sequence& seq, nb::object xs) {
		new (&seq) Sequence(nb::cast<Sequence>(mod.attr("psequence")(xs)));
	}, R"(
		Support method for :mod:`python:pickle`

		:math:`O(n)`

		>>> import pickle
		>>> pickle.loads(pickle.dumps(psequence([1,2,3,4])))
		psequence([1, 2, 3, 4])
	)");
	cls.def("__getstate__", [](nb::object seq) {
		return seq.attr("totuple")();
	}, R"(
		Support method for :mod:`python:pickle`

		:math:`O(n)`

		>>> import pickle
		>>> pickle.loads(pickle.dumps(psequence([1,2,3,4])))
		psequence([1, 2, 3, 4])
	)");

	// cls.def("__repr__", [](const Sequence& seq) {
		// return seq.pretty();
	// });
	cls.def("__repr__", [](const Sequence& seq) {
		std::ostringstream out;
		using Iter = pyr_nb::repr_iterator<typename Sequence::iterator>;
		out << pyr::ShowIterator
			(Iter(seq.begin()), Iter(seq.end()), "psequence([", "])", ", ");
		return out.str();
	});

	cls.def("__str__", nb::repr,
		"Alias for :meth:`__repr__`");

	cls.def("appendright", &Sequence::push_back, R"(
		Add an element to the right end

		:math:`O(1)`

		>>> psequence([1,2,3]).append(4)
		psequence([1, 2, 3, 4])
		>>> psequence([1,2,3]).appendright(4)
		psequence([1, 2, 3, 4])
	)", nb::sig("def appendright(self, value: T) -> PSequence[T]"));

	cls.def("appendleft", &Sequence::push_front, R"(
		Add an element to the left end

		:math:`O(1)`

		>>> psequence([1,2,3]).appendleft(0)
		psequence([0, 1, 2, 3])
	)", nb::sig("def appendleft(self, value: T) -> PSequence[T]"));

	cls.def("append", [](nb::object seq, nb::args args, nb::kwargs kwargs) {
		return seq.attr("appendright")(*args, **kwargs);
	}, nb::sig("def append(self, value: T) -> PSequence[T]"),
		"Alias for :meth:`appendright`");

	cls.def("splitat", [](const Sequence& seq, Py_ssize_t index)
	-> std::pair<Sequence, Sequence> {
		if(index < 0) index += seq.size();
		if(index <= 0) return {Sequence(), seq};
		if(index >= seq.size()) return {seq, Sequence()};
		auto [left, value, right] = seq.split(index);
		return {left, right.push_front(value)};
	}, R"(
		Split a sequence at a given position

		:math:`O(\log(\min(i,n−i)))`

		Equivalent to ``(seq.take(i), seq.drop(i))``.
		Does not raise :exc:`python:IndexError`, unlike :meth:`view`.

		>>> psequence([1,2,3,4]).splitat(2)
		(psequence([1, 2]), psequence([3, 4]))
		>>> psequence([1,2,3,4]).splitat(5)
		(psequence([1, 2, 3, 4]), psequence([]))
		>>> psequence([1,2,3,4]).splitat(-1)
		(psequence([1, 2, 3]), psequence([4]))
		>>> psequence([1,2,3,4]).splitat(-5)
		(psequence([]), psequence([1, 2, 3, 4]))
	)", nb::sig("def splitat(self, index: int) -> typing.Tuple[PSequence[T], PSequence[T]]"));

	cls.def("chunksof", [](Sequence seq, Py_ssize_t chunk) {
		if(chunk-- <= 0) throw std::out_of_range("chunk size must be positive");
		Sequence chunks;
		while(chunk < seq.size()) {
			auto [left, value, right] = seq.split(chunk);
			chunks = chunks.push_back(nb::cast(left.push_back(value)));
			seq = std::move(right);
		}
		if(!seq.empty())
			chunks = chunks.push_back(nb::cast(seq));
		return chunks;
	}, R"(
		Split the sequence into chunks

		:math:`O(\frac{n}{k}\log{n})`

		>>> psequence([1,2,3,4,5,6,7,8]).chunksof(3)
		psequence([psequence([1, 2, 3]), psequence([4, 5, 6]), psequence([7, 8])])
	)", nb::sig("def chunksof(self, chunk: int) -> PSequence[PSequence[T]]"));

	cls.def_prop_ro("left", &Sequence::front, R"(
		Extract the first element

		:math:`O(1)`

		:raises IndexError: if the sequence is empty

		>>> psequence([1,2,3,4]).left
		1
		>>> psequence([]).left
		Traceback (most recent call last):
		...
		IndexError: ...
	)", nb::sig("def left(self) -> T"));

	cls.def_prop_ro("right", &Sequence::back, R"(
		Extract the last element

		:math:`O(1)`

		:raises IndexError: if the sequence is empty

		>>> psequence([1,2,3,4]).right
		4
		>>> psequence([]).right
		Traceback (most recent call last):
		...
		IndexError: ...
	)", nb::sig("def right(self) -> T"));

	cls.def("viewleft", &Sequence::view_front, R"(
		Analyse the left end

		:math:`O(1)`

		:raises IndexError: if the sequence is empty

		>>> psequence([1,2,3,4]).viewleft()
		(1, psequence([2, 3, 4]))
		>>> psequence([]).viewleft()
		Traceback (most recent call last):
		...
		IndexError: ...
	)", nb::sig("def viewleft(self) -> typing.Tuple[PSequence, T]"));

	cls.def("viewright", &Sequence::view_back, R"(
		Analyse the right end

		:math:`O(1)`

		:raises IndexError: if the sequence is empty

		>>> psequence([1,2,3,4]).viewright()
		(psequence([1, 2, 3]), 4)
		>>> psequence([]).viewright()
		Traceback (most recent call last):
		...
		IndexError: ...
	)", nb::sig("def viewright(self) -> typing.Tuple[T, PSequence]"));

	cls.def("view", [](Sequence seq, const nb::args& args) {
		nb::list views;
		Py_ssize_t size = seq.size(), last = -1;
		for(auto i = args.begin(); i != args.end(); ++i) {
			Py_ssize_t idx = pyr::adjust_index<Py_ssize_t>
				(size, nb::cast<Py_ssize_t>(*i));
			if(last >= idx) throw nb::index_error
				("indices must be in ascending order");
			auto [left, value, right] = seq.split(idx - last - 1);
			views.append(nb::cast(left));
			views.append(value);
			seq = std::move(right);
			last = idx;
		}
		views.append(nb::cast(seq));
		return views;
	}, R"(
		Split a sequence on the given position(s)

		:math:`O(k\log{n})`

		Useful for pattern matching:

		>>> # doctest: +SKIP
		... match seq.view(0, 1, 4):
		...   case (_, x0, _, x1, x_2_3, x4, _, rest):
		...     x0 == seq[0], x1 = seq[1], x_2_3 == seq[2:4]
		...     x_4 == seq[4], rest = seq[5:]

		Equivalent to ``(seq[:i1], seq[i1], seq[i1+1:i2],
		seq[i2], seq[i2+1:i3], ..., seq[in+1:])``.

		:raises IndexError: if any index is out of bounds

		>>> psequence([1,2,3,4]).view(0)
		[psequence([]), 1, psequence([2, 3, 4])]
		>>> psequence([1,2,3,4]).view(1)
		[psequence([1]), 2, psequence([3, 4])]
		>>> psequence([1,2,3,4]).view(1, 3)
		[psequence([1]), 2, psequence([3]), 4, psequence([])]
		>>> psequence([1,2,3,4]).view(5)
		Traceback (most recent call last):
		...
		IndexError: ...
	)");

	cls.def("reverse", &Sequence::reverse, R"(
		Reverse the sequence

		:math:`O(n)`

		>>> psequence([1,2,3,4]).reverse()
		psequence([4, 3, 2, 1])
	)", nb::sig("def reverse(self) -> PSequence[T]"));

	cls.def("tolist", [](const Sequence& seq) {
		PyObject* xs = PyList_New(seq.size());
		size_t n = 0; for(auto x: seq)
			PyList_SET_ITEM(xs, n++, x.inc_ref().ptr());
		return nb::steal(xs);
	}, R"(
		Convert the sequence to a :class:`python:list`

		:math:`O(n)`

		>>> psequence([1,2,3,4]).tolist()
		[1, 2, 3, 4]
	)", nb::sig("def tolist(self) -> typing.List[T]"));

	cls.def("totuple", [](const Sequence& seq) {
		PyObject* xs = PyTuple_New(seq.size());
		size_t n = 0; for(auto x: seq)
			PyTuple_SET_ITEM(xs, n++, x.inc_ref().ptr());
		return nb::steal(xs);
	}, R"(
		Convert the sequence to a :class:`python:tuple`

		:math:`O(n)`

		>>> psequence([1,2,3,4]).totuple()
		(1, 2, 3, 4)
	)", nb::sig("def totuple(self) -> typing.Tuple[T]"));

	cls.def("sort", [mod](nb::object seq, nb::args args, nb::kwargs kwargs) {
		nb::object xs = seq.attr("tolist")();
		xs.attr("sort")(*args, **kwargs);
		return mod.attr("psequence")(xs);
	}, R"(
		Creat a sorted copy of the sequence

		:math:`O(n\log{n})`

		Arguments are the same as :meth:`python:list.sort`.

		>>> psequence([3,1,4,2]).sort()
		psequence([1, 2, 3, 4])
		>>> psequence([3,1,4,2]).sort(reverse=True)
		psequence([4, 3, 2, 1])
	)", nb::sig("def sort(self, *args, **kwargs) -> PSequence[T]"));

	cls.def("transform", [](nb::object seq, nb::args args) {
		static nb::object transform;
		if(!transform.is_valid())
			new (&transform) nb::object(nb::module_::import_
				("pyrsistent._transformations").attr("transform"));
		return transform(seq, args);
	}, nb::sig("def transform(self, *args, **kwargs) -> PSequence[T]"), R"(
		Apply one or more transformations

		>>> from pyrsistent import ny
		>>> psequence([1,2,3,4]).transform([ny], lambda x: x*2)
		psequence([2, 4, 6, 8])
	)", nb::sig("def transform(self, *args, **kwargs) -> PSequence[T]"));

	cls.def("__hash__", [](const Sequence& seq) {
		return std::hash<Sequence>()(seq);
	}, R"(
		Calculate a hash

		:math:`O(n)`

		>>> hash(psequence([1,2,3])) == hash(psequence([1,2,3]))
		True
		>>> hash(psequence([1,2,3])) == hash(psequence([3,2,1]))
		False
	)", nb::sig("def __hash__(self) -> int"));

	auto abc = nb::module_::import_("collections.abc");
	abc.attr("Sequence").attr("register")(cls);
	cls.attr("count") = abc.attr("Sequence").attr("count");
	cls.attr("__contains__") = abc.attr("Sequence").attr("__contains__");
	abc.attr("Hashable").attr("register")(cls);

	auto evo = nb::class_<Evolver>(mod, "PSequenceEvolver", nb::is_generic(), R"(
		Evolver for :class:`PSequence`

		The evolver acts as a mutable view of the sequence with "transaction
		like" semantics. No part of the underlying sequence is updated, it is
		still fully immutable. Furthermore multiple evolvers created from the
		same psequence do not interfere with each other.

		You may want to use an evolver instead of working directly with
		:class:`PSequence` in the following cases:

		- Multiple updates are done to the same sequence and the
			intermediate results are of no interest. In this case using an
			evolver may be easier to work with.
		- You need to pass a sequence into a legacy function or a function
			that you have no control over which performs in place mutations
			of lists. In this case pass an evolver instance instead and then
			create a new psequence from the evolver once the function returns.

		The following example illustrates a typical workflow when working with
		evolvers:

		Create the evolver and perform various mutating updates to it:

		>>> seq1 = psequence([1,2,3,4,5])
		>>> evo1 = seq1.evolver()
		>>> evo1[1] = 22
		>>> _ = evo1.append(6)
		>>> _ = evo1.extend([7,8,9])
		>>> evo1[8] += 1
		>>> evo1
		psequence([1, 22, 3, 4, 5, 6, 7, 8, 10]).evolver()

		The underlying psequence remains the same:

		>>> seq1
		psequence([1, 2, 3, 4, 5])

		The changes are kept in the evolver. An updated psequence can be
		created using the persistent() function on the evolver.

		>>> seq2 = evo1.persistent()
		>>> seq2
		psequence([1, 22, 3, 4, 5, 6, 7, 8, 10])

		The new psequence will share data with the original psequence in the
		same way that would have been done if only using operations on the
		sequence.

		>>> evo = psequence([1,2,3,4]).evolver()
		>>> evo[2] = 0
		>>> evo
		psequence([1, 2, 0, 4]).evolver()
	)", nb::sig("class PSequenceEvolver(collections.abc.MutableSequence[T])"));

	evo.def("persistent", [](const Evolver& evo) { return evo.seq; }, R"(
		Extract the sequence from the evolver

		:math:`O(1)`

		>>> seq = psequence([1,2,3,4])
		>>> seq.evolver().persistent()
		psequence([1, 2, 3, 4])
	)", nb::sig("def persistent(self) -> PSequence[T]"));

	cls.def("evolver", [](const Sequence& seq) { return Evolver{seq}; }, R"(
		Create a :class:`PSequenceEvolver`

		:math:`O(1)`
	)", nb::sig("def evolver(self) -> PSequenceEvolver[T]"));

	for(auto name: {
		"extendright", "extendleft", "appendright", "appendleft",
		"set", "mset", "delete", "sort", "transform",
	}) {
		auto [ func, doc, sig ] = pyr_nb::inherit_docstring(
			cls, name, evo, name, "Mutable version of", std::nullopt);
		evo.def(name, [func=func](Evolver& evo, nb::args args, nb::kwargs kwargs) {
			evo.seq = nb::cast<Sequence>(func(nb::cast(evo.seq), *args, **kwargs));
			return evo;
		}, doc.c_str(), nb::sig(sig.c_str()));
	}

	for(auto name: {
		"extend", "append", "insert", "remove", "reverse",
	}) {
		auto [ func, doc, sig ] = pyr_nb::inherit_docstring(
			cls, name, evo, name, "Mutable version of", [](std::string str)
			{ return std::regex_replace(str, std::regex("\\s*->\\s*.*"), ""); });
		evo.def(name, [func=func](Evolver& evo, nb::args args, nb::kwargs kwargs) {
			evo.seq = nb::cast<Sequence>(func(nb::cast(evo.seq), *args, **kwargs));
		}, doc.c_str(), nb::sig(sig.c_str()));
	}

	for(auto [source, target] : {
		std::make_pair("set", "__setitem__"),
		std::make_pair("delete", "__delitem__"),
		std::make_pair("extend", "__iadd__"),
	}) {
		auto [ func, doc, sig ] = pyr_nb::inherit_docstring(
			cls, source, evo, target, "Mutable version of", std::nullopt);
		evo.def(target, [func=func](Evolver& evo, nb::args args, nb::kwargs kwargs) {
			evo.seq = nb::cast<Sequence>(func(nb::cast(evo.seq), *args, **kwargs));
			return evo;
		}, doc.c_str(), nb::sig(sig.c_str()));
	}

	for(auto name: {
		"__eq__", "__ne__", "__lt__", "__gt__", "__le__", "__ge__",
		"index", "__iter__", "__reversed__", "__getstate__", "count", "tolist",
		"totuple", "__hash__", "__len__", "__getitem__", "__contains__",
	}) {
		auto [ func, doc, sig ] = pyr_nb::inherit_docstring(
			cls, name, evo, name, "Alias of", std::nullopt);
		evo.def(name, [func=func](Evolver& evo, nb::args args, nb::kwargs kwargs) {
			return func(nb::cast(evo.seq), *args, **kwargs);
		}, doc.c_str(), nb::sig(sig.c_str()));
	}

	for(auto name: {"left", "right"}) {
		auto [ func, doc, sig ] = pyr_nb::inherit_docstring(
			cls, name, evo, name, "Alias", "(self) -> T");
		evo.def_prop_ro(name, [name](Evolver& evo) {
			return nb::cast(evo.seq).attr(name);
		}, doc.c_str(), nb::sig(sig.c_str()));
	}

	for(auto name: {"__setstate__"}) {
		auto [ func, doc, sig ] = pyr_nb::inherit_docstring(
			cls, name, evo, name, "Evolver version of", std::nullopt);
		evo.def(name, [mod](Evolver& evo, nb::object xs) {
			new (&evo) Evolver{Sequence(
				nb::cast<Sequence>(mod.attr("psequence")(xs)))};
		}, doc.c_str(), nb::sig(sig.c_str()));
	}

	for(auto name: {"__add__", "__radd__", "__mul__", "__rmul__"}) {
		auto [ func, doc, sig ] = pyr_nb::inherit_docstring(
			cls, name, evo, name, "Evolver version of", std::nullopt);
		evo.def(name, [func=func](Evolver& evo, nb::args args, nb::kwargs kwargs) {
			return Evolver{nb::cast<Sequence>(func(nb::cast(evo.seq), *args, **kwargs))};
		}, doc.c_str(), nb::sig(sig.c_str()));
	}

	for(auto name: {"__repr__", "__str__"}) {
		auto [ func, doc, sig ] = pyr_nb::inherit_docstring(
			cls, name, evo, name, "Alias of", std::nullopt);
		evo.def(name, [func=func](Evolver& evo) {
				return func(nb::cast(evo.seq)) + nb::str(".evolver()");
		}, doc.c_str(), nb::sig(sig.c_str()));
	}

	for(auto name: {"splitat"}) {
		auto [ func, doc, sig ] = pyr_nb::inherit_docstring(
			cls, name, evo, name, "Evolver version of", std::nullopt);
		evo.def(name, [func=func](Evolver& evo, nb::args args, nb::kwargs kwargs) {
			nb::object xs = func(nb::cast(evo.seq), *args, **kwargs);
			return nb::make_tuple(Evolver{nb::cast<Sequence>(xs[0])},
				Evolver{nb::cast<Sequence>(xs[1])});
		}, doc.c_str(), nb::sig(sig.c_str()));
	}

	for(auto name: {"chunksof"}) {
		auto [ func, doc, sig ] = pyr_nb::inherit_docstring(
			cls, name, evo, name, "Evolver version of", std::nullopt);
		evo.def(name, [func=func](Evolver& evo, nb::args args, nb::kwargs kwargs) {
			Sequence seq = nb::cast<Sequence>(func(nb::cast(evo.seq), *args, **kwargs));
			std::function<nb::object(nb::object)> tf = [](nb::object seq)
				{ return nb::cast(Evolver{nb::cast<Sequence>(seq)}); };
			return Evolver{seq.transform(tf)};
		}, doc.c_str(), nb::sig(sig.c_str()));
	}

	for(auto name: {"viewleft"}) {
		auto [ func, doc, sig ] = pyr_nb::inherit_docstring(
			cls, name, evo, name, "Evolver version of", std::nullopt);
		evo.def(name, [func=func](Evolver& evo) {
			nb::object view = func(nb::cast(evo.seq));
			return std::make_pair(nb::cast(view[0]), Evolver{nb::cast<Sequence>(view[1])});
		}, doc.c_str(), nb::sig(sig.c_str()));
	}

	for(auto name: {"viewright"}) {
		auto [ func, doc, sig ] = pyr_nb::inherit_docstring(
			cls, name, evo, name, "Evolver version of", std::nullopt);
		evo.def(name, [func=func](Evolver& evo) {
			nb::object view = func(nb::cast(evo.seq));
			return std::make_pair(Evolver{nb::cast<Sequence>(view[0])}, nb::cast(view[1]));
		}, doc.c_str(), nb::sig(sig.c_str()));
	}

	for(auto name: {"view"}) {
		auto [ func, doc, sig ] = pyr_nb::inherit_docstring(
			cls, name, evo, name, "Evolver version of", std::nullopt);
		evo.def(name, [func=func](Evolver& evo, nb::args args) {
			nb::object views = func(nb::cast(evo.seq), *args);
			for(Py_ssize_t i = nb::len(views) - 1; i >= 0; i -= 2)
				views[i] = nb::cast(Evolver{nb::cast<Sequence>(views[i])});
			return views;
		}, doc.c_str(), nb::sig(sig.c_str()));
	}

	evo.def("clear", [](Evolver& evo) {
		evo.seq = Sequence();
	}, R"(
		Remove all items from the sequence

		:math:`O(1)`

		>>> seq = psequence([1,2,3,4]).evolver()
		>>> _ = seq.clear()
		>>> seq
		psequence([]).evolver()
	)", nb::sig("def clear(self)"));

	evo.def("pop", []() { throw nb::next_overload(); },
		nb::sig("def pop(self, index:int) -> T"));
	evo.def("pop", [](Evolver& evo, nb::object index) {
		nb::object value = nb::cast(evo.seq).attr("__getitem__")(index);
		nb::cast(evo).attr("__delitem__")(index);
		return value;
	}, "index"_a = -1, R"(
		Remove and return an element at the specified index

		See :meth:`PSequence.delete` and :meth:`list.pop`.

		:raises IndexError: if the sequence is empty or the index is out of bounds

		>>> seq = psequence([1,2,3,4]).evolver()
		>>> seq.pop()
		4
		>>> seq
		psequence([1, 2, 3]).evolver()
		>>> seq.pop(1)
		2
		>>> seq
		psequence([1, 3]).evolver()
	)", nb::sig("def pop(self, index:slice) -> PSequenceEvolver[T]"));

	// def __setitem__(self, index: int, value: T) -> PSequenceEvolver[T]:
	// def __delitem__(self, index: int) -> PSequenceEvolver[T]:
	// def __getitem__(self, index: int) -> T:

	abc.attr("MutableSequence").attr("register")(evo);
	cls.attr("count") = abc.attr("MutableSequence").attr("count");
	cls.attr("__contains__") = abc.attr("MutableSequence").attr("__contains__");

	mod.def("psequence", []() { return Sequence(); },
		nb::sig("def psequence() -> PSequence[typing.Any]"));
	mod.def("psequence", [](const Sequence& seq) { return seq; },
		nb::sig("def psequence(items: PSequence[T]) -> PSequence[T]"));
	mod.def("psequence", [](const Evolver& evo) { return evo.seq; },
		nb::sig("def psequence(items: PSequenceEvolver[T]) -> PSequence[T]"));
	mod.def("psequence", [](const nb::object& xs) {
		using Iter = pyr_nb::object_iterator<decltype(xs.begin())>;
		size_t size;
		try {
			size = nb::len(xs);
		} catch(const nb::python_error&) {
			std::vector<nb::object> objs(Iter(xs.begin()), Iter(xs.end()));
			return Sequence(objs.size(), objs.begin());
		}
		return Sequence(size, Iter(xs.begin()));
	}, R"(
		Create a :class:`PSequence` from the given items

		:math:`O(n)`

		>>> psequence()
		psequence([])
		>>> psequence([1,2,3,4])
		psequence([1, 2, 3, 4])
	)", nb::sig("def psequence(items: collections.abc.Iterable[T]) -> PSequence[T]"));

	mod.def("sq", [](const nb::args& xs) {
		using Iter = pyr_nb::object_iterator<decltype(xs.begin())>;
		return Sequence(xs.size(), Iter(xs.begin()));
	}, R"(
		Shorthand for :func:`psequence`

		>>> sq(1,2,3,4)
		psequence([1, 2, 3, 4])
	)", nb::sig("def sq(*items: T) -> PSequence[T]"));
}

