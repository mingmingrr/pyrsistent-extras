#pragma once

#include <iterator>
#include <memory>
#include <algorithm>
#include <variant>
#include <optional>
#include <sstream>
#include <tuple>
#include <cassert>
#include <cstdint>
#include <stdexcept>

#include "_plist.hpp"
#include "_utility.hpp"

namespace pyrsistent {

template<typename Value, typename Allocator=std::allocator<Value>>
struct Sequence {
	struct Branch;
	struct Node;
	struct Digit;
	struct Deep;
	struct Tree;

	using NodePtr = std::shared_ptr<Node>;
	using DigitPtr = std::shared_ptr<Digit>;
	using DeepPtr = std::shared_ptr<Deep>;

	// LCOV_EXCL_START
	static void indent(std::ostream& out, size_t depth)
		{ while(depth--) out << "  "; }
	// LCOV_EXCL_STOP

	static bool check_index(size_t& index, size_t size) {
		if(index < size) return true;
		index -= size;
		return false;
	}

	struct Branch {
		const size_t size;
		const NodePtr items[3];

		Branch(const Branch&) = default;
		Branch(Branch&&) = default;
		Branch(size_t size, const NodePtr& n0, const NodePtr& n1, const NodePtr& n2)
			: size(size), items{n0, n1, n2}
			{ assert(n0->depth() == n1->depth());
				assert(!n2 || n0->depth() == n2->depth()); }
	};

	struct Node : public std::variant<Value, Branch> {
		using Variant = std::variant<Value, Branch>;

		template<typename ...Args>
		static inline NodePtr make(Args&&... args) {
			return std::allocate_shared<Node, Allocator, Args...>
				(Allocator{}, std::forward<Args>(args)...);
		}

		explicit Node(const Value& value) : Variant(value) { }
		explicit Node(Value&& value) : Variant(value) { }
		Node(size_t size, const NodePtr& n0, const NodePtr& n1, const NodePtr& n2=nullptr)
			: Variant(Branch(size, n0, n1, n2)) { }
		Node(const NodePtr& n0, const NodePtr& n1)
			: Variant(Branch(n0->size() + n1->size(), n0, n1, nullptr)) { }
		Node(const NodePtr& n0, const NodePtr& n1, const NodePtr& n2)
			: Variant(Branch(n0->size() + n1->size() + n2->size(), n0, n1, n2)) { }

		template<typename Iterator>
		static constexpr NodePtr from(size_t depth, Iterator& values) {
			if(depth == 0) {
				auto node = Node::make(*values);
				++values;
				return node;
			}
			auto x = Node::from(depth - 1, values);
			auto y = Node::from(depth - 1, values);
			auto z = Node::from(depth - 1, values);
			return Node::make(3 * x->size(), x, y, z);
		}

		constexpr size_t size() const {
			return std::visit(overloaded {
				[&](const Value& value) -> size_t { return 1; },
				[&](const Branch& branch) -> size_t { return branch.size; },
			}, *this);
		}

		constexpr size_t depth() const {
			return std::visit(overloaded {
				[&](const Value& value) -> size_t { return 0; },
				[&](const Branch& branch) -> size_t
					{ return branch.items[0]->depth() + 1; },
			}, *this);
		}

		// LCOV_EXCL_START
		void pretty(std::ostream& out, size_t depth) const {
			indent(out, depth);
			return std::visit(overloaded {
				[&](const Value& value) {
					out << "Element " << value << std::endl;
				},
				[&](const Branch& branch) {
					out << "Node" << (branch.items[3] ? 3 : 2)
						<< "[size=" << branch.size << "]" << std::endl;
					branch.items[0]->pretty(out, depth + 1);
					branch.items[1]->pretty(out, depth + 1);
					if(branch.items[2]) branch.items[2]->pretty(out, depth + 1);
				},
			}, *this);
		}
		// LCOV_EXCL_STOP

		constexpr Value value() const
			{ return std::get<0>(*this); }

		constexpr Value operator [](size_t index) const {
			return std::visit(overloaded {
				[&](const Value& value) -> Value
					{ assert(index == 0); return value; },
				[&](const Branch& branch) -> Value {
					assert(index < branch.size);
					if(check_index(index, branch.items[0]->size()))
						return (*branch.items[0])[index];
					if(check_index(index, branch.items[1]->size()))
						return (*branch.items[1])[index];
					assert(branch.items[2]);
					return (*branch.items[2])[index];
				},
			}, *this);
		}

		template<typename Func>
		constexpr typename Sequence<typename std::invoke_result<Func, Value>::type>::NodePtr
		transform(const Func& func) const {
			using RNode = typename Sequence<typename std::invoke_result<Func, Value>::type>::NodePtr;
			return std::visit(overloaded {
				[&](const Value& value) -> RNode { return Node::make(func(value)); },
				[&](const Branch& branch) -> RNode {
					return Node::make(branch.size,
						branch.items[0]->transform(func),
						branch.items[1]->transform(func),
						branch.items[2] ? branch.items[2]->transform(func) : nullptr);
				},
			}, *this);
		}

		constexpr NodePtr set(size_t index, const Value& value) const {
			return std::visit(overloaded {
				[&](const Value& _) -> NodePtr
					{ assert(index == 0); return Node::make(value); },
				[&](const Branch& branch) -> NodePtr {
					assert(index < branch.size);
					if(check_index(index, branch.items[0]->size()))
						return Node::make(branch.size,
							branch.items[0]->set(index, value), branch.items[1], branch.items[2]);
					if(check_index(index, branch.items[1]->size()))
						return Node::make(branch.size,
							branch.items[0], branch.items[1]->set(index, value), branch.items[2]);
					assert(branch.items[2]);
					return Node::make(branch.size,
						branch.items[0], branch.items[1], branch.items[2]->set(index, value));
				},
			}, *this);
		}

		static constexpr std::pair<NodePtr, std::optional<NodePtr>>
		insert(const NodePtr& node, size_t index, const Value& value) {
			assert(index < node->size());
			return std::visit(overloaded {
				[&](const Value& _) -> std::pair<NodePtr, std::optional<NodePtr>>
					{ return {Node::make(value), node}; },
				[&](const Branch& branch) -> std::pair<NodePtr, std::optional<NodePtr>> {
					assert(index < branch.size);
					if(check_index(index, branch.items[0]->size())) {
						auto [node, extra] = Node::insert(branch.items[0], index, value);
						if(!extra) return {Node::make(branch.size + 1,
							node, branch.items[1], branch.items[2]), std::nullopt};
						if(!branch.items[2]) return {Node::make(branch.size + 1,
							node, *extra, branch.items[1]), std::nullopt};
						return {Node::make(branch.items[0]->size() + 1, node, *extra),
							Node::make(branch.items[1], branch.items[2])};
					}
					if(check_index(index, branch.items[1]->size())) {
						auto [node, extra] = Node::insert(branch.items[1], index, value);
						if(!extra) return {Node::make(branch.size + 1,
							branch.items[0], node, branch.items[2]), std::nullopt};
						if(!branch.items[2]) return {Node::make(branch.size + 1,
							branch.items[0], node, *extra), std::nullopt};
						return {Node::make(branch.items[0], node),
							Node::make(*extra, branch.items[2])};
					}
					assert(branch.items[2]); {
						auto [node, extra] = Node::insert(branch.items[2], index, value);
						if(!extra) return {Node::make(branch.size + 1,
							branch.items[0], branch.items[1], node), std::nullopt};
						return {Node::make(branch.items[0], branch.items[1]),
							Node::make(node, *extra)};
					}
				},
			}, *node);
		}

		static constexpr std::pair<NodePtr, std::optional<NodePtr>>
		merge_left(const NodePtr& left, const NodePtr& node) {
			if(!left) return {node, std::nullopt};
			assert(left->depth() + 1 == node->depth());
			return std::visit(overloaded {
				[&](const Value& _) -> std::pair<NodePtr, std::optional<NodePtr>> // LCOV_EXCL_LINE
					{ throw std::logic_error("value node"); }, // LCOV_EXCL_LINE
				[&](const Branch& branch) -> std::pair<NodePtr, std::optional<NodePtr>> {
					if(!branch.items[2]) return {Node::make(left->size() + branch.size,
						left, branch.items[0], branch.items[1]), std::nullopt};
					return {Node::make(left, branch.items[0]),
						Node::make(branch.items[1], branch.items[2])};
				},
			}, *node);
		}

