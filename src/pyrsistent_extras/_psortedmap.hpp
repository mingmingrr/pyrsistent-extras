#pragma once

#include <cstdint>
#include <iterator>
#include <memory>
#include <algorithm>
#include <variant>
#include <optional>
#include <sstream>
#include <tuple>
#include <cassert>
#include <stdexcept>

#include "_plist.hpp"
#include "_utility.hpp"

namespace pyrsistent {

template<
	typename Key,
	typename Value,
	typename Compare=std::less<Key>,
	typename Allocator=std::allocator<std::pair<Key,Value>>
>
struct SortedMap {
	struct Node;

	static constexpr uint_least8_t delta = 3;
	static constexpr uint_least8_t gamma = 2;

	using NodePtr = std::shared_ptr<Node>;

	struct Node {
		const Key key;
		const Value value;
		size_t size;
		NodePtr left;
		NodePtr right;

		template<typename ...Args>
		static inline NodePtr make(Args&&... args) {
			return std::allocate_shared<Node, Allocator, Args...>
				(Allocator{}, std::forward<Args>(args)...);
		}

		explicit Node(const Key& key, const Value& value)
			: Node(key, value, 1, nullptr, nullptr) { }
		Node(const Key& key, const Value& value,
			const NodePtr& left, const NodePtr& right)
			: Node(key, value, Node::sizes(left) + Node::sizes(right) + 1, left, right) { }
		Node(const Key& key, const Value& value, ssize_t size,
			const NodePtr& left, const NodePtr& right)
			: key(key), value(value), size(size), left(left), right(right)
			{ assert(size == Node::sizes(left) + Node::sizes(right) + 1); }

		// LCOV_EXCL_START
		static constexpr void pretty(const NodePtr& node, std::ostream& out, size_t depth) {
			if(!node) return;
			Node::pretty(node->left, out, depth + 1);
			for(auto i = depth; i--;) out << "  ";
			out << "Node[" << node->size << "] "
				<< node->key << ": " << node->value << std::endl;
			Node::pretty(node->right, out, depth + 1);
		}
		// LCOV_EXCL_STOP

		static constexpr size_t sizes(const NodePtr& node)
			{ return node ? node->size : 0; }

		static constexpr NodePtr balance(
			const Key& key,
			const Value& value,
			const NodePtr& left,
			const NodePtr& right
		) {
			auto sl = Node::sizes(left), sr = Node::sizes(right), sx = sl + sr + 1;
			if(sx <= 2) return Node::make(key, value, sx, left, right);
			if(sr >= delta * sl) {
				assert(right);
				if(Node::sizes(right->left) < gamma * Node::sizes(right->right))
					return Node::make(right->key, right->value, sx,
						Node::make(key, value, left, right->left), right->right);
				assert(right->left);
				return Node::make(right->left->key, right->left->value, sx,
					Node::make(key, value, left, right->left->left),
					Node::make(right->key, right->value, right->left->right, right->right));
			}
			if(sl >= delta * sr) {
				assert(left);
				if(Node::sizes(left->right) < gamma * Node::sizes(left->left))
					return Node::make(left->key, left->value, sx,
						left->left, Node::make(key, value, left->right, right));
				assert(left->right);
				return Node::make(left->right->key, left->right->value, sx,
					Node::make(left->key, left->value, left->left, left->right->left),
					Node::make(key, value, left->right->right, right));
			}
			return Node::make(key, value, left, right);
		}

		static constexpr NodePtr insert(const NodePtr& node, const Key& key, const Value& value) {
			if(!node) return Node::make(key, value);
			if(key < node->key)
				return Node::balance(node->key, node->value,
					Node::insert(node->left, key, value), node->right);
			if(node->key < key)
				return Node::balance(node->key, node->value,
					node->left, Node::insert(node->right, key, value));
			return Node::make(key, value, node->size, node->left, node->right);
		}

		template<typename Func>
		static constexpr NodePtr alter(
			const NodePtr& node,
			const Key& key,
			const Func& func
		) {
			if(!node) {
				auto value = func(key, std::nullopt);
				return value ? Node::make(key, *value) : node;
			}
			if(key < node->key)
				return Node::balance(node->key, node->value,
					Node::alter(node->left, key, func), node->right);
			if(node->key < key)
				return Node::balance(node->key, node->value,
					node->left, Node::alter(node->right, key, func));
			auto value = func(key, node->value);
			return value ? Node::make(key, *value, node->size, node->left, node->right)
				: Node::glue(node->left, node->right);
		}

		static constexpr std::optional<Value> at(const NodePtr& node, const Key& key) {
			if(!node) return std::nullopt;
			if(key < node->key) return at(node->left, key);
			if(node->key < key) return at(node->right, key);
			return node->value;
		}

		constexpr std::tuple<Key, Value, NodePtr> viewmin() const {
			if(!this->left) return std::make_tuple(this->key, this->value, this->right);
			auto [key, value, rec] = this->left->viewmin();
			return std::make_tuple(key, value, Node::make(this->key, this->value,
				this->size - 1, rec, this->right));
		}

