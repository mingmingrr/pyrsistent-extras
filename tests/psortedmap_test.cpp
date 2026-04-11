#include <rapidcheck.h>
#include <gtest/gtest.h>
#include <rapidcheck/gtest.h>

#include <map>
// #include <vector>
#include <algorithm>

#include "_psortedmap.hpp"

namespace pyr = pyrsistent;

template<typename Key, typename Value>
using SortedMap = pyr::SortedMap<Key, Value>;
template<typename Key, typename Value>
using Node = typename SortedMap<Key, Value>::Node;
template<typename Key, typename Value>
using NodePtr = typename SortedMap<Key, Value>::NodePtr;

// template struct pyr::SortedMap<int, int>;

template<typename Key, typename Value>
struct rc::Arbitrary<SortedMap<Key, Value>> {
	using Elems = std::vector<std::pair<Key, Value>>;
	static rc::Gen<NodePtr<Key, Value>>
	arbitrary_node(std::shared_ptr<Elems> elems, size_t left, size_t right) {
		if(left == right) return rc::gen::just<NodePtr<Key, Value>>(nullptr);
		return rc::gen::mapcat(rc::gen::inRange(left, right),
			[=](size_t index) { return rc::gen::apply(
				[=](auto lnode, auto rnode) { return Node<Key, Value>::join(
					elems->at(index).first, elems->at(index).second, lnode, rnode); },
				arbitrary_node(elems, left, index),
				arbitrary_node(elems, index + 1, right)); });
	}
	static rc::Gen<SortedMap<Key, Value>> arbitrary() {
		return rc::gen::mapcat(rc::gen::arbitrary<std::map<Key, Value>>(),
		[](auto gens) { auto elems = std::make_shared<Elems>(gens.begin(), gens.end());
			return rc::gen::map(arbitrary_node(elems, 0, elems->size()),
			[](auto node) { return SortedMap<Key, Value>(std::move(node)); }); });
	}
};

// LCOV_EXCL_START
namespace std {
	template<typename Value>
	void showValue(const std::shared_ptr<Value>& ptr, std::ostream& out)
		{ if(ptr) out << *ptr; else out << "<nullptr>"; }
}
namespace pyrsistent {
	template<typename Key, typename Value>
	void showValue(const SortedMap<Key, Value>& smap, std::ostream& out)
		{ smap.pretty(out); }
	template<typename Key, typename Value>
	void showValue(const Node<Key, Value>& node, std::ostream& out)
		{ Node<Key, Value>::pretty(node, out, 0); }
}
// LCOV_EXCL_STOP

template<typename Key, typename Value, bool Assert=true>
size_t check(
	const NodePtr<Key, Value>& node,
	const std::optional<Key>& low,
	const std::optional<Key>& high,
	std::map<Key, Value>& elems
) {
	if(!node) return 0;
	if(Assert) RC_ASSERT(elems.find(node->key) == elems.end());
	if(Assert && low) RC_ASSERT(*low < node->key);
	if(Assert && high) RC_ASSERT(*high > node->key);
	auto lsize = check(node->left, low, std::make_optional(node->key), elems);
	elems.insert(std::make_pair(node->key, node->value));
	auto rsize = check(node->right, std::make_optional(node->key), high, elems);
	if(Assert && !lsize) RC_ASSERT(rsize <= 2);
	if(Assert && !rsize) RC_ASSERT(lsize <= 2);
	if(Assert && lsize && rsize) {
		float ratio = lsize > rsize ? float(lsize) / rsize : float(rsize) / lsize;
		RC_ASSERT(ratio <= (SortedMap<Key, Value>::delta));
	}
	return lsize + rsize + 1;
}

template<typename Key, typename Value, bool Assert=true>
std::map<Key, Value> check(const SortedMap<Key, Value>& smap) {
	std::map<Key, Value> elems;
	size_t size = check<Key, Value, Assert>(
		smap.node, std::nullopt, std::nullopt, elems);
	if(Assert) RC_ASSERT(size == elems.size());
	return elems;
} // LCOV_EXCL_LINE

template<typename Key, typename Value>
std::map<Key, Value> tomap(const SortedMap<Key, Value>& smap)
	{ return check<Key, Value, false>(smap); }

template<typename Key, typename Value>
std::optional<Value> lookup(const std::map<Key, Value>& elems, const Key& key)
	{ return elems.count(key) ? std::make_optional(elems.at(key)) : std::nullopt; }

RC_GTEST_PROP(SortedMap, check, (SortedMap<int, int> smap)) {
	RC_ASSERT(check(smap) == tomap(smap));
}

RC_GTEST_PROP(SortedMap, empty, (SortedMap<int, int> smap)) {
	auto elems = tomap(smap);
	RC_ASSERT((bool)smap == (bool)elems.size());
	RC_ASSERT(smap.empty() == elems.empty());
}

RC_GTEST_PROP(SortedMap, size, (SortedMap<int, int> smap)) {
	RC_ASSERT(smap.size() == tomap(smap).size());
}

RC_GTEST_PROP(SortedMap, insert, (SortedMap<int, int> smap, int k, int v)) {
	auto elems = tomap(smap);
	elems[k] = v;
	RC_ASSERT(check(smap.insert(k, v)) == elems);
}

RC_GTEST_PROP(SortedMap, at, (SortedMap<int, int> smap, int k)) {
	auto elems = tomap(smap);
	RC_ASSERT(smap.at(k) == lookup(elems, k));
}

RC_GTEST_PROP(SortedMap, pop, (SortedMap<int, int> smap, int k)) {
	auto elems = tomap(smap);
	auto [value, smap1] = smap.pop(k);
	auto expect = lookup(elems, k);
	elems.erase(k);
	RC_ASSERT(value == expect);
	RC_ASSERT(check(smap1) == elems);
}

RC_GTEST_PROP(SortedMap_Iterator, tolist, (SortedMap<int, int> smap)) {
	using Array = std::vector<std::pair<int, int>>;
	std::map<int, int> elems = tomap(smap);
	Array flats = Array(elems.begin(), elems.end());
	RC_ASSERT((Array(smap.begin(), smap.end())) == flats);
}

// RC_GTEST_PROP(SortedMap_RIterator, tolist, (SortedMap<int, int> smap)) {
	// using Array = std::vector<std::pair<int, int>>;
	// auto elems = tomap(smap);
	// auto flats = Array(elems.rbegin(), elems.rend());
	// RC_ASSERT((Array(smap.rbegin(), smap.rend())) == flats);
// }

