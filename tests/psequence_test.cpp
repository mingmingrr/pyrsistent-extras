#include <rapidcheck.h>
#include <gtest/gtest.h>
#include <rapidcheck/gtest.h>

#include <vector>
#include <algorithm>

#include "_psequence.hpp"

namespace pyr = pyrsistent;

template<typename Value>
using Sequence = pyr::Sequence<Value>;
template<typename Value>
using Tree = typename Sequence<Value>::Tree;
template<typename Value>
using Empty = typename Sequence<Value>::Empty;
template<typename Value>
using Deep = typename Sequence<Value>::Deep;
template<typename Value>
using DeepPtr = typename Sequence<Value>::DeepPtr;
template<typename Value>
using Digit = typename Sequence<Value>::Digit;
template<typename Value>
using DigitPtr = typename Sequence<Value>::DigitPtr;
template<typename Value>
using Node = typename Sequence<Value>::Node;
template<typename Value>
using NodePtr = typename Sequence<Value>::NodePtr;
template<typename Value>
using Branch = typename Sequence<Value>::Branch;

template struct pyr::Sequence<int>;

template<typename Value>
struct rc::Arbitrary<pyr::Sequence<Value>> {
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

	static rc::Gen<DigitPtr<Value>> arbitrary_digit(int depth) {
		return rc::gen::oneOf(
			rc::gen::lazy([=]() { return rc::gen::apply(
				Digit<Value>::template make<NodePtr<Value>>,
				arbitrary_node(depth)); }),
			rc::gen::lazy([=]() { return rc::gen::apply(
				Digit<Value>::template make<NodePtr<Value>, NodePtr<Value>>,
				arbitrary_node(depth), arbitrary_node(depth)); }),
			rc::gen::lazy([=]() { return rc::gen::apply(
				Digit<Value>::template make<NodePtr<Value>, NodePtr<Value>, NodePtr<Value>>,
				arbitrary_node(depth), arbitrary_node(depth), arbitrary_node(depth)); }),
			rc::gen::lazy([=]() { return rc::gen::apply(
				Digit<Value>::template make<
					NodePtr<Value>, NodePtr<Value>, NodePtr<Value>, NodePtr<Value>>,
				arbitrary_node(depth), arbitrary_node(depth),
				arbitrary_node(depth), arbitrary_node(depth)); })
		);
	}

	static rc::Gen<Tree<Value>> arbitrary_tree(int size, int depth) {
		if(size == 0) return rc::gen::just(Tree<Value>(Empty<Value>()));
		if(size == 1) return rc::gen::map(arbitrary_node(depth),
			[](const NodePtr<Value>& node) { return Tree<Value>(node); });
		return rc::gen::mapcat(
			rc::gen::pair(arbitrary_digit(depth), arbitrary_digit(depth)),
				[=](std::pair<DigitPtr<Value>,DigitPtr<Value>> xs) -> rc::Gen<Tree<Value>> {
				int lower = std::max(size / 7,
					(size - xs.first->order - xs.second->order) / 3);
				return rc::gen::map(arbitrary_tree(lower, depth + 1), [=](const Tree<Value>& middle)
					{ return Tree<Value>(Deep<Value>::make(xs.first, middle, xs.second)); });
			}
		);
	}

