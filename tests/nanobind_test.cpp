#include <rapidcheck.h>
#include <gtest/gtest.h>
#include <rapidcheck/gtest.h>

#include <nanobind/nanobind.h>
#include <nanobind/operators.h>
#include <nanobind/make_iterator.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include "_nanobind.hpp"

namespace nb = nanobind;
namespace pyr = pyrsistent;
namespace pyr_nb = pyrsistent::nanobind;

template<typename Value>
struct rc::Arbitrary<pyr_nb::object_iterator<nb::object>> {
	static rc::Gen<NodePtr<Value>> arbitrary_node(int depth) {
		if(depth == 0) return rc::gen::map(rc::gen::arbitrary<Value>(),
			[](Value&& value) { return Node<Value>::make(std::move(value)); });
		return rc::gen::oneOf(
			rc::gen::lazy([=]() { return rc::gen::apply(
				Node<Value>::template make<NodePtr<Value>, NodePtr<Value>>,
				arbitrary_node(depth-1), arbitrary_node(depth-1)); }),
			rc::gen::lazy([=]() { return rc::gen::apply(
				Node<Value>::template make<NodePtr<Value>, NodePtr<Value>, NodePtr<Value>>,
				arbitrary_node(depth-1), arbitrary_node(depth-1), arbitrary_node(depth-1)); })
		);
	}
};

RC_GTEST_PROP(Pyrsistent_Nanobind, object_iterator, ()) {
}