		static constexpr std::pair<NodePtr, std::optional<NodePtr>>
		merge_right(const NodePtr& node, const NodePtr& right) {
			if(!right) return {node, std::nullopt};
			assert(node->depth() == right->depth() + 1);
			return std::visit(overloaded {
				[&](const Value& _) -> std::pair<NodePtr, std::optional<NodePtr>> // LCOV_EXCL_LINE
					{ throw std::logic_error("value node"); }, // LCOV_EXCL_LINE
				[&](const Branch& branch) -> std::pair<NodePtr, std::optional<NodePtr>> {
					if(!branch.items[2]) return {Node::make(right->size() + branch.size,
						branch.items[0], branch.items[1], right), std::nullopt};
					return {Node::make(branch.items[0], branch.items[1]),
						Node::make(branch.items[2], right)};
				},
			}, *node);
		}

		static constexpr std::pair<bool, NodePtr>
		meld_left(const NodePtr& node, const std::pair<NodePtr, std::optional<NodePtr>>& merge) {
			if(merge.second) {
				if(!node) return {true, Node::make(merge.first, *merge.second)};
				return {true, Node::make(node, merge.first, *merge.second)};
			}
			if(!node) return {false, merge.first};
			return {true, Node::make(node, merge.first)};
		}

		static constexpr std::pair<bool, NodePtr>
		meld_right(const std::pair<NodePtr, std::optional<NodePtr>>& merge, const NodePtr& node) {
			if(merge.second) {
				if(!node) return {true, Node::make(merge.first, *merge.second)};
				return {true, Node::make(merge.first, *merge.second, node)};
			}
			if(!node) return {false, merge.first};
			return {true, Node::make(merge.first, node)};
		}

		constexpr std::pair<bool, NodePtr>
		erase(size_t index) const {
			assert(index < this->size());
			return std::visit(overloaded {
				[&](const Value& _) -> std::pair<bool, NodePtr>
					{ return {false, nullptr}; },
				[&](const Branch& branch) -> std::pair<bool, NodePtr> {
					assert(index < branch.size);
					if(check_index(index, branch.items[0]->size())) {
						auto [full, node] = branch.items[0]->erase(index);
						if(full) return {true, Node::make(branch.size - 1,
								node, branch.items[1], branch.items[2])};
						return Node::meld_right(
							Node::merge_left(node, branch.items[1]), branch.items[2]);
					}
					if(check_index(index, branch.items[1]->size())) {
						auto [full, node] = branch.items[1]->erase(index);
						if(full) return {true, Node::make(branch.size - 1,
								branch.items[0], node, branch.items[2])};
						return Node::meld_right(
							Node::merge_right(branch.items[0], node), branch.items[2]);
					}
					assert(branch.items[2]); {
						auto [full, node] = branch.items[2]->erase(index);
						if(full) return {true, Node::make(branch.size - 1,
								branch.items[0], branch.items[1], node)};
						return Node::meld_left(
							branch.items[0], Node::merge_right(branch.items[1], node));
					}
				},
			}, *this);
		}

		static constexpr NodePtr reverse(const NodePtr& node) {
			return std::visit(overloaded {
				[&](const Value& _) { return node; },
				[&](const Branch& branch) {
					if(branch.items[2]) return Node::make(branch.size,
						Node::reverse(branch.items[2]),
						Node::reverse(branch.items[1]),
						Node::reverse(branch.items[0]));
					return Node::make(branch.size,
						Node::reverse(branch.items[1]),
						Node::reverse(branch.items[0]));
				},
			}, *node);
		}
	};

	struct Digit {
		const size_t size;
		const uint_least8_t order;
		const NodePtr items[4];

		template<typename ...Args>
		static inline DigitPtr make(Args&&... args) {
			return std::allocate_shared<Digit, Allocator, Args...>
				(Allocator{}, std::forward<Args>(args)...);
		}

		Digit(const Digit&) = default;
		Digit(Digit&&) = default;
		Digit(size_t size, uint_least8_t order,
			const NodePtr& n0, const NodePtr& n1=nullptr,
			const NodePtr& n2=nullptr, const NodePtr& n3=nullptr)
			: size(size), order(order), items{n0,n1,n2,n3}
			{ assert(n0); assert(1 <= order && order <= 4);
				assert(order < 2 || (n1 && n1->depth() == n0->depth()));
				assert(order < 3 || (n2 && n2->depth() == n0->depth()));
				assert(order < 4 || (n3 && n3->depth() == n0->depth())); }
		explicit Digit(const NodePtr& n0)
			: Digit(n0->size(), 1, n0, nullptr, nullptr, nullptr) { }
		Digit(const NodePtr& n0, const NodePtr& n1)
			: Digit(n0->size() + n1->size(), 2, n0, n1, nullptr, nullptr) { }
		Digit(const NodePtr& n0, const NodePtr& n1, const NodePtr& n2)
			: Digit(n0->size() + n1->size() + n2->size(), 3, n0, n1, n2, nullptr) { }
		Digit(const NodePtr& n0, const NodePtr& n1, const NodePtr& n2, const NodePtr& n3)
			: Digit(n0->size() + n1->size() + n2->size() + n3->size(), 4, n0, n1, n2, n3) { }

		static constexpr DigitPtr from(const NodePtr& node) {
			return std::visit(overloaded {
				[](const Value& value) -> DigitPtr // LCOV_EXCL_LINE
					{ throw std::logic_error("value node"); }, // LCOV_EXCL_LINE
				[](const Branch& branch) -> DigitPtr {
					if(branch.items[2])
						return Digit::make(branch.size, 3,
							branch.items[0], branch.items[1], branch.items[2]);
					return Digit::make(branch.size, 2,
						branch.items[0], branch.items[1]);
				},
			}, *node);
		}

		static constexpr DigitPtr from(uint_least8_t order, const NodePtr* node) {
			switch(order) {
				case 1: assert(node[0]);
					return Digit::make(node[0]);
				case 2: assert(node[0] && node[1]);
					return Digit::make(node[0], node[1]);
				case 3: assert(node[0] && node[1] && node[2]);
					return Digit::make(node[0], node[1], node[2]);
				case 4: assert(node[0] && node[1] && node[2] && node[3]);
					return Digit::make(node[0], node[1], node[2], node[3]);
				default: throw std::out_of_range("bad order");
			}
		}

		static constexpr DigitPtr
		from(const std::pair<NodePtr, std::optional<NodePtr>>& merge) {
			auto [node, extra] = merge;
			if(!extra) return Digit::make(node);
			return Digit::make(node, *extra);
		}

		constexpr size_t depth() const
			{ return this->items[0]->depth(); }

		// LCOV_EXCL_START
		void pretty(std::ostream& out, size_t depth) const {
			indent(out, depth);
			out << "Digit" << this->order
				<< "[size=" << this->size << "]" << std::endl;
			for(uint_least8_t i = 0; i < this->order; ++i)
				this->items[i]->pretty(out, depth + 1);
		}
		// LCOV_EXCL_STOP

		constexpr const NodePtr& back() const
			{ return this->items[this->order - 1]; }

		constexpr DigitPtr push_front(const NodePtr& node) const {
			assert(this->order < 4);
			return Digit::make(this->size + node->size(), this->order + 1,
				node, this->items[0], this->items[1], this->items[2]);
		}

		constexpr DigitPtr push_back(const NodePtr& node) const {
			switch(this->order) {
				case 1: return Digit::make(this->size + node->size(), 2,
					this->items[0], node);
				case 2: return Digit::make(this->size + node->size(), 3,
					this->items[0], this->items[1], node);
				case 3: return Digit::make(this->size + node->size(), 4,
					this->items[0], this->items[1], this->items[2], node);
				default: throw std::logic_error("bad digit order"); // LCOV_EXCL_LINE
			}
		}