	static rc::Gen<Sequence<Value>> arbitrary() {
		return rc::gen::withSize([](int size) -> rc::Gen<Sequence<Value>> {
			return rc::gen::mapcat(rc::gen::inRange<int>(0, size + 1),
				[](int size) { return rc::gen::map(arbitrary_tree(size, 0),
					[](Tree<Value>&& tree) { return Sequence<Value>(std::move(tree)); }); }
			);
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
	template<typename Value>
	void showValue(const Sequence<Value>& seq, std::ostream& out)
		{ seq.pretty(out); }
	template<typename Value>
	void showValue(const Tree<Value>& tree, std::ostream& out)
		{ tree.pretty(out, 0); }
	template<typename Value>
	void showValue(const Deep<Value>& deep, std::ostream& out)
		{ deep.pretty(out, 0); }
	template<typename Value>
	void showValue(const Digit<Value>& digit, std::ostream& out)
		{ digit.pretty(out, 0); }
	template<typename Value>
	void showValue(const Node<Value>& node, std::ostream& out)
		{ node.pretty(out, 0); }
}
// LCOV_EXCL_STOP

template<typename Value, bool Assert=true>
size_t check(const NodePtr<Value>& node, int depth, std::vector<Value>& elems) {
	if(Assert) RC_ASSERT(node);
	return std::visit(overloaded {
		[&](const Value& value) {
			if(Assert) RC_ASSERT(depth == 0);
			elems.push_back(value);
			return (size_t)1;
		},
		[&](const Branch<Value>& branch) {
			if(Assert) RC_ASSERT(depth > 0);
			size_t size = check(branch.items[0], depth - 1, elems);
			size += check(branch.items[1], depth - 1, elems);
			if(branch.items[2]) size += check(branch.items[2], depth - 1, elems);
			if(Assert) RC_ASSERT(branch.size == size);
			return size;
		}
	}, *node);
}

template<typename Value, bool Assert=true>
size_t check(const DigitPtr<Value>& digit, int depth, std::vector<Value>& elems) {
	if(Assert) RC_ASSERT(digit);
	if(Assert) RC_ASSERT(0 < digit->order && digit->order <= 4);
	if(Assert) RC_ASSERT(digit->items[0]);
	size_t size = check<Value, Assert>(digit->items[0], depth, elems);
	if(digit->order >= 2) {
		if(Assert) RC_ASSERT(digit->items[1]);
		size += check<Value, Assert>(digit->items[1], depth, elems);
	} else if(Assert) RC_ASSERT(digit->items[1] == nullptr);
	if(digit->order >= 3) {
		if(Assert) RC_ASSERT(digit->items[2]);
		size += check<Value, Assert>(digit->items[2], depth, elems);
	} else if(Assert) RC_ASSERT(digit->items[2] == nullptr);
	if(digit->order >= 4) {
		if(Assert) RC_ASSERT(digit->items[3]);
		size += check<Value, Assert>(digit->items[3], depth, elems);
	} else if(Assert) RC_ASSERT(digit->items[3] == nullptr);
	return size;
}

template<typename Value, bool Assert=true>
size_t check(const Tree<Value>& tree, int depth, std::vector<Value>& elems) {
	return std::visit(overloaded {
		[&](const Empty<Value>& _) { return (size_t)0; },
		[&](const NodePtr<Value>& node)
			{ return check<Value, Assert>(node, depth, elems); },
		[&](const DeepPtr<Value>& deep) {
			size_t size = check<Value, Assert>(deep->left, depth, elems);
			size += check<Value, Assert>(deep->middle, depth + 1, elems);
			size += check<Value, Assert>(deep->right, depth, elems);
			if(Assert) RC_ASSERT(deep->size == size);
			return size;
		},
	}, tree);
}

template<typename Value, bool Assert=true>
std::vector<Value> check(const Sequence<Value>& seq) {
	std::vector<Value> elems;
	size_t size = check<Value, Assert>(seq.tree, 0, elems);
	if(Assert) RC_ASSERT(size == elems.size());
	return elems;
} // LCOV_EXCL_LINE

template<typename Value>
std::vector<Value> tolist(const Sequence<Value>& seq)
	{ return check<Value, false>(seq); }

std::vector<int> slice(std::vector<int> xs, ssize_t left, ssize_t right) {
	auto a = left >= 0 ? std::min((ssize_t)xs.size(), left)
		: std::max<ssize_t>(0, xs.size() + left + 1);
	auto b = right >= 0 ? std::min((ssize_t)xs.size(), right)
		: std::max<ssize_t>(0, xs.size() + right + 1);
	if(a >= b) return std::vector<int>();
	return std::vector<int>(xs.begin() + a, xs.begin() + b);
}

std::vector<int> erase(std::vector<int> xs, ssize_t left, ssize_t right) {
	ssize_t a = left >= 0 ? std::min((ssize_t)xs.size(), left)
		: std::max<ssize_t>(0, xs.size() + left + 1);
	ssize_t b = right >= 0 ? std::min((ssize_t)xs.size(), right)
		: std::max<ssize_t>(0, xs.size() + right + 1);
	if(a >= b) return xs;
	auto ys = xs;
	ys.erase(ys.begin() + a, ys.begin() + b);
	return ys;
}

RC_GTEST_PROP(Sequence, check, (Sequence<int> seq)) {
	RC_ASSERT(check(seq) == tolist(seq));
}

RC_GTEST_PROP(Sequence, empty, (Sequence<int> seq)) {
	auto elems = tolist(seq);
	RC_ASSERT((bool)seq == (bool)elems.size());
	RC_ASSERT(seq.empty() == elems.empty());
}

RC_GTEST_PROP(Sequence, size, (Sequence<int> seq)) {
	RC_ASSERT(seq.size() == tolist(seq).size());
}

RC_GTEST_PROP(Sequence, push_front, (Sequence<int> seq, int x)) {
	auto elems = tolist(seq);
	elems.insert(elems.begin(), x);
	RC_ASSERT(check(seq.push_front(x)) == elems);
}

RC_GTEST_PROP(Sequence, push_back, (Sequence<int> seq, int x)) {
	auto elems = tolist(seq);
	elems.push_back(x);
	RC_ASSERT(check(seq.push_back(x)) == elems);
}

RC_GTEST_PROP(Sequence, front, (Sequence<int> seq)) {
	auto elems = tolist(seq);
	if(!elems.empty())
		RC_ASSERT(seq.front() == elems.front());
	else RC_ASSERT_THROWS(seq.front());
}

RC_GTEST_PROP(Sequence, back, (Sequence<int> seq)) {
	auto elems = tolist(seq);
	if(!elems.empty())
		RC_ASSERT(seq.back() == elems.back());
	else RC_ASSERT_THROWS(seq.back());
}

RC_GTEST_PROP(Sequence, view_front, (Sequence<int> seq)) {
	auto elems = tolist(seq);
	if(!elems.empty()) {
		auto [head, tail] = seq.view_front();
		RC_ASSERT(head == elems.front());
		elems.erase(elems.begin());
		RC_ASSERT(check(tail) == elems);
	} else RC_ASSERT_THROWS(seq.view_front());
}

RC_GTEST_PROP(Sequence, view_back, (Sequence<int> seq)) {
	auto elems = tolist(seq);
	if(!elems.empty()) {
		auto [init, last] = seq.view_back();
		RC_ASSERT(last == elems.back());
		elems.pop_back();
		RC_ASSERT(check(init) == elems);
	} else RC_ASSERT_THROWS(seq.view_back());
}

RC_GTEST_PROP(Sequence, from_list, (std::vector<int> elems)) {
	RC_ASSERT(check(Sequence<int>(elems.begin(), elems.end())) == elems);
}

RC_GTEST_PROP(Sequence, at, (Sequence<int> seq, size_t index)) {
	auto elems = tolist(seq);
	if(!elems.empty()) {
		index %= elems.size();
		RC_ASSERT(seq[index] == elems[index]);
		RC_ASSERT(seq.at(index) == elems.at(index));
	}
	RC_ASSERT_THROWS(seq.at(index + elems.size()));
}

RC_GTEST_PROP(Sequence, at_slice, (Sequence<int> seq, size_t left, size_t right)) {
	auto elems = tolist(seq);
	left %= std::max<size_t>(1, elems.size() * 5/4);
	right %= std::max<size_t>(1, elems.size() * 5/4);
	elems = left >= right ? decltype(elems)() : decltype(elems)(
		elems.begin() + std::min(left, elems.size()),
		elems.begin() + std::min(right, elems.size()));
	RC_ASSERT(check(seq.at(left, right)) == elems);
}

RC_GTEST_PROP(Sequence, at_step, (Sequence<int> seq, size_t left, size_t right, size_t step)) {
	auto elems = tolist(seq);
	left %= std::max<size_t>(1, elems.size() * 5/4);
	right %= std::max<size_t>(1, elems.size() * 5/4);
	step = step % std::max<size_t>(1, elems.size() * 5/4) + 1;
	std::tie(left, right) = std::make_pair(
		std::min(left, right), std::max(left, right));
	RC_ASSERT(check(seq.at(right, left, step)).empty());
	std::vector<int> ns;
	for(auto i = left; i < std::min(right, elems.size()); i += step)
		ns.push_back(elems[i]);
	RC_ASSERT(check(seq.at(left, right, step)) == ns);
	RC_ASSERT_THROWS(seq.erase(left, right, 0));
}

RC_GTEST_PROP(Sequence, append, (Sequence<int> seq1, Sequence<int> seq2)) {
	auto elems = tolist(seq1), ys = tolist(seq2);
	elems.insert(elems.end(), ys.begin(), ys.end());
	RC_ASSERT(check(seq1.append(seq2)) == elems);
}

RC_GTEST_PROP(Sequence, repeat, (Sequence<int> seq, size_t times)) {
	times %= 40;
	auto elems = tolist(seq);
	decltype(elems) ys;
	for(auto n = 0; n < times; ++n)
		ys.insert(ys.end(), elems.begin(), elems.end());
	RC_ASSERT(check(seq.repeat(times)) == ys);
}

RC_GTEST_PROP(Sequence, transform, (Sequence<int> seq, int value)) {
	auto elems = tolist(seq);
	for(auto& n: elems) n += value;
	RC_ASSERT(check(seq.transform([&](auto x) { return x + value; })) == elems);
}

RC_GTEST_PROP(Sequence, set, (Sequence<int> seq, size_t index, int value)) {
	auto elems = tolist(seq);
	auto size = elems.size();
	if(!elems.empty()) {
		index %= elems.size();
		elems[index] = value;
		RC_ASSERT(check(seq.set(index, value)) == elems);
	}
	RC_ASSERT_THROWS(seq.set(index + size, value));
}

RC_GTEST_PROP(Sequence, set_slice, (
	Sequence<int> seq,
	size_t left,
	size_t right,
	Sequence<int> values
)) {
	auto elems = tolist(seq);
	elems.erase(elems.begin() + std::min(elems.size(), left),
		elems.begin() + std::min(elems.size(), std::max(left, right)));
	elems.insert(elems.begin() + std::min(elems.size(), left),
		values.begin(), values.end());
	RC_ASSERT(check(seq.set(left, right, values)) == elems);
}

RC_GTEST_PROP(Sequence, set_step, (
	Sequence<int> seq,
	size_t left,
	size_t right,
	size_t step,
	Sequence<int> values
)) {
	auto elems = tolist(seq);
	left %= std::max<size_t>(1, elems.size() * 5/4);
	right %= std::max<size_t>(1, elems.size() * 5/4);
	step = step % std::max<size_t>(1, elems.size() * 5/4) + 2;
	std::tie(left, right) = std::make_pair(
		std::min(left, right), std::max(left, right));
	std::vector<size_t> ns;
	for(size_t i = left, j = 0; i < std::min(right, elems.size()); i += step, ++j) {
		ns.push_back(i);
		if(j < values.size()) elems[i] = values[j];
	}
	if(ns.empty() || ns.size() == values.size())
		RC_ASSERT(check(seq.set(left, right, step, values.begin(), values.end())) == elems);
	else
		RC_ASSERT_THROWS(seq.set(left, right, step, values.begin(), values.end()));
	RC_ASSERT(check(seq.set(left, right, 1, values.begin(), values.end()))
		== check(seq.set(left, right, values)));
}

RC_GTEST_PROP(Sequence, insert, (Sequence<int> seq, size_t index, int value)) {
	auto elems = tolist(seq);
	auto size = elems.size();
	if(!elems.empty()) {
		index %= elems.size();
		elems.insert(elems.begin() + index, value);
		RC_ASSERT(check(seq.insert(index, value)) == elems);
	}
	RC_ASSERT_THROWS(seq.insert(index + size, value));
}

RC_GTEST_PROP(Sequence, erase, (Sequence<int> seq, size_t index)) {
	auto elems = tolist(seq);
	auto size = elems.size();
	if(!elems.empty()) {
		index %= elems.size();
		elems.erase(elems.begin() + index);
		RC_ASSERT(check(seq.erase(index)) == elems);
	}
	RC_ASSERT_THROWS(seq.erase(index + size));
}

RC_GTEST_PROP(Sequence, erase_slice, (Sequence<int> seq, size_t left, size_t right)) {
	auto elems = tolist(seq);
	left %= std::max<size_t>(1, elems.size() * 5/4);
	right %= std::max<size_t>(1, elems.size() * 5/4);
	std::tie(left, right) = std::make_pair(
		std::min(left, right), std::max(left, right));
	RC_ASSERT(check(seq.erase(right, left)) == elems);
	RC_ASSERT(check(seq.erase(left, right)) == erase(elems, left, right));
}

RC_GTEST_PROP(Sequence, erase_step, (Sequence<int> seq, size_t left, size_t right, size_t step)) {
	auto elems = tolist(seq);
	left %= std::max<size_t>(1, elems.size() * 5/4);
	right %= std::max<size_t>(1, elems.size() * 5/4);
	step = step % std::max<size_t>(1, elems.size() * 5/4) + 1;
	std::tie(left, right) = std::make_pair(
		std::min(left, right), std::max(left, right));
	RC_ASSERT(check(seq.erase(right, left, step)) == elems);
	std::vector<size_t> ns;
	for(auto i = left; i < std::min(right, elems.size()); i += step)
		ns.push_back(i);
	for(auto i = ns.rbegin(); i != ns.rend(); ++i)
		elems.erase(elems.begin() + *i);
	RC_ASSERT(check(seq.erase(left, right, step)) == elems);
	RC_ASSERT_THROWS(seq.erase(left, right, 0));
}

RC_GTEST_PROP(Sequence, split, (Sequence<int> seq, size_t index)) {
	auto elems = tolist(seq);
	auto size = elems.size();
	if(!elems.empty()) {
		index %= elems.size();
		auto [left, value, right] = seq.split(index);
		RC_ASSERT(value == elems[index]);
		RC_ASSERT(check(left) == slice(elems, 0, index));
		RC_ASSERT(check(right) == slice(elems, index + 1, elems.size()));
	}
	RC_ASSERT_THROWS(seq.split(index + size));
}

RC_GTEST_PROP(Sequence, split_append, (Sequence<int> seq, size_t index)) {
	auto elems = tolist(seq);
	if(!elems.empty()) {
		index %= elems.size();
		auto [left, value, right] = seq.split(index);
		RC_ASSERT(check(left.push_back(value).append(right)) == elems);
		RC_ASSERT(check(left.append(right.push_front(value))) == elems);
	}
}

RC_GTEST_PROP(Sequence, splitat, (Sequence<int> seq, size_t index)) {
	auto [left, right] = seq.splitat(index);
	RC_ASSERT(check(left) == check(seq.take_front(index)));
	RC_ASSERT(check(right) == check(seq.drop_front(index)));
}

RC_GTEST_PROP(Sequence, take_front, (Sequence<int> seq, size_t index)) {
	auto elems = tolist(seq);
	index %= std::max<size_t>(1, elems.size() * 5/4);
	elems = slice(elems, 0, std::min(index, elems.size()));
	RC_ASSERT(check(seq.take_front(index)) == elems);
}

RC_GTEST_PROP(Sequence, drop_back, (Sequence<int> seq, size_t index)) {
	auto elems = tolist(seq);
	index %= std::max<size_t>(1, elems.size() * 5/4);
	if(index) elems = erase(elems, -(ssize_t)index-1, elems.size());
	RC_ASSERT(check(seq.drop_back(index)) == elems);
}

RC_GTEST_PROP(Sequence, take_back, (Sequence<int> seq, size_t index)) {
	auto elems = tolist(seq);
	index %= std::max<size_t>(1, elems.size() * 5/4);
	elems = slice(elems, -(ssize_t)index-1, elems.size());
	RC_ASSERT(check(seq.take_back(index)) == elems);
}

RC_GTEST_PROP(Sequence, drop_front, (Sequence<int> seq, size_t index)) {
	auto elems = tolist(seq);
	index %= std::max<size_t>(1, elems.size() * 5/4);
	elems = erase(elems, 0, index);
	RC_ASSERT(check(seq.drop_front(index)) == elems);
}

RC_GTEST_PROP(Sequence, reverse, (Sequence<int> seq)) {
	auto elems = tolist(seq);
	std::reverse(elems.begin(), elems.end());
	RC_ASSERT(check(seq.reverse()) == elems);
	RC_ASSERT(check(seq.reverse().reverse()) == check(seq));
}

RC_GTEST_PROP(Sequence_Iterator, tolist, (Sequence<int> seq)) {
	RC_ASSERT(std::vector<int>(seq.begin(), seq.end()) == tolist(seq));
}

RC_GTEST_PROP(Sequence_Iterator, add, (Sequence<int> seq, size_t index)) {
	auto elems = tolist(seq);
	if(!elems.empty()) {
		index %= elems.size();
		RC_ASSERT(*(seq.begin() + index) == elems[index]);
		RC_ASSERT(*(seq.begin() + index / 2 + index / 2 + index % 2) == elems[index]);
	}
}

RC_GTEST_PROP(Sequence_RIterator, tolist, (Sequence<int> seq)) {
	auto ref = tolist(seq); std::reverse(ref.begin(), ref.end());
	RC_ASSERT(std::vector<int>(seq.rbegin(), seq.rend()) == ref);
}

RC_GTEST_PROP(Sequence, reverse_tolist, (Sequence<int> seq)) {
	RC_ASSERT(check(seq.reverse()) == std::vector<int>(seq.rbegin(), seq.rend()));
}

RC_GTEST_PROP(Sequence, compare_eq, (Sequence<int> xs, Sequence<int> ys)) {
	auto as = tolist(xs), bs = tolist(ys);
	RC_ASSERT((xs == ys) == (as == bs));
	RC_ASSERT((xs == bs) == (as == bs));
	RC_ASSERT((xs != ys) == (as != bs));
	RC_ASSERT((xs != bs) == (as != bs));
}

RC_GTEST_PROP(Sequence, compare_ord, (Sequence<int> xs, Sequence<int> ys)) {
	auto as = tolist(xs), bs = tolist(ys);
	RC_ASSERT((xs < ys) == (as < bs));
	RC_ASSERT((xs < bs) == (as < bs));
	RC_ASSERT((xs > ys) == (as > bs));
	RC_ASSERT((xs > bs) == (as > bs));
	RC_ASSERT((xs <= ys) == (as <= bs));
	RC_ASSERT((xs <= bs) == (as <= bs));
	RC_ASSERT((xs >= ys) == (as >= bs));
	RC_ASSERT((xs >= bs) == (as >= bs));
}

RC_GTEST_PROP(Sequence, hash, (Sequence<int> xs, Sequence<int> ys)) {
	static size_t okay = 0, fail = 0;
	std::hash<decltype(xs)> HashSeq;
	auto eq1 = HashSeq(xs) == HashSeq(ys);
	auto eq2 = tolist(xs) == tolist(ys);
	RC_ASSERT(!eq1 || eq2);
	if(eq1 == eq2) ++okay; else ++fail;
	if((okay + fail) > 50)
		RC_ASSERT(fail * 10 < okay);
}

