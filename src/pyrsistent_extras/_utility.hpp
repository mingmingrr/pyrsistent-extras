#pragma once

#include <functional>
#include <utility>
#include <cstdlib>
#include <iostream>

namespace pyrsistent {

template<typename Container>
inline size_t hash_combine(size_t seed, const Container& value) {
	return std::hash<Container>{}(value) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
}

template<typename Container>
struct HashIterable {
	size_t operator () (const Container& xs) {
		size_t seed = 0x9e3779b9;
		for(auto& x: xs) seed = pyrsistent::hash_combine(seed, x);
		return seed;
	}
};

template<typename Value, typename Compare>
constexpr std::pair<const Value&, const Value&> ordered(
	Compare&& cmp,
	const Value& x,
	const Value& y
) {
	if(cmp(x.value, y.value))
		return {x, y};
	return {y, x};
}

template<typename Value, typename Compare>
constexpr std::pair<Value, Value> ordered(
	Compare&& cmp,
	Value&& x,
	Value&& y
) {
	if(cmp(x.value, y.value))
		return {x, y};
	return {y, x};
}

template<typename Value>
struct Boxed {
	const Value& value;
	explicit Boxed(const Value& value) : value(value) { }
};

template<class... Ts>
struct overloaded : Ts... { using Ts::operator()...; };
template<class... Ts>
overloaded(Ts...) -> overloaded<Ts...>;

// template<typename Iterator, typename Function, typename Equal=
	// std::equal_to<typename std::iterator_traits<Iterator>::value_type>>
// constexpr decltype(auto) groups_of(
	// Iterator left, const Iterator& right, const Function& func
// ) {
	// while(left != right) {
		// Iterator start = left;
		// while(++left != right && Equal{}(*start, *left));
		// auto value = func(start, left);
		// if(value) return value;
	// }
	// return decltype(func(left, right))();
// }

template<typename Iterator>
struct ShowIterator {
	Iterator left;
	Iterator right;
	std::string open;
	std::string close;
	std::string sep;

	ShowIterator(const Iterator& left, const Iterator& right,
		const std::string& open, const std::string& close, const std::string& sep)
		: left(left), right(right), open(open), close(close), sep(sep) { }

	friend std::ostream& operator <<(std::ostream& out, const ShowIterator& conf) {
		Iterator iter(conf.left);
		if(iter == conf.right) return out << conf.open << conf.close;
		out << conf.open << *iter;
		while(++iter != conf.right)
			out << conf.sep << *iter;
		out << conf.close;
		return out;
	}
};

template<typename Iterator1, typename Iterator2, typename Equal=
	std::equal_to<typename std::iterator_traits<Iterator1>::value_type>>
constexpr bool equal_iterator(
	Iterator1 xs, const Iterator1& xl,
	Iterator2 ys, const Iterator2& yl
) {
	while((xs != xl) && (ys != yl)) {
		if(!Equal{}(*xs, *ys)) return false;
		++xs; ++ys;
	}
	return (xs == xl) && (ys == yl);
}

template<typename Iterator1, typename Iterator2, typename Compare=
	std::less<typename std::iterator_traits<Iterator1>::value_type>>
constexpr bool less_iterator(
	Iterator1 xs, const Iterator1& xl,
	Iterator2 ys, const Iterator2& yl
) {
	while((xs != xl) && (ys != yl)) {
		if(Compare{}(*xs, *ys)) return true;
		if(Compare{}(*ys, *xs)) return false;
		++xs; ++ys;
	}
	return ys != yl;
}

template<typename Value, typename Compare=std::less<Value>>
struct CompareDown : public Compare {
	inline constexpr bool operator ()(const Value& x, const Value& y) const
		{ return Compare::operator()(y, x); }
	inline constexpr bool operator ()(Value&& x, Value&& y) const
		{ return Compare::operator()(y, x); }
};

template<typename T>
T adjust_index(T length, T index) {
	assert(length >= 0);
	constexpr bool sign = std::is_signed<T>::value;
	if(sign && index < 0) {
		index += length;
		if(index < 0)
			throw std::out_of_range("index out of range");
	} else if(index >= length)
		throw std::out_of_range("index out of range");
	return index;
}

template<typename T>
T adjust_index(T length, T& start, T& stop, T& step) {
	assert(length >= 0);
	if(step == 0) throw std::out_of_range("zero slice step");
	constexpr bool sign = std::is_signed<T>::value;
	if(sign && start < 0) {
		start += length;
		if(sign && start < 0)
			start = (sign && step < 0) ? -1 : 0;
	} else if(start >= length)
		start = (sign && step < 0) ? length - 1 : length;
	if(sign && stop < 0) {
		stop += length;
		if(sign && stop < 0)
			stop = (sign && step < 0) ? -1 : 0;
	} else if(stop >= length)
		stop = (sign && step < 0) ? length - 1 : length;
	T count = 0;
	if(sign && step < 0) {
		if(stop < start)
			count = (start - stop - 1) / (-step) + 1;
	} else if(start < stop)
		count = (stop - start - 1) / step + 1;
	if(sign && step < 0) {
		T tstart = start + (count - 1) * step;
		stop = start + 1; start = tstart; step = -step;
	}
	return count;
}

}