		constexpr std::pair<NodePtr, DigitPtr> view_front() const {
			DigitPtr tail;
			switch(this->order) {
				case 2: tail = Digit::make(this->items[1]); break;
				case 3: tail = Digit::make(this->items[1], this->items[2]); break;
				case 4: tail = Digit::make(this->size - this->items[0]->size(), 3,
					this->items[1], this->items[2], this->items[3]); break;
				default: throw std::logic_error("bad digit order"); // LCOV_EXCL_LINE
			}
			return {this->items[0], tail};
		}

		constexpr std::pair<DigitPtr, NodePtr> view_back() const {
			switch(this->order) {
				case 2: return {Digit::make(this->items[0]), this->items[1]};
				case 3: return {Digit::make(this->items[0], this->items[1]), this->items[2]};
				case 4: return {Digit::make(this->size - this->items[3]->size(), 3,
					this->items[0], this->items[1], this->items[2]), this->items[3]};
				default: throw std::logic_error("bad digit order"); // LCOV_EXCL_LINE
			}
		}

		template<typename Func>
		constexpr typename Sequence<typename std::invoke_result<Func, Value>::type>::DigitPtr
		transform(const Func& func) const {
			using RSeq = Sequence<typename std::invoke_result<Func, Value>::type>;
			typename RSeq::NodePtr items[4] = { nullptr, nullptr, nullptr, nullptr };
			switch(this->order) {
				case 4: items[3] = this->items[3]->transform(func); [[fallthrough]];
				case 3: items[2] = this->items[2]->transform(func); [[fallthrough]];
				case 2: items[1] = this->items[1]->transform(func); [[fallthrough]];
				case 1: items[0] = this->items[0]->transform(func); break;
				default: throw std::logic_error("bad digit order"); // LCOV_EXCL_LINE
			}
			return RSeq::Digit::make(this->size, this->order,
				items[0], items[1], items[2], items[3]);
		}

		constexpr Value operator [](size_t index) const {
			assert(index < this->size);
			if(check_index(index, this->items[0]->size()))
				return (*this->items[0])[index];
			if(check_index(index, this->items[1]->size()))
				return (*this->items[1])[index];
			if(check_index(index, this->items[2]->size()))
				return (*this->items[2])[index];
			return (*this->items[3])[index];
		}

		constexpr DigitPtr set(size_t index, const Value& value) const {
			assert(index < this->size);
			if(check_index(index, this->items[0]->size()))
				return Digit::make(this->size, this->order,
					this->items[0]->set(index, value), this->items[1],
					this->items[2], this->items[3]);
			if(check_index(index, this->items[1]->size()))
				return Digit::make(this->size, this->order,
					this->items[0], this->items[1]->set(index, value),
					this->items[2], this->items[3]);
			if(check_index(index, this->items[2]->size()))
				return Digit::make(this->size, this->order,
					this->items[0], this->items[1],
					this->items[2]->set(index, value), this->items[3]);
			return Digit::make(this->size, this->order,
				this->items[0], this->items[1],
				this->items[2], this->items[3]->set(index, value));
		}

		template<bool Left=true>
		constexpr std::pair<DigitPtr, std::optional<NodePtr>>
		insert(size_t index, const Value& value) const {
			assert(index < this->size);
			NodePtr nodes[5] = {nullptr, nullptr, nullptr, nullptr, nullptr};
			uint_least8_t mid = 0;
			for(; !check_index(index, this->items[mid]->size()); ++mid)
				nodes[mid] = this->items[mid];
			assert(mid < this->order);
			auto [node, extra] = Node::insert(this->items[mid], index, value);
			nodes[mid++] = node;
			uint_least8_t order = mid;
			if(extra) nodes[order++] = *extra;
			for(; mid < this->order; ++mid, ++order)
				nodes[order] = this->items[mid];
			if(order < 5)
				return {Digit::make(this->size + 1, order,
					nodes[0], nodes[1], nodes[2], nodes[3]), std::nullopt};
			if constexpr(Left)
				return {Digit::make(nodes[0], nodes[1], nodes[2]),
					Node::make(nodes[3], nodes[4])};
			return {Digit::make(nodes[2], nodes[3], nodes[4]),
				Node::make(nodes[0], nodes[1])};
		}

		constexpr std::variant<NodePtr, DigitPtr> erase(size_t index) const {
			assert(index < this->size);
			NodePtr nodes[4] = {nullptr, nullptr, nullptr, nullptr};
			uint_least8_t mid = 0, order = 0;
			for(; !check_index(index, this->items[mid]->size()); ++mid)
				nodes[mid] = this->items[mid];
			assert(mid < this->order);
			auto [full, node] = this->items[mid]->erase(index);
			if(full) {
				nodes[mid] = node;
				for(uint_least8_t i = mid + 1; i < this->order; ++i)
					nodes[i] = this->items[i];
				order = this->order;
			} else if(this->order == 1) {
				return node;
			} else if(mid + 1 == this->order) {
				auto [merged, extra] = Node::merge_right(this->items[mid - 1], node);
				nodes[mid - 1] = merged;
				if(!extra) {
					order = this->order - 1;
				} else {
					nodes[mid] = *extra;
					order = this->order;
				}
			} else {
				auto [merged, extra] = Node::merge_left(node, this->items[mid + 1]);
				nodes[mid] = merged;
				if(!extra) {
					for(uint_least8_t i = mid + 2; i < this->order; ++i)
						nodes[i - 1] = this->items[i];
					order = this->order - 1;
				} else {
					nodes[mid + 1] = *extra;
					for(uint_least8_t i = mid + 2; i < this->order; ++i)
						nodes[i] = this->items[i];
					order = this->order;
				}
			}
			return Digit::from(order, nodes);
		}

		static constexpr DigitPtr merge_left(const NodePtr& left, const NodePtr& node) {
			if(!left) return Digit::from(node);
			assert(left->depth() + 2 == node->depth());
			return std::visit(overloaded {
				[&](const Value& value) -> DigitPtr // LCOV_EXCL_LINE
					{ throw std::logic_error("value node"); }, // LCOV_EXCL_LINE
				[&](const Branch& branch) -> DigitPtr {
					auto [merge, extra] = Node::merge_left(left, branch.items[0]);
					if(!extra) {
						if(!branch.items[2])
							return Digit::make(merge, branch.items[1]);
						return Digit::make(merge, branch.items[1], branch.items[2]);
					}
					if(!branch.items[2])
						return Digit::make(merge, *extra, branch.items[1]);
					return Digit::make(merge, *extra, branch.items[1], branch.items[2]);
				},
			}, *node);
		}

		static constexpr DigitPtr merge_right(const NodePtr& node, const NodePtr& right) {
			if(!right) return Digit::from(node);
			assert(node->depth() == right->depth() + 2);
			return std::visit(overloaded {
				[&](const Value& value) -> DigitPtr // LCOV_EXCL_LINE
					{ throw std::logic_error("value node"); }, // LCOV_EXCL_LINE
				[&](const Branch& branch) -> DigitPtr {
					if(!branch.items[2]) {
						auto [merge, extra] = Node::merge_right(branch.items[1], right);
						if(!extra) return Digit::make(branch.items[0], merge);
						return Digit::make(branch.items[0], merge, *extra);
					} else {
						auto [merge, extra] = Node::merge_right(branch.items[2], right);
						if(!extra) return Digit::make(branch.items[0], branch.items[1], merge);
						return Digit::make(branch.items[0], branch.items[1], merge, *extra);
					}
				},
			}, *node);
		}

