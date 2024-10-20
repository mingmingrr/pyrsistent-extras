#pragma once

#include <variant>
#include <tuple>
#include <utility>
#include <optional>
#include <functional>
#include <regex>
#include <sstream>

#include <nanobind/nanobind.h>
#include <nanobind/operators.h>

#include "_utility.hpp"

namespace pyrsistent {
namespace nanobind {

namespace nb = ::nanobind;

template<typename Iterator>
struct object_iterator : public Iterator {
	using value_type = nb::object;
	using iterator_category = std::input_iterator_tag;
	template<typename... Args>
	object_iterator(Args&& ...args)
		: Iterator(std::forward<Args>(args)...) { }
	inline nb::object operator *()
		{ return nb::borrow(Iterator::operator*()); }
	inline object_iterator operator ++()
		{ return object_iterator(Iterator::operator++()); }
};

template<typename Iterator>
struct repr_iterator : public Iterator {
	template<typename... Args>
	repr_iterator(Args&& ...args)
		: Iterator(std::forward<Args>(args)...) { }
	inline std::string operator *() {
		nb::str obj = nb::repr(Iterator::operator*());
		return std::string(obj.c_str());
	}
	inline repr_iterator operator ++()
		{ return repr_iterator(Iterator::operator++()); }
	inline repr_iterator operator ++(int x)
		{ return repr_iterator(Iterator::operator++(x)); }
};

struct object_view : public nb::object {
	using iterator = object_iterator<nb::iterator>;
	template<typename... Args>
	object_view(Args&& ...args)
		: nb::object(std::forward<Args>(args)...) { }
	inline iterator begin() const
		{ return iterator(nb::object::begin()); }
	inline iterator end() const
		{ return iterator(nb::object::end()); }
};

// template<typename ...Args>
// nb::object evolver_inherit(Args... args)
	// { return evolver_inherit([](auto evo) { return evo.def; }); }

inline std::tuple<nb::object, std::string, std::string> inherit_docstring(
	nb::object src_obj, const char* src_attr,
	nb::object dest_obj, const char* dest_attr,
	std::variant<std::nullopt_t, const char*,
		std::function<std::string(std::string)>> docstring,
	std::variant<std::nullopt_t, const char*,
		std::function<std::string(std::string)>> signature
) {
	nb::object func = src_obj.attr(src_attr);
	const char* src_cls = nb::str(src_obj.attr("__name__")).c_str();
	std::string doc = std::visit(overloaded {
		[&](std::nullopt_t) { return (std::ostringstream()
			<< "See :meth:`" << src_cls << "." << src_attr << "`").str(); },
		[&](const char* prefix) { return (std::ostringstream()
			<< prefix << " :meth:`" << src_cls << "." << src_attr << "`").str(); },
		[&](auto func) { return func((std::ostringstream()
			<< ":meth:`" << src_cls << "." << src_attr << "`").str()); },
	}, docstring);
	std::string sig; do {
		nb::object nbsig = nb::getattr(func, "__nb_signature__", nb::none());
		if(!nb::isinstance<nb::tuple>(nbsig)) break;
		if(nb::len(nbsig) < 1) break;
		nbsig = nbsig[0];
		if(!nb::isinstance<nb::tuple>(nbsig)) break;
		if(nb::len(nbsig) < 1) break;
		nbsig = nbsig[0];
		if(!nb::isinstance<nb::str>(nbsig)) break;
		sig = nb::cast<nb::str>(nbsig).c_str();
		size_t paren = sig.find('(');
		if(paren != std::string::npos)
			sig.erase(0, paren);
	} while(false);
	if(sig.empty() || std::holds_alternative<const char*>(signature)) {
		sig = std::holds_alternative<const char*>(signature)
			? std::get<const char*>(signature)
			: nb::str(nb::module_::import_
				("inspect").attr("signature")(func)).c_str();
	}
	sig = (std::ostringstream() << "def " << dest_attr << sig).str();
	sig = std::visit(overloaded {
		[&](std::nullopt_t) -> std::string { return sig; },
		[&](const char*) -> std::string { return sig; },
		[&](auto func) -> std::string { return func(sig); },
	}, signature);
	const char* tname = nb::str(dest_obj.attr("__name__")).c_str();
	std::regex srcregex((std::ostringstream() << "\\b" << src_cls << "\\b").str());
	sig = std::regex_replace(sig, srcregex, tname);
	return std::make_tuple(func, doc, sig);
}

template<typename Cls, typename Evo, typename Prop>
decltype(auto) evolver_inherit(
	Cls& cls,
	Evo& evo,
	std::pair<const char*, const char*> names,
	const char* docstring,
	std::optional<const char*> signature,
	Prop prop
) {
	nb::object fn = cls.attr(names.first);
	const char* clsname = nb::str(cls.attr("__name__")).c_str();
	const char* evoname = nb::str(evo.attr("__name__")).c_str();
	std::string doc = (std::ostringstream() << docstring
		<< " of :meth:`" << clsname << "." << names.first << "`").str();
	std::regex clsregex((std::ostringstream()
		<< "\\b" << clsname << "\\b").str());
	std::string sig;
	nb::object nbsig = nb::getattr(fn, "__nb_signature__", nb::none());
	if(nb::isinstance<nb::tuple>(nbsig) && nb::len(nbsig) > 0) {
		nbsig = nbsig[0];
		if(nb::isinstance<nb::tuple>(nbsig) && nb::len(nbsig) > 0) {
			nbsig = nbsig[0];
			if(nb::isinstance<nb::str>(nbsig)) {
			}
		}
	}
	if(sig.empty()) sig = (std::ostringstream()
		<< "def " << names.second << *signature).str();
	sig = std::regex_replace(sig, clsregex, "PSequenceEvolver");
	return prop(doc.c_str(), nb::sig(sig.c_str()));
}

template<typename Cls, typename Evo, typename Prop>
decltype(auto) evolver_inherit(
	Cls& cls,
	Evo& evo,
	const char* name,
	const char* docstring,
	std::optional<const char*> signature,
	Prop prop
) {
	return evolver_inherit(cls, evo,
		std::make_pair(name, name),
		docstring, signature, prop);
}

}
}

template<>
struct std::equal_to<nanobind::object> {
	bool operator ()(const nanobind::object& x, const nanobind::object& y) const {
		int rv = PyObject_RichCompareBool(x.ptr(), y.ptr(), Py_EQ);
		if (rv == -1) [[unlikely]] nanobind::raise_python_error();
		return rv;
	}
};

template<>
struct std::less<nanobind::object> {
	bool operator ()(const nanobind::object& x, const nanobind::object& y) const {
		int rv = PyObject_RichCompareBool(x.ptr(), y.ptr(), Py_LT);
		if (rv == -1) [[unlikely]] nanobind::raise_python_error();
		return rv;
	}
};

template<>
struct std::hash<nanobind::object> {
	size_t operator ()(const nanobind::object& obj) const {
		auto hash = PyObject_Hash(obj.ptr());
		if(hash == -1) [[unlikely]]
			nanobind::raise_python_error();
		return (size_t)hash;
	}
};