		constexpr std::tuple<Key, Value, NodePtr> viewmax() const {
			if(!this->right) return std::make_tuple(this->key, this->value, this->left);
			auto [key, value, rec] = this->right->viewmax();
			return std::make_tuple(key, value, Node::make(this->key, this->value,
				this->size - 1, this->left, rec));
		}

		static constexpr NodePtr glue(const NodePtr& left, const NodePtr& right) {
			if(!left) return right;
			if(!right) return left;
			if(left->size > right->size) {
				auto [key, value, tree] = left->viewmax();
				return Node::balance(key, value, tree, right);
			}
			auto [key, value, tree] = right->viewmin();
			return Node::balance(key, value, left, tree);
		}

		static constexpr std::pair<std::optional<Value>, NodePtr> pop(
			const NodePtr& node, const Key& key
		) {
			if(!node) return std::make_pair(std::nullopt, node);
			if(key < node->key) {
				auto [value, rec] = Node::pop(node->left, key);
				return std::make_pair(value, Node::balance(
					node->key, node->value, rec, node->right));
			}
			if(node->key < key) {
				auto [value, rec] = Node::pop(node->right, key);
				return std::make_pair(value, Node::balance(
					node->key, node->value, node->left, rec));
			}
			return std::make_pair(node->value, Node::glue(node->left, node->right));
		}

		static constexpr NodePtr merge(const NodePtr& left, const NodePtr& right) {
			if(!left) return right;
			if(!right) return left;
			if(delta * left->size <= right->size)
				return Node::balance(right->key, right->value,
					Node::merge(left, right->left), right->right);
			if(delta * right->size <= left->size)
				return Node::balance(left->key, left->value,
					left->left, Node::merge(left->right, right));
			return Node::glue(left, right);
		}

		static constexpr NodePtr join(
			const Key& key,
			const Value& value,
			const NodePtr& left,
			const NodePtr& right
		) {
			if(!left) return Node::insert(right, key, value);
			if(!right) return Node::insert(left, key, value);
			if(delta * left->size < right->size)
				return Node::balance(right->key, right->value,
					Node::join(key, value, left, right->left), right->right);
			if(delta * right->size < left->size)
				return Node::balance(left->key, left->value,
					left->left, Node::join(key, value, left->right, right));
			return Node::balance(key, value, left, right);
		}

		static constexpr std::tuple<NodePtr, std::optional<Value>, NodePtr> split(
			const NodePtr& node, const Key& key
		) {
			if(!node) return std::make_tuple(node, std::nullopt, node);
			if(key < node->key) {
				auto [left, value, right] = Node::split(node->left, key);
				return std::make_tuple(left, value, Node::join(
					node->key, node->value, right, node->right));
			}
			if(node->key < key) {
				auto [left, value, right] = Node::split(node->right, key);
				return std::make_tuple(Node::join(
					node->key, node->value, node->left, left), value, right);
			}
			return std::make_tuple(node->left, node->value, node->right);
		}

		static constexpr std::pair<std::optional<Value>, NodePtr> trim(
			const NodePtr& node,
			const std::optional<Key>& low,
			const std::optional<Key>& high
		) {
			if(!node) return std::make_pair(std::nullopt, node);
			if(!low || *low < node->key) {
				if(!high || node->key < high) {
					if(!low) return std::make_pair(std::nullopt, node);
					return std::make_pair(Node::at(node, *low), node);
				} else return Node::trim(node->left, low, high);
			} else if(node->key < low) return Node::trim(node->right, low, high);
			else return std::make_pair(node->value, Node::trim(node->right, low, high).second);
		}

		template<typename Func>
		static constexpr NodePtr unionwith(
			const NodePtr& left,
			const NodePtr& right,
			const Func& func,
			const std::optional<Key>& low,
			const std::optional<Key>& high
		) {
			if(!right) return left;
			if(!left) return Node::join(right->key, right->value,
				low ? std::get<2>(Node::split(right->left, *low)) : right->left,
				high ? std::get<0>(Node::split(right->right, *high)) : right->right);
			auto lesser = Node::trim(right, low, left->key).second;
			auto [value, greater] = Node::trim(right, left->key, high);
			return Node::join(left->key,
				value ? func(left->key, left->value, *value) : left->value,
				Node::unionwith(left->left, lesser, func, low, left->key),
				Node::unionwith(left->right, greater, func, left->key, high));
		}

		template<typename Func>
		static constexpr NodePtr intersectwith(
			const NodePtr& left,
			const NodePtr& right,
			const Func& func
		) {
			if(!left || !right) return nullptr;
			auto [lesser, value, greater] = Node::split(left, right->key);
			auto left1 = Node::intersectwith(lesser, right->left, func);
			auto right1 = Node::intersectwith(greater, right->right, func);
			if(!value) return Node::merge(left1, right1);
			return Node::join(Node(right->key, func(
				right->key, value, right->value), left1, right1));
		}