		constexpr DigitPtr reverse() const {
			switch(this->order) {
				case 1: return Digit::make(this->size, 1,
					Node::reverse(this->items[0]));
				case 2: return Digit::make(this->size, 2,
					Node::reverse(this->items[1]),
					Node::reverse(this->items[0]));
				case 3: return Digit::make(this->size, 3,
					Node::reverse(this->items[2]),
					Node::reverse(this->items[1]),
					Node::reverse(this->items[0]));
				case 4: return Digit::make(this->size, 4,
					Node::reverse(this->items[3]),
					Node::reverse(this->items[2]),
					Node::reverse(this->items[1]),
					Node::reverse(this->items[0]));
				default: throw std::logic_error("bad digit order"); // LCOV_EXCL_LINE
			}
		}
	};

	struct Empty {
		constexpr bool operator ==(const Empty&) const { return true; }
		constexpr bool operator !=(const Empty&) const { return false; }
	};

	struct Deep {
		const size_t size;
		const DigitPtr left;
		const Tree middle;
		const DigitPtr right;

		template<typename ...Args>
		static inline DeepPtr make(Args&&... args) {
			return std::allocate_shared<Deep, Allocator, Args...>
				(Allocator{}, std::forward<Args>(args)...);
		}

		Deep(const Deep&) = default;
		Deep(Deep&&) = default;
		Deep(size_t size, const DigitPtr& left,
			const Tree& middle, const DigitPtr& right)
			: size(size), left(left), middle(middle), right(right)
			{ assert(!middle || left->depth() + 1 == middle.depth());
				assert(left->depth() == right->depth()); }
		Deep(const DigitPtr& left, const Tree& middle, const DigitPtr& right)
			: Deep(left->size + middle.size() + right->size, left, middle, right) { }
	};

	struct Tree : public std::variant<Empty, NodePtr, DeepPtr> {
		using Variant = std::variant<Empty, NodePtr, DeepPtr>;

		Tree() : Variant(Empty()) { }
		template<typename ...Args>
		Tree(Args&&... args) : Variant(std::forward<Args>(args)...) { }

		static constexpr Tree from(const DigitPtr& digit) {
			switch(digit->order) {
				case 1: return digit->items[0];
				case 2: return Deep::make(digit->size,
					Digit::make(digit->items[0]), Tree(),
					Digit::make(digit->items[1]));
				case 3: return Deep::make(digit->size,
					Digit::make(digit->items[0], digit->items[1]), Tree(),
					Digit::make(digit->items[2]));
				case 4: return Deep::make(digit->size,
					Digit::make(digit->items[0], digit->items[1]), Tree(),
					Digit::make(digit->items[2], digit->items[3]));
				default: throw std::logic_error("bad digit order"); // LCOV_EXCL_LINE
			}
		}

		template<typename Iterator>
		static constexpr Tree from(size_t count, size_t depth, Iterator& values) {
			if(count == 0) return Tree();
			if(count <= 8) {
				NodePtr nodes[8];
				switch(count) {
					case 8: nodes[7] = Node::from(depth, values); [[fallthrough]];
					case 7: nodes[6] = Node::from(depth, values); [[fallthrough]];
					case 6: nodes[5] = Node::from(depth, values); [[fallthrough]];
					case 5: nodes[4] = Node::from(depth, values); [[fallthrough]];
					case 4: nodes[3] = Node::from(depth, values); [[fallthrough]];
					case 3: nodes[2] = Node::from(depth, values); [[fallthrough]];
					case 2: nodes[1] = Node::from(depth, values); [[fallthrough]];
					case 1: nodes[0] = Node::from(depth, values); break;
					default: throw std::out_of_range("bad count"); // LCOV_EXCL_LINE
				}
				size_t size = nodes[0]->size();
				switch(count) {
					case 1: return nodes[0];
					case 2: return Deep::make(2 * size,
						Digit::make(1 * size, 1, nodes[1]), Tree(),
						Digit::make(1 * size, 1, nodes[0]));
					case 3: return Deep::make(3 * size,
						Digit::make(1 * size, 1, nodes[2]), Tree(),
						Digit::make(2 * size, 2, nodes[1], nodes[0]));
					case 4: return Deep::make(4 * size,
						Digit::make(2 * size, 2, nodes[3], nodes[2]), Tree(),
						Digit::make(2 * size, 2, nodes[1], nodes[0]));
					case 5: return Deep::make(5 * size,
						Digit::make(2 * size, 2, nodes[4], nodes[3]), Tree(),
						Digit::make(3 * size, 3, nodes[2], nodes[1], nodes[0]));
					case 6: return Deep::make(6 * size,
						Digit::make(3 * size, 3, nodes[5], nodes[4], nodes[3]), Tree(),
						Digit::make(3 * size, 3, nodes[2], nodes[1], nodes[0]));
					case 7: return Deep::make(7 * size,
						Digit::make(3 * size, 3, nodes[6], nodes[5], nodes[4]), Tree(),
						Digit::make(4 * size, 4, nodes[3], nodes[2], nodes[1], nodes[0]));
					case 8: return Deep::make(8 * size,
						Digit::make(4 * size, 4, nodes[7], nodes[6], nodes[5], nodes[4]), Tree(),
						Digit::make(4 * size, 4, nodes[3], nodes[2], nodes[1], nodes[0]));
					default: throw std::logic_error("bad count"); // LCOV_EXCL_LINE
				}
			}
			DigitPtr ldigit; {
				NodePtr nodes[3];
				nodes[0] = Node::from(depth, values);
				nodes[1] = Node::from(depth, values);
				nodes[2] = Node::from(depth, values);
				ldigit = Digit::make(3 * nodes[0]->size(), 3,
					nodes[0], nodes[1], nodes[2]);
			}
			Tree middle = Tree::from((count + 2) / 3 - 2, depth + 1, values);
			DigitPtr rdigit; {
				NodePtr nodes[3];
				switch(count % 3) {
					case 0: nodes[2] = Node::from(depth, values); [[fallthrough]];
					case 2: nodes[1] = Node::from(depth, values); [[fallthrough]];
					case 1: nodes[0] = Node::from(depth, values); break;
					default: throw std::logic_error("bad count % 3"); // LCOV_EXCL_LINE
				}
				switch(count % 3) {
					case 1: rdigit = Digit::make(nodes[0]); break;
					case 2: rdigit = Digit::make(nodes[1], nodes[0]); break;
					case 0: rdigit = Digit::make(nodes[2], nodes[1], nodes[0]); break;
					default: throw std::logic_error("bad count % 3"); // LCOV_EXCL_LINE
				}
			}
			return Deep::make(ldigit, middle, rdigit);
		}

		static constexpr Tree from(uint_least8_t count, const NodePtr* nodes) {
			assert(count <= 4);
			switch(count) {
				case 0: return Tree();
				case 1: return nodes[0];
				case 2: return Deep::make(
					Digit::make(nodes[0]), Tree(),
					Digit::make(nodes[1]));
				case 3: return Deep::make(
					Digit::make(nodes[0]), Tree(),
					Digit::make(nodes[1], nodes[2]));
				case 4: return Deep::make(
					Digit::make(nodes[0], nodes[1]), Tree(),
					Digit::make(nodes[2], nodes[3]));
				default: throw std::out_of_range("bad count"); // LCOV_EXCL_LINE
			}
		}

		static constexpr Tree
		from(const std::pair<NodePtr, std::optional<NodePtr>>& merge) {
			auto [node, extra] = merge;
			if(!extra) return node;
			return Deep::make(node->size() + (*extra)->size(),
				Digit::make(node), Tree(), Digit::make(*extra));
		}

		constexpr size_t depth() const {
			return std::visit(overloaded {
				[](const Empty& _) -> size_t { return 0; },
				[](const NodePtr& node) -> size_t { return node->depth(); },
				[](const DeepPtr& deep) -> size_t { return deep->left->depth(); },
			}, *this);
		}

		constexpr operator bool() const
			{ return !std::holds_alternative<Empty>(*this); }

		constexpr size_t size() const {
			return std::visit(overloaded {
				[](const Empty& _) -> size_t { return 0; },
				[](const NodePtr& node) -> size_t { return node->size(); },
				[](const DeepPtr& deep) -> size_t { return deep->size; },
			}, *this);
		}

