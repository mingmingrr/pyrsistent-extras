#include <rapidcheck.h>
#include <gtest/gtest.h>
#include <rapidcheck/gtest.h>

#include <vector>
#include <algorithm>

#include "_psortedmap.hpp"

namespace pyr = pyrsistent;

template<typename Value>
using SortedMap = pyr::SortedMap<Value>;
template<typename Value>
using Node = typename SortedMap<Value>::Node;
template<typename Value>
using NodePtr = typename SortedMap<Value>::NodePtr;

template struct pyr::SortedMap<int>;

template<typename Value>
struct rc::Arbitrary<pyr::Sequence<Value>> {
	static rc::Gen<NodePtr<Value>> arbitrary_node(int size) {
		if(size == 0) return rc::gen::map(rc::gen::arbitrary<Value>(),
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

	static rc::Gen<Sequence<Value>> arbitrary() {
		return rc::gen::withSize([](int size) -> rc::Gen<Sequence<Value>> {
			return rc::gen::mapcat(rc::gen::inRange<int>(0, size + 1),
				[](int size) { return rc::gen::map(arbitrary_node(size),
					[](NodePtr<Value>&& node) { return Sequence<Value>(std::move(tree)); }); }
			);
		});
	}
};

template<class... Ts>
struct overloaded : Ts... { using Ts::operator()...; };
template<class... Ts>
overloaded(Ts...) -> overloaded<Ts...>;