		template<typename Func>
		static constexpr NodePtr differencewith(
			const NodePtr& left,
			const NodePtr& right,
			const Func& func,
			const std::optional<Key>& low,
			const std::optional<Key>& high
		) {
			if(!left) return left;
			if(!right) return Node::join(left.key, left.value,
				low ? std::get<2>(Node::split(left->left, low)) : left->left,
				high ? std::get<0>(Node::split(left->right, high)) : left->right);
			auto lesser = Node::trim(left, low, right->key).second;
			auto [value, greater] = Node::trim(left, right->key, high);
			auto left1 = Node::differencewith(lesser, right->left, func, low, right->key);
			auto right1 = Node::differencewith(greater, right->right, func, right->key, high);
			if(!value) return Node::merge(left1, right1);
			auto value1 = func(right->key, *value, right->value);
			if(!value1) return Node::merge(left1, right1);
			return Node::join(right->key, *value1, left1, right1);
		}
	};

	using value_type = const Value;
	using size_type = size_t;
	using diference_type = std::ptrdiff_t;
	using const_reference = const Value&;
	using reference = const_reference;

	NodePtr node;

	SortedMap() : node() { }
	SortedMap(const SortedMap&) = default;
	SortedMap(NodePtr&& node) : node(std::move(node)) { }
	SortedMap(std::initializer_list<std::pair<Key, Value>> xs)
		: SortedMap(xs.begin(), xs.end()) { }

	template<typename Iterator>
	SortedMap(Iterator left, const Iterator& right) : node() {
		while(left != right) {
			auto [key, value] = *left;
			this->node = Node::insert(this->node, key, value);
			++left;
		}
	}

	// LCOV_EXCL_START
	void pretty(std::ostream& out) const
		{ Node::pretty(this->node, out, 0); }
	std::string pretty() const {
		std::ostringstream out;
		this->pretty(out);
		return out.str();
	}
	// LCOV_EXCL_STOP

	constexpr size_t size() const
		{ return Node::sizes(this->node); }

	constexpr operator bool() const
		{ return bool(this->node); }
	constexpr bool empty() const
		{ return !this->node; }

	constexpr std::optional<Value> at(const Key& key) {
		return Node::at(this->node, key);
	}

	constexpr SortedMap insert(const Key& key, const Value& value) {
		return SortedMap(Node::insert(this->node, key, value));
	}

	constexpr std::pair<std::optional<Value>, SortedMap> pop(const Key& key) {
		auto [value, node] = Node::pop(this->node, key);
		return std::make_pair(value, SortedMap(std::move(node)));
	}

	template<bool Reverse=false>
	struct Iterator {
		using value_type = const Value;
		using difference_type = std::ptrdiff_t;
		using reference = const Value&;
		using pointer = const Value*;
		using iterator_category = std::forward_iterator_tag;

		using Stack = List<std::pair<bool, NodePtr>>;
		Stack stack;

		Iterator() : stack() { }
		Iterator(const Iterator&) = default;
		Iterator(Iterator&&) = default;
		explicit Iterator(const SortedMap& xs)
			: stack(std::make_pair(false, xs.node), Stack())
			{ this->advance(); }

		constexpr void advance() {
			if(this->stack.empty()) return;
			auto& [seen, node] = this->stack.head();
			if(!node) {
				this->stack = this->stack.tail();
				return this->advance();
			}
			if(seen) {
				auto target = Reverse ? node->left : node->right;
				this->stack = Stack(std::make_pair(false, target), this->stack.tail());
				return;
			}
			auto target = Reverse ? node->right : node->left;
			this->stack = Stack(std::make_pair(false, target),
				Stack(std::make_pair(true, node), this->stack.tail()));
			return this->advance();
		}

		constexpr Iterator& operator ++() {
			if(this->stack.size()) {
				this->stack = this->stack.tail();
				this->advance();
			}
			return *this;
		}

		constexpr Iterator operator ++(int)
			{ Iterator copy(*this); ++*this; return copy; }

		constexpr const Value& operator *() const
			{ return std::get<Value>(*std::get<NodePtr>(this->stack.head())); }

		constexpr bool operator ==(const Iterator& that) const
			{ return this->stack == that.stack; }
		constexpr bool operator !=(const Iterator& that) const
			{ return !(*this == that); }

		constexpr bool empty() const
			{ return this->stack.empty(); }
	};

	using iterator = Iterator<false>;

	constexpr iterator begin() const
		{ return iterator(*this); }
	constexpr iterator end() const
		{ return iterator(); }

	using reverse_iterator = Iterator<true>;

	constexpr reverse_iterator rbegin() const
		{ return reverse_iterator(*this); }
	constexpr reverse_iterator rend() const
		{ return reverse_iterator(); }

};

template struct SortedMap<int, bool>;

}

// template<typename Value, typename Allocator>
// struct std::hash<pyrsistent::SortedMap<Value, Allocator>>
	// : public pyrsistent::HashIterable<pyrsistent::SortedMap<Value, Allocator>> { };

template struct pyrsistent::SortedMap<int, int>;