		// LCOV_EXCL_START
		void pretty(std::ostream& out, size_t depth) const {
			std::visit(overloaded {
				[&](const Empty&)
					{ indent(out, depth); out << "Empty" << std::endl; },
				[&](const NodePtr& node)
					{ node->pretty(out, depth); },
				[&](const DeepPtr& deep) {
					indent(out, depth);
					out << "Deep[size=" << deep->size << "]" << std::endl;
					deep->left->pretty(out, depth + 1);
					deep->middle.pretty(out, depth + 1);
					deep->right->pretty(out, depth + 1);
				},
			}, *this);
		}
		// LCOV_EXCL_STOP

		constexpr Tree push_front(const NodePtr& x) const {
			return std::visit(overloaded {
				[&](const Empty&) -> Tree { return x; },
				[&](const NodePtr& node) -> Tree
					{ return Deep::make(node->size() + x->size(),
						Digit::make(x), Tree(), Digit::make(node)); },
				[&](const DeepPtr& deep) -> Tree {
					if(deep->left->order < 4)
						return Deep::make(deep->size + x->size(),
							deep->left->push_front(x), deep->middle, deep->right);
					auto& items = deep->left->items;
					return Deep::make(deep->size + x->size(),
						Digit::make(x, items[0]),
						deep->middle.push_front(Node::make(
							deep->left->size - items[0]->size(),
							items[1], items[2], items[3])),
						deep->right);
				},
			}, *this);
		}

		constexpr Tree push_back(const NodePtr& x) const {
			return std::visit(overloaded {
				[&](const Empty&) -> Tree { return x; },
				[&](const NodePtr& node) -> Tree
					{ return Deep::make(node->size() + x->size(),
						Digit::make(node), Tree(), Digit::make(x)); },
				[&](const DeepPtr& deep) -> Tree {
					if(deep->right->order < 4)
						return Deep::make(deep->size + x->size(),
							deep->left, deep->middle, deep->right->push_back(x));
					auto& items = deep->right->items;
					return Deep::make(deep->size + x->size(), deep->left,
						deep->middle.push_back(Node::make(
							deep->right->size - items[3]->size(),
							items[0], items[1], items[2])),
						Digit::make(items[3], x));
				},
			}, *this);
		}

		constexpr std::pair<NodePtr, Tree> view_front() const {
			return std::visit(overloaded {
				[](const Empty& _) -> std::pair<NodePtr, Tree>
					{ throw std::out_of_range("empty sequence"); },
				[](const NodePtr& node) -> std::pair<NodePtr, Tree>
					{ return {node, Tree()}; },
				[](const DeepPtr& deep) -> std::pair<NodePtr, Tree> {
					if(deep->left->order == 1)
						return {deep->left->items[0], deep->middle.pull_left(deep->right)};
					auto [head, left] = deep->left->view_front();
					return {head, Deep::make(deep->size - head->size(),
						left, deep->middle, deep->right)};
				},
			}, *this);
		}

		constexpr Tree pull_left(const DigitPtr& right) const {
			if(!*this) return Tree::from(right);
			auto [node, tree] = this->view_front();
			return Deep::make(this->size() + right->size,
				Digit::from(node), tree, right);
		}

		constexpr std::pair<Tree, NodePtr> view_back() const {
			return std::visit(overloaded {
				[](const Empty& _) -> std::pair<Tree, NodePtr>
					{ throw std::out_of_range("empty sequence"); },
				[](const NodePtr& node) -> std::pair<Tree, NodePtr>
					{ return {Tree(), node}; },
				[](const DeepPtr& deep) -> std::pair<Tree, NodePtr> {
					if(deep->right->order == 1)
						return {deep->middle.pull_right(deep->left), deep->right->items[0]};
					auto [right, last] = deep->right->view_back();
					return {Deep::make(deep->size - last->size(),
						deep->left, deep->middle, right), last};
				},
			}, *this);
		}

		constexpr Tree pull_right(const DigitPtr& left) const {
			if(!*this) return Tree::from(left);
			auto [tree, node] = this->view_back();
			return Deep::make(this->size() + left->size,
				left, tree, Digit::from(node));
		}

		constexpr Value operator [](size_t index) const {
			return std::visit(overloaded {
				[&](const Empty& _) -> Value // LCOV_EXCL_LINE
					{ throw std::out_of_range("empty tree"); }, // LCOV_EXCL_LINE
				[&](const NodePtr& node) -> Value
					{ return (*node)[index]; },
				[&](const DeepPtr& deep) -> Value {
					if(check_index(index, deep->left->size))
						return (*deep->left)[index];
					if(check_index(index, deep->middle.size()))
						return deep->middle[index];
					return (*deep->right)[index];
				},
			}, *this);
		}

		constexpr Tree append(const Tree& that) const {
			return std::visit(overloaded {
				[&](const Empty& _) -> Tree
					{ return that; },
				[&](const NodePtr& node) -> Tree
					{ return that.push_front(node); },
				[&](const DeepPtr& left) -> Tree {
					return std::visit(overloaded {
						[&](const Empty& _) -> Tree
							{ return *this; },
						[&](const NodePtr& node) -> Tree
							{ return this->push_back(node); },
						[&](const DeepPtr& right) -> Tree {
							NodePtr mid[8]; uint_least8_t count = 0;
							for(; count < left->right->order; ++count)
								mid[count] = left->right->items[count];
							for(uint_least8_t i = 0; i < right->left->order; ++i, ++count)
								mid[count] = right->left->items[i];
							Tree rtree = right->middle;
							switch(count) {
								case 8: rtree = rtree.push_front(
									Node::make(mid[5], mid[6], mid[7]));
								[[fallthrough]];
								case 5: rtree = rtree.push_front(
									Node::make(mid[2], mid[3], mid[4]));
								[[fallthrough]];
								case 2: rtree = rtree.push_front(
									Node::make(mid[0], mid[1]));
								break;
								case 6: rtree = rtree.push_front(
									Node::make(mid[3], mid[4], mid[5]));
								[[fallthrough]];
								case 3: rtree = rtree.push_front(
									Node::make(mid[0], mid[1], mid[2]));
								break;
								case 7: rtree = rtree.push_front(
									Node::make(mid[4], mid[5], mid[6]));
								[[fallthrough]];
								case 4: rtree = rtree
									.push_front(Node::make(mid[2], mid[3]))
									.push_front(Node::make(mid[0], mid[1]));
								break;
								default: throw std::logic_error("bad mid count"); // LCOV_EXCL_LINE
							}
							return Deep::make(left->size + right->size,
								left->left, left->middle.append(rtree), right->right);
						},
					}, that);
				},
			}, *this);
		}

		constexpr Tree set(size_t index, const Value& value) const {
			return std::visit(overloaded {
				[&](const Empty& _) -> Tree // LCOV_EXCL_LINE
					{ throw std::out_of_range("empty tree"); }, // LCOV_EXCL_LINE
				[&](const NodePtr& node) -> Tree
					{ return node->set(index, value); },
				[&](const DeepPtr& deep) -> Tree {
					if(check_index(index, deep->left->size))
						return Deep::make(deep->size,
							deep->left->set(index, value), deep->middle, deep->right);
					if(check_index(index, deep->middle.size()))
						return Deep::make(deep->size,
							deep->left, deep->middle.set(index, value), deep->right);
					return Deep::make(deep->size,
						deep->left, deep->middle, deep->right->set(index, value));
				},
			}, *this);
		}

		constexpr Tree insert(size_t index, const Value& value) const {
			return std::visit(overloaded {
				[&](const Empty& _) -> Tree // LCOV_EXCL_LINE
					{ throw std::out_of_range("empty tree"); }, // LCOV_EXCL_LINE
				[&](const NodePtr& node) -> Tree {
					auto [node1, extra] = Node::insert(node, index, value);
					if(!extra) return node1;
					return Deep::make(node->size() + 1,
						Digit::make(node1), Tree(),
						Digit::make(*extra));
				},
				[&](const DeepPtr& deep) -> Tree {
					if(check_index(index, deep->left->size)) {
						auto [digit, extra] = deep->left->template insert<true>(index, value);
						auto middle = extra ? deep->middle.push_front(*extra) : deep->middle;
						return Deep::make(deep->size + 1, digit, middle, deep->right);
					}
					if(check_index(index, deep->middle.size())) return Deep::make(deep->size + 1,
						deep->left, deep->middle.insert(index, value), deep->right);
					auto [digit, extra] = deep->right->template insert<false>(index, value);
					auto middle = extra ? deep->middle.push_back(*extra) : deep->middle;
					return Deep::make(deep->size + 1, deep->left, middle, digit);
				},
			}, *this);
		}

