#include <rapidcheck.h>
#include <gtest/gtest.h>
#include <rapidcheck/gtest.h>

#include "_utility.hpp"

namespace pyr = pyrsistent;

RC_GTEST_PROP(Utility, adjust_index, (ssize_t length, ssize_t index)) {
	length = std::abs(length) >> 1;
	if(-length <= index && index < length)
		RC_ASSERT(pyr::adjust_index(length, index)
			== (index % length + length) % length);
	else
		RC_ASSERT_THROWS(pyr::adjust_index(length, index));
}

RC_GTEST_PROP(Utility, adjust_index_step, (
	ssize_t length, ssize_t left, ssize_t right, ssize_t step
)) {
	length = std::abs(length);
	if(step != 0) {
		auto w = length, l = left, r = right, s = step;
		auto count = pyr::adjust_index(w, l, r, s);
		RC_ASSERT(w == length);
		RC_ASSERT(s == std::abs(step));
		if(count != 0) {
			RC_ASSERT(0 <= l);
			RC_ASSERT(0 <= r);
			RC_ASSERT(l <= length);
			RC_ASSERT(r <= length);
			RC_ASSERT(l <= r);
		}
	} else RC_ASSERT_THROWS(pyr::adjust_index(length, left, right, step));
}

RC_GTEST_PROP(Utility, ordered, (int x, int y)) {
	auto [a, b] = pyr::ordered(std::less<int>{}, pyr::Boxed{x}, pyr::Boxed{y});
	RC_ASSERT(a.value <= b.value);
	auto [c, d] = pyr::ordered(std::greater<int>{}, pyr::Boxed{x}, pyr::Boxed{y});
	RC_ASSERT(c.value >= d.value);
}

RC_GTEST_PROP(Utility, ShowIterator, (std::vector<int> xs)) {
	std::ostringstream out1, out2;
	out1 << pyr::ShowIterator(xs.begin(), xs.end(), "[", "]", ", ");
	rc::show(xs, out2);
	RC_ASSERT(out1.str() == out2.str());
}

RC_GTEST_PROP(Utility, equal_iterator, (std::vector<int> xs, std::vector<int> ys)) {
	RC_ASSERT(pyr::equal_iterator(xs.begin(), xs.end(), ys.begin(), ys.end()) == (xs == ys));
}

RC_GTEST_PROP(Utility, less_iterator, (std::vector<int> xs, std::vector<int> ys)) {
	RC_ASSERT(pyr::less_iterator(xs.begin(), xs.end(), ys.begin(), ys.end()) == (xs < ys));
}

RC_GTEST_PROP(Utility, CompareDown, (int x, int y)) {
	RC_ASSERT(pyr::CompareDown<int>{}(x, y) == (y < x));
}

