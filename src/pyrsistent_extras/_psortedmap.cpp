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

#include "_psortedmap.hpp"
#include "_utility.hpp"
#include "_nanobind.hpp"

namespace pyr = pyrsistent;
namespace pyr_nb = pyrsistent::nanobind;

using SortedMap = pyr::SortedMap<nb::object, nb::object>;

struct Evolver { SortedMap map; };

NB_MODULE(_psortedmap, mod) {
	mod.attr("K") = nb::type_var("K");
	mod.attr("V") = nb::type_var("V");

	auto cls = nb::class_<SortedMap>(mod, "PSortedMap", nb::is_generic(), R"(
	)", nb::sig("class PSortedMap(collections.abc.Mapping[K, V], collections.abc.Hashable)"));
	cls.def(nb::init<>());
}