		constexpr std::pair<bool, Tree> erase(size_t index) const {
			return std::visit(overloaded {
				[&](const Empty& _) -> std::pair<bool, Tree> // LCOV_EXCL_LINE
					{ throw std::out_of_range("empty tree"); }, // LCOV_EXCL_LINE
				[&](const NodePtr& node) -> std::pair<bool, Tree> {
					auto [full, erased] = node->erase(index);
					if(!erased) return {false, Tree()};
					return {full, erased};
				},
				[&](const DeepPtr& deep) -> std::pair<bool, Tree> {
					if(check_index(index, deep->left->size))
						return std::visit(overloaded {
							[&](const DigitPtr& digit) -> std::pair<bool, Tree> {
								return {true, Deep::make(deep->size - 1,
									digit, deep->middle, deep->right)};
							},
							[&](const NodePtr& node) -> std::pair<bool, Tree> {
								if(deep->middle) {
									auto [head, tail] = deep->middle.view_front();
									return {true, Deep::make(deep->size - 1,
										Digit::merge_left(node, head), tail, deep->right)};
								}
								auto merge = Node::merge_left(node, deep->right->items[0]);
								if(deep->right->order == 1)
									return {true, Tree::from(merge)};
								return {true, Deep::make(deep->size - 1,
									Digit::from(merge), Tree(), deep->right->view_front().second)};
							},
						}, deep->left->erase(index));
					if(check_index(index, deep->middle.size())) {
						auto [full, meld] = deep->middle.erase(index);
						if(full) return {true, Deep::make(deep->size - 1,
							deep->left, meld, deep->right)};
						auto node = std::get<NodePtr>(meld);
						if(deep->left->order == 4)
							return {true, Deep::make(deep->size - 1,
								Digit::make(deep->left->items[0], deep->left->items[1]),
								Node::make(deep->left->items[2], deep->left->items[3], node),
								deep->right)};
						NodePtr nodes[4] = {nullptr, nullptr, nullptr, nullptr};
						for(uint_least8_t i = 0; i < deep->left->order; ++i)
							nodes[i] = deep->left->items[i];
						nodes[deep->left->order] = std::get<NodePtr>(meld);
						return {true, Deep::make(deep->size - 1,
							Digit::from(deep->left->order + 1, nodes),
							Tree(), deep->right)};
					}
					assert(index < deep->right->size);
					return std::visit(overloaded {
						[&](const DigitPtr& digit) -> std::pair<bool, Tree> {
							return {true, Deep::make(deep->size - 1,
								deep->left, deep->middle, digit)};
						},
						[&](const NodePtr& node) -> std::pair<bool, Tree> {
							if(deep->middle) {
								auto [init, last] = deep->middle.view_back();
								return {true, Deep::make(deep->size - 1,
									deep->left, init, Digit::merge_right(last, node))};
							}
							auto merge = Node::merge_right(deep->left->back(), node);
							if(deep->left->order == 1)
								return {true, Tree::from(merge)};
							return {true, Deep::make(deep->size - 1,
								deep->left->view_back().first, Tree(), Digit::from(merge))};
						},
					}, deep->right->erase(index));
				},
			}, *this);
		}

		constexpr std::tuple<Tree, NodePtr, Tree> split(size_t index) const {
			assert(index < this->size());
			return std::visit(overloaded {
				[&](const Empty& _) -> std::tuple<Tree, NodePtr, Tree> // LCOV_EXCL_LINE
					{ throw std::out_of_range("empty tree"); }, // LCOV_EXCL_LINE
				[&](const NodePtr& node) -> std::tuple<Tree, NodePtr, Tree>
					{ return {Empty(), node, Empty()}; },
				[&](const DeepPtr& deep) -> std::tuple<Tree, NodePtr, Tree> {
					if(check_index(index, deep->left->size)) {
						uint_least8_t i = 0;
						for(; !check_index(index, deep->left->items[i]->size()); ++i);
						auto& items = deep->left->items;
						auto right = i + 1 == deep->left->order
							? deep->middle.pull_left(deep->right)
							: Deep::make(Digit::from(
								deep->left->order - i - 1, &items[i+1]),
								deep->middle, deep->right);
						return {Tree::from(i, items), items[i], right};
					}
					if(check_index(index, deep->middle.size())) {
						auto [ltree, node, rtree] = deep->middle.split(index);
						assert(std::get<Branch>(*node).size != 1);
						auto& items = std::get<Branch>(*node).items;
						index -= ltree.size();
						if(check_index(index, items[0]->size()))
							return {ltree.pull_right(deep->left), items[0], Deep::make(
								!items[2] ? Digit::make(items[1])
									: Digit::make(items[1], items[2]),
								rtree, deep->right)};
						if(check_index(index, items[1]->size()))
							return {Deep::make(deep->left, ltree, Digit::make(items[0])),
								items[1], !items[2] ? rtree.pull_left(deep->right)
									: Deep::make(Digit::make(items[2]), rtree, deep->right)};
						assert(items[2]);
						return {Deep::make(deep->left, ltree,
							Digit::make(items[0], items[1])),
							items[2], rtree.pull_left(deep->right)};
					}
					assert(index < deep->right->size); {
						uint_least8_t i = 0;
						auto& items = deep->right->items;
						for(; !check_index(index, items[i]->size()); ++i);
						auto left = i == 0 ? deep->middle.pull_right(deep->left)
							: Deep::make(deep->left, deep->middle, Digit::from(i, &items[0]));
						return {left, items[i],
							Tree::from(deep->right->order - i - 1, &items[i+1])};
					}
				},
			}, *this);
		}

		constexpr std::pair<Tree, NodePtr> take_front(size_t index) const {
			assert(index < this->size());
			return std::visit(overloaded {
				[&](const Empty& _) -> std::pair<Tree, NodePtr> // LCOV_EXCL_LINE
					{ throw std::out_of_range("empty tree"); }, // LCOV_EXCL_LINE
				[&](NodePtr node) -> std::pair<Tree, NodePtr>
					{ return {Empty(), node}; },
				[&](const DeepPtr& deep) -> std::pair<Tree, NodePtr> {
					if(check_index(index, deep->left->size)) {
						uint_least8_t i = 0;
						auto& items = deep->left->items;
						for(; !check_index(index, items[i]->size()); ++i);
						return {Tree::from(i, items), items[i]};
					}
					if(check_index(index, deep->middle.size())) {
						auto [tree, node] = deep->middle.take_front(index);
						assert(index >= tree.size());
						index -= tree.size();
						auto& branch = std::get<Branch>(*node);
						if(check_index(index, branch.items[0]->size()))
							return {tree.pull_right(deep->left), branch.items[0]};
						if(check_index(index, branch.items[1]->size()))
							return {Deep::make(deep->left, tree,
								Digit::make(branch.items[0])), branch.items[1]};
						assert(branch.items[2]);
						return {Deep::make(deep->left, tree,
							Digit::make(branch.items[0], branch.items[1])), branch.items[2]};
					}
					assert(index < deep->right->size); {
						uint_least8_t i = 0;
						auto& items = deep->right->items;
						for(; !check_index(index, items[i]->size()); ++i);
						if(i == 0) return {deep->middle.pull_right(deep->left), items[i]};
						return {Deep::make(deep->left, deep->middle,
							Digit::from(i, items)), items[i]};
					}
				},
			}, *this);
		}

