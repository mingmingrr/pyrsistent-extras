#pragma once

#include <optional>
#include <memory>
#include <stdexcept>

namespace pyrsistent {

template<typename Value, typename Allocator=std::allocator<Value>>
struct List {
	struct Cons;
	using ConsPtr = std::shared_ptr<Cons>;
	using ListT = List<Value, Allocator>;

	struct Cons {
		const Value head;
		const ListT tail;

		template<typename ...Args>
		static inline ConsPtr allocate(Args&&... args) {
			return std::allocate_shared<Cons, Allocator, Args...>
				(Allocator{}, std::forward<Args>(args)...);
		}

		Cons(const Value& head, const ListT& tail)
			: head(head), tail(tail) { }
	};

	ConsPtr list;

	List() : list(nullptr) { }
	List(const ListT&) = default;
	List(ListT&&) = default;
	explicit List(const ConsPtr& list) : list(list) { }
	explicit List(const ConsPtr&& list) : list(list) { }
	List(const Value& head, const ListT& tail)
		: list(Cons::allocate(head, tail)) { }

	template<typename Iterator>
	List(Iterator left, Iterator right) : list(nullptr) {
		ConsPtr* last = &this->list;
		while(left != right) {
			const Value& head = *left++;
			*last = Cons::allocate(head, List(nullptr));
			last = const_cast<ConsPtr*>(&(*last)->tail.list);
		}
	}

	inline List& operator =(const List& list) noexcept
		{ this->list = list.list; return *this; }
	inline List& operator =(List&& list) noexcept
		{ this->list = list.list; return *this; }

	inline constexpr bool empty() const
		{ return !(bool)this->list; }

	inline constexpr const Value& head() const {
		if(!this->list) [[unlikely]] throw std::logic_error("empty list");
		return this->list->head;
	}

	inline constexpr const List& tail() const {
		if(!this->list) [[unlikely]] throw std::logic_error("empty list");
		return this->list->tail;
	}

	constexpr size_t size() const {
		size_t s = 0;
		for(ConsPtr xs = this->list; xs; xs = xs->tail.list) ++s;
		return s;
	}

	constexpr List reverse() const {
		ConsPtr rs = nullptr;
		for(ConsPtr xs = this->list; xs; xs = xs->tail.list)
			rs = Cons::allocate(xs->head, rs);
		return List(rs);
	}

	constexpr bool operator ==(const List& that) const {
		if(this->list == that.list) return true;
		if(this->empty() && that.empty()) return true;
		if(this->empty() != that.empty()) return false;
		if(this->head() != that.head()) return false;
		return this->tail() == that.tail();
	}

	inline constexpr bool operator !=(const List& that) const
		{ return !(*this == that); }

	constexpr bool operator <(const List& that) const {
		if(this->list == that.list) return false;
		if(that.empty()) return false;
		if(this->empty()) return true;
		if(this->head() < that.head()) return true;
		if(that.head() < this->head()) return false;
		return this->tail() < that.tail();
	}

	inline constexpr bool operator >(const List& that) const
		{ return (that < *this); }
	inline constexpr bool operator <=(const List& that) const
		{ return !(that < *this); }
	inline constexpr bool operator >=(const List& that) const
		{ return !(*this < that); }

	struct iterator {
		using value_type = const Value;
		using difference_type = std::ptrdiff_t;
		using reference = const Value&;
		using pointer = const Value*;
		using iterator_category = std::forward_iterator_tag;

		ListT list;

		iterator() : list() { }
		iterator(const iterator&) = default;
		iterator(iterator&&) = default;
		explicit iterator(List&& list) : list(list) { }
		explicit iterator(const List& list) : list(list) { }
		iterator& operator =(const iterator&) = default;
		iterator& operator =(iterator&&) = default;

		inline constexpr iterator& operator ++()
			{ this->list = this->list.tail(); return *this; }
		inline constexpr const Value& operator *() const
			{ return this->list.head(); }
		inline constexpr bool operator ==(const iterator& that) const
			{ return this->list.list == that.list.list; }
		inline constexpr bool operator !=(const iterator& that) const
			{ return !(*this == that); }

		inline constexpr operator bool() const noexcept
			{ return this->list.empty(); }
	};

	inline constexpr iterator begin() const
		{ return iterator(*this); }
	inline constexpr iterator end() const
		{ return iterator(); }

	using const_iterator = iterator;
};

}
