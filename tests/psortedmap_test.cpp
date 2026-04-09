#include <rapidcheck.h>
#include <gtest/gtest.h>
#include <rapidcheck/gtest.h>

#include <map>
#include <vector>
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
	using Cache = std::vector<std::pair<Key, Value>>;
	static rc::Gen<NodePtr<Key, Value>> arbitrary_node(
		typename Cache::iterator left, typename Cache::iterator right
	) {
		if(left == right) return nullptr;
		return rc::gen::map(rc::gen::inRange(0, std::distance(left, right)), [&](int index) {
			auto middle = left + index;
			return Node<Key, Value>::balance((left + index)->first, (left + index)->second,
				arbitrary_node(left, middle), arbitrary_node(middle + 1, right));
		});
	}
	static rc::Gen<SortedMap<Key, Value>> arbitrary() {
		return rc::gen::map(rc::gen::arbitrary<Cache>(), [](Cache& cache) {
			std::sort(cache.begin(), cache.end());
			for(int i = 0; i < cache.length; ++i) cache[i].first += i;
			return rc::gen::map(arbitrary_node(cache.begin(), cache.end()),
				[](const NodePtr<Key, Value>& node) { return SortedMap<Key, Value>(node); });
		});
	}
};

template<class... Ts>
struct overloaded : Ts... { using Ts::operator()...; };
template<class... Ts>
overloaded(Ts...) -> overloaded<Ts...>;

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
		{ node.pretty(out, 0); }
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
	if(Assert) {
		float ratio = lsize > rsize ? float(lsize) / rsize : float(rsize) / lsize,
			gamma = float(SortedMap<Key, Value>::gamma),
			delta = float(SortedMap<Key, Value>::delta);
		RC_ASSERT(gamma <= ratio);
		RC_ASSERT(ratio <= delta);
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

// RC_GTEST_PROP(SortedMap, insert, (SortedMap<int, int> smap, int k, int v)) {
	// auto elems = tomap(smap);
	// elems.insert(elems.begin(), std::make_pair(k, v));
	// RC_ASSERT(check(smap.insert(k)) == elems);
// }