		constexpr std::pair<NodePtr, Tree> take_back(size_t index) const {
			assert(index < this->size());
			return std::visit(overloaded {
				[&](const Empty& _) -> std::pair<NodePtr, Tree> // LCOV_EXCL_LINE
					{ throw std::out_of_range("empty tree"); }, // LCOV_EXCL_LINE
				[&](NodePtr node) -> std::pair<NodePtr, Tree>
					{ return {node, Empty()}; },
				[&](const DeepPtr& deep) -> std::pair<NodePtr, Tree> {
					if(check_index(index, deep->right->size)) {
						uint_least8_t i = deep->right->order - 1;
						auto& items = deep->right->items;
						while(!check_index(index, items[i]->size())) --i;
						return {items[i], Tree::from(deep->right->order - i - 1, &items[i+1])};
					}
					if(check_index(index, deep->middle.size())) {
						auto [node, tree] = deep->middle.take_back(index);
						assert(index >= tree.size());
						index -= tree.size();
						auto& branch = std::get<Branch>(*node);
						if(branch.items[2])
							if(check_index(index, branch.items[2]->size()))
								return {branch.items[2], tree.pull_left(deep->right)};
						if(check_index(index, branch.items[1]->size()))
							return {branch.items[1], !branch.items[2] ? tree.pull_left(deep->right)
								: Deep::make(Digit::make(branch.items[2]), tree, deep->right)};
						return {branch.items[0], Deep::make(
							!branch.items[2] ? Digit::make(branch.items[1])
								: Digit::make(branch.items[1], branch.items[2]),
							tree, deep->right)};
					}
					assert(index < deep->left->size); {
						uint_least8_t i = deep->left->order - 1;
						auto& items = deep->left->items;
						while(!check_index(index, items[i]->size())) --i;
						if(i + 1 == deep->left->order)
							return {items[i], deep->middle.pull_left(deep->right)};
						return {items[i], Deep::make(
							Digit::from(deep->left->order - i - 1, &items[i+1]),
							deep->middle, deep->right)};
					}
				},
			}, *this);
		}

		template<typename Func>
		constexpr typename Sequence<typename std::invoke_result<Func, Value>::type>::Tree
		transform(const Func& func) const {
			using RTree = typename Sequence<typename std::invoke_result<Func, Value>::type>::Tree;
			return std::visit(overloaded {
				[&](const Empty& _) -> RTree { return Empty(); },
				[&](NodePtr node) -> RTree { return node->transform(func); },
				[&](const DeepPtr& deep) -> RTree {
					return Deep::make(deep->size,
						deep->left->transform(func),
						deep->middle.transform(func),
						deep->right->transform(func));
				},
			}, *this);
		}

		constexpr Tree reverse() const {
			return std::visit(overloaded {
				[&](const Empty& _) -> Tree { return Empty(); },
				[&](const NodePtr& node) -> Tree { return Node::reverse(node); },
				[&](const DeepPtr& deep) -> Tree {
					return Deep::make(deep->right->reverse(),
						deep->middle.reverse(), deep->left->reverse());
				},
			}, *this);
		}
	};

	using value_type = const Value;
	using size_type = size_t;
	using diference_type = std::ptrdiff_t;
	using const_reference = const Value&;
	using reference = const_reference;

	Tree tree;

	Sequence() : tree() { }
	Sequence(const Sequence&) = default;
	Sequence(Tree&& tree) : tree(std::move(tree)) { }
	Sequence(std::initializer_list<Value> xs)
		: Sequence(xs.begin(), xs.end()) { }

	template<typename Iterator>
	Sequence(size_t size, Iterator left)
		: tree(Tree::from(size, 0, left)) { }
	template<typename Iterator>
	Sequence(Iterator left, const Iterator& right, std::random_access_iterator_tag)
		: tree(Tree::from((size_t)std::distance(left, right), 0, left)) { }
	template<typename Iterator>
	Sequence(Iterator left, const Iterator& right, std::input_iterator_tag) : tree() {
		while(left != right) {
			this->tree = this->tree.push_back(Node::make(*left));
			++left;
		}
	}
	template<typename Iterator>
	Sequence(Iterator left, const Iterator& right) : Sequence(left, right,
		typename std::iterator_traits<Iterator>::iterator_category()) { }

	// LCOV_EXCL_START
	void pretty(std::ostream& out) const
		{ this->tree.pretty(out, 0); }
	std::string pretty() const {
		std::ostringstream out;
		this->pretty(out);
		return out.str();
	}
	// LCOV_EXCL_STOP

	constexpr size_t size() const
		{ return this->tree.size(); }

	constexpr operator bool() const
		{ return bool(this->tree); }
	constexpr bool empty() const
		{ return !this->tree; }

	constexpr Sequence push_front(const Value& value) const
		{ return this->tree.push_front(Node::make(value)); }

	constexpr Sequence push_back(const Value& value) const
		{ return this->tree.push_back(Node::make(value)); }

	constexpr Value front() const {
		return std::visit(overloaded {
			[](const Empty& _) -> Value
				{ throw std::out_of_range("empty sequence"); },
			[](const NodePtr& node) -> Value
				{ return node->value(); },
			[](const DeepPtr& deep) -> Value
				{ return deep->left->items[0]->value(); },
		}, this->tree);
	}

	constexpr Value back() const {
		return std::visit(overloaded {
			[](const Empty& _) -> Value
				{ throw std::out_of_range("empty sequence"); },
			[](const NodePtr& node) -> Value
				{ return node->value(); },
			[](const DeepPtr& deep) -> Value
				{ return deep->right->back()->value(); },
		}, this->tree);
	}

	constexpr std::pair<Value, Sequence> view_front() const {
		auto [head, tail] = this->tree.view_front();
		return {head->value(), Sequence(std::move(tail))};
	}

	constexpr std::pair<Sequence, Value> view_back() const {
		auto [init, last] = this->tree.view_back();
		return {Sequence(std::move(init)), last->value()};
	}

	constexpr Value operator [](size_t index) const
		{ return this->tree[index]; }

	constexpr Value at(size_t index) const {
		if(index >= this->size())
			throw std::out_of_range("out of range");
		return this->tree[index];
	}

	constexpr Sequence at(size_t left, size_t right) const {
		if(left >= right) Sequence();
		if(left == 0) this->take_front(right);
		if(right >= this->size()) this->drop_front(left);
		return this->take_front(right).drop_front(left);
	}

	constexpr Sequence append(const Sequence& that) const
		{ return this->tree.append(that.tree); }

	constexpr Sequence repeat(size_t times) const {
		if(times == 0) return Sequence();
		Tree result, tree = this->tree;
		while(true) {
			if(times & 1) result = tree.append(result);
			if(!(times >>= 1)) break;
			tree = tree.append(tree);
		}
		return result;
	}

	constexpr Sequence set(size_t index, const Value& value) const {
		if(index >= this->size())
			throw std::out_of_range("out of range");
		return this->tree.set(index, value);
	}

	constexpr Sequence set(size_t left, size_t right, const Sequence& values) const {
		if(left > right) right = left;
		return this->take_front(left).append(values).append(this->drop_front(right));
	}

	template<typename Iterator>
	constexpr Sequence set(
		size_t left,
		size_t right,
		size_t step,
		Iterator values,
		const Iterator& end
	) const {
		auto count = adjust_index(this->size(), left, right, step);
		if(step-- == 1) return this->set(left, right, Sequence(values, end));
		if(count == 0) return *this;
		auto [keep, _, rest] = this->tree.split(left);
		if(values == end) throw std::out_of_range("not enough items");
		keep = keep.push_back(Node::make(*values));
		++values;
		while(--count) {
			auto [chunk, _, rest1] = rest.split(step);
			if(values == end) throw std::out_of_range("not enough items");
			keep = keep.append(chunk).push_back(Node::make(*values));
			++values;
			rest = std::move(rest1);
		}
		if(values != end) throw std::out_of_range("too many items");
		return keep.append(rest);
	}

	constexpr Sequence insert(size_t index, const Value& value) const {
		if(index >= this->size())
			throw std::out_of_range("out of bounds");
		return this->tree.insert(index, value);
	}

	constexpr Sequence erase(size_t index) const {
		if(index >= this->size())
			throw std::out_of_range("out of bounds");
		auto [full, tree] = this->tree.erase(index);
		if(!full) return Sequence();
		return Sequence(std::move(tree));
	}

	constexpr Sequence erase(size_t left, size_t right) const {
		if(left >= right) return *this;
		if(left == 0) return this->drop_front(right);
		if(right >= this->size()) return this->take_front(left);
		return this->take_front(left).append(this->drop_front(right));
	}

	constexpr Sequence erase(size_t left, size_t right, size_t step) const {
		auto count = adjust_index(this->size(), left, right, step);
		if(count == 0) return *this;
		if(step-- == 1) return this->erase(left, right);
		auto [keep, _, rest] = this->tree.split(left);
		while(--count) {
			auto [chunk, _, rest1] = rest.split(step);
			keep = keep.append(chunk);
			rest = std::move(rest1);
		}
		return keep.append(rest);
	}

	constexpr std::tuple<Sequence, Value, Sequence> split(size_t index) const {
		if(index >= this->size())
			throw std::out_of_range("out of bounds");
		auto [left, node, right] = this->tree.split(index);
		return {std::move(left), node->value(), std::move(right)};
	}

	constexpr std::tuple<Sequence, Sequence> splitat(size_t index) const {
		if(index >= this->size()) return {*this, Sequence()};
		auto [left, value, right] = this->split(index);
		return {std::move(left), right.push_front(std::move(value))};
	}

	constexpr Sequence take_front(size_t index) const {
		if(index == 0) return Sequence();
		if(index >= this->size()) return *this;
		auto [tree, node] = this->tree.take_front(index);
		return Sequence(std::move(tree));
	}

	constexpr Sequence drop_back(size_t index) const
		{ return this->take_front(this->size() - std::min(this->size(), index)); }

	constexpr Sequence take_back(size_t index) const {
		if(index == 0) return Sequence();
		if(index >= this->size()) return *this;
		auto [node, tree] = this->tree.take_back(index);
		return Sequence(std::move(tree));
	}

	constexpr Sequence drop_front(size_t index) const
		{ return this->take_back(this->size() - std::min(this->size(), index)); }

	constexpr Sequence reverse() const
		{ return this->tree.reverse(); }

	template<typename Func>
	constexpr Sequence<typename std::invoke_result<Func, Value>::type>
	transform(const Func& func) const
		{ return Sequence(this->tree.transform(func)); }

	template<bool Reverse=false>
	struct Iterator {
		using value_type = const Value;
		using difference_type = std::ptrdiff_t;
		using reference = const Value&;
		using pointer = const Value*;
		using iterator_category = std::forward_iterator_tag;

		using Stack = List<std::variant<NodePtr, DigitPtr, Tree>>;
		Stack stack;

		Iterator() : stack() { }
		Iterator(const Iterator&) = default;
		Iterator(Iterator&&) = default;
		explicit Iterator(const Sequence& seq)
			: stack(seq.tree, Stack())
			{ this->advance(0); }

		const void advance(size_t n) {
			if(this->stack.empty()) return;
			std::visit(overloaded {
				[&](NodePtr node) {
					return std::visit(overloaded {
						[&](const Value& value) {
							if(n == 0) return;
							this->stack = this->stack.tail();
							this->advance(n - 1);
						},
						[&](const Branch& branch) {
							this->stack = this->stack.tail();
							if(check_index(n, branch.size)) {
								if(Reverse)
									this->stack = Stack(branch.items[1],
										Stack(branch.items[0], this->stack));
								if(branch.items[2]) this->stack =
									Stack(branch.items[2], this->stack);
								if(!Reverse)
									this->stack = Stack(branch.items[0],
										Stack(branch.items[1], this->stack));
							}
							this->advance(n);
						},
					}, *node);
				},
				[&](DigitPtr digit) {
					this->stack = this->stack.tail();
					if(check_index(n, digit->size)) {
						if(Reverse) {
							this->stack = Stack(digit->items[0], this->stack);
							if(digit->order >= 2) this->stack = Stack(digit->items[1], this->stack);
							if(digit->order >= 3) this->stack = Stack(digit->items[2], this->stack);
							if(digit->order >= 4) this->stack = Stack(digit->items[3], this->stack);
						} else switch(digit->order) {
							case 4: this->stack = Stack(digit->items[3], this->stack); [[fallthrough]];
							case 3: this->stack = Stack(digit->items[2], this->stack); [[fallthrough]];
							case 2: this->stack = Stack(digit->items[1], this->stack); [[fallthrough]];
							case 1: this->stack = Stack(digit->items[0], this->stack); break;
							default: throw std::logic_error("bad count"); // LCOV_EXCL_LINE
						}
					}
					this->advance(n);
				},
				[&](Tree tree) {
					this->stack = this->stack.tail();
					if(check_index(n, tree.size())) {
						std::visit(overloaded {
							[&](const Empty& _) { },
							[&](const NodePtr& node)
								{ this->stack = Stack(node, this->stack); },
							[&](const DeepPtr& deep) {
								this->stack = Stack(Reverse ? deep->left : deep->right, this->stack);
								this->stack = Stack(deep->middle, this->stack);
								this->stack = Stack(Reverse ? deep->right : deep->left, this->stack);
							},
						}, tree);
					}
					this->advance(n);
				},
			}, this->stack.head());
		}

		constexpr Iterator& operator ++() {
			this->stack = this->stack.tail();
			this->advance(0);
			return *this;
		}

		constexpr Iterator operator ++(int)
			{ Iterator copy(*this); ++*this; return copy; }

		constexpr Iterator operator +(size_t n) {
			Iterator copy(*this);
			copy.advance(n);
			return copy;
		}

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

	template<typename Container, typename Equal=std::equal_to<Value>>
	constexpr bool operator ==(const Container& that) const {
		// if(this->size() != that.size()) return false;
		return equal_iterator<decltype(this->begin()), decltype(that.begin()), Equal>
			(this->begin(), this->end(), that.begin(), that.end());
	}
	template<typename Container, typename Equal=std::equal_to<Value>>
	constexpr bool operator !=(const Container& that) const
		{ return !this->template operator == <Container, Equal>(that); }

	template<typename Container, typename Compare=std::less<Value>>
	constexpr bool operator <(const Container& that) const {
		return less_iterator<decltype(this->begin()), decltype(that.begin()), Compare>
			(this->begin(), this->end(), that.begin(), that.end());
	}
	template<typename Container, typename Compare=std::less<Value>>
	constexpr bool operator >=(const Container& that) const
		{ return !this->template operator < <Container, Compare>(that); }

	template<typename Container, typename Compare=std::less<Value>>
	constexpr bool operator >(const Container& that) const {
		return less_iterator<decltype(that.begin()), decltype(this->begin()), Compare>
			(that.begin(), that.end(), this->begin(), this->end());
	}
	template<typename Container, typename Compare=std::less<Value>>
	constexpr bool operator <=(const Container& that) const
		{ return !this->template operator > <Container, Compare>(that); }

	struct StepIterator : public iterator {
		size_t step;

		template<typename ...Args>
		StepIterator(size_t step, Args&&... args)
			: step(step), iterator(std::forward<Args>(args)...) { }

		constexpr StepIterator& operator ++() {
			this->stack = (*this + this->step).stack;
			return *this;
		}

		constexpr StepIterator operator ++(int)
			{ StepIterator copy(*this); ++*this; return copy; }
	};

	constexpr Sequence at(size_t left, size_t right, size_t step) const {
		auto count = adjust_index(this->size(), left, right, step);
		if(count == 0) return Sequence();
		if(step == 1) return this->at(left, right);
		StepIterator iter(step, this->drop_front(left));
		return Tree::from(count, 0, iter);
	}
};

}

template<typename Value, typename Allocator>
struct std::hash<pyrsistent::Sequence<Value, Allocator>>
	: public pyrsistent::HashIterable<pyrsistent::Sequence<Value, Allocator>> { };

