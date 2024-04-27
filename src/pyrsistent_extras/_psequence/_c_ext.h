#pragma once

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <structmember.h>

#include <stdarg.h>
#include <stdbool.h>
#include <assert.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct FNode {
	size_t refs;
	size_t size;
	union {
		PyObject* value;
		struct FNode* items[3];
	};
} FNode;

typedef struct FDigit {
	size_t refs;
	size_t size;
	int  count;
	FNode* items[4];
} FDigit;

typedef struct FTree FTree;

typedef struct FDeep {
	size_t size;
	FDigit* left;
	FTree* middle;
	FDigit* right;
} FDeep;

typedef enum FTreeT {
	FEmptyT  = 0,
	FSingleT = 1,
	FDeepT   = 2
} FTreeT ;

typedef struct FTree {
	size_t refs;
	FTreeT type;
	union {
		void* empty;
		FNode* single;
		FDeep* deep;
	};
} FTree;

typedef struct FView {
	FNode* node;
	FTree* tree;
} FView;

typedef struct FSplit {
	FTree* left;
	FNode* node;
	FTree* right;
} FSplit;

typedef struct FIndex {
	size_t index;
	union {
		FNode* node;
		PyObject* value;
	};
} FIndex;

typedef struct FIndex2 {
	size_t index1;
	size_t index2;
	union {
		FNode* node;
		PyObject* value;
	};
} FIndex2;

typedef struct FInsert {
	FNode* extra;
	union {
		FNode* node;
		FDigit* digit;
		void* value;
	};
} FInsert;

typedef struct FMeld {
	bool full;
	union {
		FNode* node;
		FDigit* digit;
		FTree* tree;
		void* value;
	};
} FMeld;

typedef struct FMerge {
	union {
		FNode* left;
		FNode* node;
	};
	union {
		FNode* right;
		void* extra;
	};
} FMerge;

typedef enum FIterT {
	FTreeI  = 0,
	FDigitI = 1,
	FNodeI  = 2
} FIterT;

typedef struct FIter {
	FIterT type;
	int index;
	union {
		FTree* tree;
		FNode* node;
		FDigit* digit;
		void* value;
	};
	struct FIter* next;
} FIter;

typedef struct FMset {
	size_t index;
	size_t count;
	FIndex2* items;
} FMset;

typedef struct FSlice {
	size_t modulo;
	size_t count;
	size_t step;
	union {
		PyObject** input;
		FNode** output;
	};
} FSlice;

typedef struct PSequence {
	PyObject_HEAD
	FTree* tree;
	PyObject* weakrefs;
} PSequence;

typedef struct PSequenceIter {
	PyObject_HEAD
	Py_ssize_t index;
	bool reverse;
	PSequence* seq;
	FIter* stack;
} PSequenceIter;

typedef struct PSequenceEvolver {
	PyObject_HEAD
	PSequence* seq;
} PSequenceEvolver;

extern PyTypeObject PSequenceType;
extern PyTypeObject PSequenceIterType;
extern PyTypeObject PSequenceEvolverType;

extern PSequence* EMPTY_SEQUENCE;
extern FTree EMPTY_TREE;

void* PSequence_indexError(Py_ssize_t index);

int FNode_count(const FNode* node);

size_t FNode_depth(const FNode* node);

size_t FTree_size(const FTree* tree);

Py_ssize_t FTree_ssize(const FTree* tree);

bool FTree_empty(const FTree* tree);

bool FTree_checkIndex(const FTree* tree, Py_ssize_t* index);

int FIndex2_compare(const FIndex2* x, const FIndex2* y);

#if defined(__GNUC__) || defined(__clang__)
# define UNUSED __attribute__((unused))
#else
# define UNUSED
#endif

UNUSED void FIndent_print(int indent);

UNUSED void FNode_print(FNode* node, int indent);

UNUSED void FDigit_print(FDigit* digit, int indent);

UNUSED void FTree_print(FTree* tree, int indent);

UNUSED void FIter_print(FIter* iter);

// }}}

// {{{ debug

typedef enum FRefs {
	FTreeR = 0,
	FDigitR = 1,
	FNodeR = 2,
} FRefs;

extern long FRefs_count[3];
long FRefs_get(FRefs type);
void FRefs_inc(FRefs type);
void FRefs_dec(FRefs type);

// }}}

// {{{ ref count

void* PObj_IncRef(void* obj);

FNode* FNode_incRef(FNode* node);

FNode* FNode_incRefM(FNode* node);

void FNode_decRef(FNode* node);

void* FNode_decRefRet(FNode* node, void* ret);

FDigit* FDigit_incRef(FDigit* digit);

void FDigit_decRef(FDigit* digit);

// void* FDigit_decRefRet(FDigit* digit, void* ret);

FTree* FTree_incRef(FTree* tree);

void FTree_decRef(FTree* tree);

void* FTree_decRefRet(FTree* tree, void* ret);

FIter* FIter_incRef(FIter* iter);

FIter* FIter_decRef(FIter* iter);

// }}}

// {{{ constructor

// {{{ FNode

FNode* FNode_alloc();

FNode* FNode_make(
	const size_t size,
	const FNode* n0,
	const FNode* n1,
	const FNode* n2
);

FNode* FNode_makeS(
	const FNode* n0,
	const FNode* n1,
	const FNode* n2
);

FNode* FNode_makeNS(const int count, FNode** nodes);

FNode* FNode_makeE(const PyObject* item);

// }}}

// {{{ FDigit

FDigit* FDigit_alloc();

FDigit* FDigit_make(
	const size_t size,
	const int count,
	const FNode* n0,
	const FNode* n1,
	const FNode* n2,
	const FNode* n3
);

FDigit* FDigit_makeN(
	const size_t size,
	const int count,
	FNode** nodes
);

FDigit* FDigit_makeS(
	const int count,
	const FNode* n0,
	const FNode* n1,
	const FNode* n2,
	const FNode* n3
);

FDigit* FDigit_makeNS(const int count, FNode** nodes);

FDigit* FDigit_fromNode(const FNode* node);

FDigit* FDigit_fromMerge(FMerge merge);

// }}}

// {{{ FTree

FTree* FTree_alloc();

FTree* FEmpty_make();

FTree* FSingle_make(const FNode* node);

FDeep* FDeep_alloc();

FTree* FDeep_make(
	const size_t size,
	const FDigit* left,
	const FTree* middle,
	const FDigit* right
);

FTree* FDeep_makeS(
	const FDigit* left,
	const FTree* middle,
	const FDigit* right
);

FTree* FTree_fromDigit(const FDigit* digit);

FTree* FTree_fromMerge(FMerge merge);

// }}}

// {{{ PSequence

PSequence* PSequence_make(const FTree* tree);

void PSequence_dealloc(PSequence* self);

// }}}

// {{{ FIter

inline FIter* FIter_alloc() {
	return (FIter*)PyMem_Malloc(sizeof(FIter));
}

inline FIter* FIter_make(
	FIterT type,
	int index,
	void* item,
	FIter* next
) {
	FIter* iter = FIter_alloc();
	iter->type = type;
	iter->index = index;
	iter->value = item;
	iter->next = next;
	FIter_incRef(iter);
	return iter;
}

void FIter_dealloc(FIter* iter, bool all);

// }}}

// {{{ PSequenceIter

PSequenceIter* PSequenceIter_make(
	Py_ssize_t index,
	bool reverse,
	PSequence* seq,
	FIter* stack
);

void PSequenceIter_dealloc(PSequenceIter* self);

// }}}

// {{{ PSequenceEvolver

PSequenceEvolver* PSequenceEvolver_make(PSequence* seq);

void PSequenceEvolver_dealloc(PSequenceEvolver* self);

// }}}

// {{{ misc

inline FView FView_make(FNode* node, FTree* tree) {
	FView view = { .node=node, .tree=tree };
	return view;
}

inline FSplit FSplit_make(FTree* left, FNode* node, FTree* right) {
	FSplit split = { .left=left, .node=node, .right=right };
	return split;
}

inline FIndex FIndex_make(size_t idx, FNode* node) {
	FIndex index = { .index=idx, .node=node };
	return index;
}

inline FIndex2 FIndex2_make(size_t idx1, size_t idx2, FNode* node) {
	FIndex2 index = { .index1=idx1, .index2=idx2, .node=node };
	return index;
}

inline FInsert FInsert_make(FNode* extra, void* value) {
	FInsert insert = { .extra=extra, .value=value };
	return insert;
}

inline FMeld FMeld_make(bool full, void* value) {
	FMeld meld = { .full=full, .value=value };
	return meld;
}

inline FMerge FMerge_make(FNode* left, FNode* right) {
	FMerge merge = { .left=left, .right=right };
	return merge;
}

// }}}

// }}}

// {{{ toTree

PyObject* FNode_toTree(const FNode* node);

PyObject* FDigit_toTree(const FDigit* digit);

PyObject* FTree_toTree(const FTree* tree);

PyObject* PSequence_toTree(PSequence* self);

// }}}

// {{{ fromTuple

bool FTuple_checkType(PyObject* arg, const char* name);

FNode* FNode_fromTuple(PyObject* arg);

FDigit* FDigit_fromTuple(PyObject* arg);

FTree* FTree_fromTuple(PyObject* arg);

PSequence* PSequence_fromTuple(void* _, PyObject* arg);

// }}}

// {{{ appendLeft

FDigit* FDigit_appendLeft(FDigit* digit, FNode* node);

FTree* FTree_appendLeft(FTree* tree, FNode* node);

PSequence* PSequence_appendLeft(PSequence* self, PyObject* value);

// }}}

// {{{ appendRight

FDigit* FDigit_appendRight(FDigit* digit, FNode* node);

FTree* FTree_appendRight(FTree* tree, FNode* node);

PSequence* PSequence_appendRight(PSequence* self, PyObject* value);

// }}}

// {{{ viewLeft

FTree* FTree_pullLeft(FTree* middle, FDigit* right);

FView FTree_viewLeft(FTree* tree);

PyObject* PSequence_viewLeft(PSequence* self);

// }}}

// {{{ viewRight

FTree* FTree_pullRight(FDigit* left, FTree* middle);

FView FTree_viewRight(FTree* tree);

PyObject* PSequence_viewRight(PSequence* self);

// }}}

// {{{ peek

PyObject* FTree_peekLeft(FTree* tree);

PyObject* PSequence_peekLeft(PSequence* self, void* UNUSED _ignore);

PyObject* FTree_peekRight(FTree* tree);

PyObject* PSequence_peekRight(PSequence* self, void* UNUSED _ignore);

// }}}

// {{{ fromIterable

FTree* FTree_fromNodes(size_t size, size_t count, FNode** nodes);

PSequence* PSequence_fromIterable(PyObject* sequence);

// }}}

// {{{ toTuple

size_t FNode_toTuple(FNode* node, PyObject* tuple, size_t index);

size_t FDigit_toTuple(FDigit* digit, PyObject* tuple, size_t index);

size_t FTree_toTuple(FTree* tree, PyObject* tuple, size_t index);

PyObject* PSequence_toTuple(PSequence* self);

// }}}

// {{{ toList

size_t FNode_toList(FNode* node, PyObject* list, size_t index);

size_t FDigit_toList(FDigit* digit, PyObject* list, size_t index);

size_t FTree_toList(FTree* tree, PyObject* list, size_t index);

PyObject* PSequence_toList(PSequence* self);

// }}}

// {{{ getItem

void* FNode_getItem(const FNode* node, size_t index);

void* FDigit_getItem(const FDigit* digit, size_t index);

void* FTree_getItem(const FTree* tree, size_t index);

PyObject* PSequence_getItem(const PSequence* self, Py_ssize_t index);

PyObject* PSequence_getItemS(const PSequence* self, Py_ssize_t index);

// }}}

// {{{ traverse

int FNode_traverse(FNode* node, visitproc visit, void* arg);

int FDigit_traverse(FDigit* digit, visitproc visit, void* arg);

int FTree_traverse(FTree* tree, visitproc visit, void* arg);

int PSequence_traverse(PSequence* self, visitproc visit, void* arg);

// }}}

// {{{ concat

FTree* FDeep_extend(FDeep* xs, FDeep* ys);

FTree* FTree_extend(FTree* xs, FTree* ys);

PSequence* PSequence_extendRight(PSequence* self, PyObject* arg);

PSequence* PSequence_extendLeft(PSequence* self, PyObject* arg);

// }}}

// {{{ repeat

PSequence* PSequence_repeat(PSequence* self, Py_ssize_t count);

// }}}

// {{{ setItem

FNode* FNode_setItem(
	const FNode* node,
	size_t index,
	const PyObject* value
);

FDigit* FDigit_setItem(
	const FDigit* digit,
	size_t index,
	const PyObject* value
);

FTree* FTree_setItem(
	const FTree* tree,
	size_t index,
	const PyObject* value
);

PSequence* PSequence_setItem(
	PSequence* self,
	Py_ssize_t index,
	PyObject* value
);

PSequence* PSequence_setItemS(
	PSequence* self,
	Py_ssize_t index,
	PyObject* value
);

// static PSequence* PSequence_setItemN(
	// PSequence* self,
	// PyObject* args
// );

// }}}

// {{{ msetItem

FNode* FNode_msetItem(FNode* node, FMset* mset);

FDigit* FDigit_msetItem(FDigit* digit, FMset* mset);

FTree* FTree_msetItem(FTree* tree, FMset* mset);

PSequence* PSequence_msetItemN(PSequence* self, PyObject* args);

// }}}

// {{{ insertItem

FInsert FNode_insertItem(FNode* node, size_t index, PyObject* item);

FInsert FDigit_insertLeft(FDigit* digit, size_t index, PyObject* item);

FInsert FDigit_insertRight(FDigit* digit, size_t index, PyObject* item);

FTree* FTree_insertItem(FTree* tree, size_t index, PyObject* item);

PSequence* PSequence_insertItemN(PSequence* self, PyObject* args);

// }}}

// {{{ merge/meld

FMerge FNode_mergeLeft(FNode* left, FNode* node);

FMerge FNode_mergeRight(FNode* node, FNode* right);

FDigit* FDigit_mergeLeft(FNode* left, FNode* node);

FDigit* FDigit_mergeRight(FNode* node, FNode* right);

FMeld FNode_meldLeft(FNode* extra, FMerge merge);

FMeld FNode_meldRight(FMerge merge, FNode* extra);

// }}}

// {{{ deleteItem

FMeld FNode_deleteItem(FNode* node, size_t index);

FMeld FDigit_deleteItem(FDigit* digit, size_t index);

FMeld FTree_deleteItemLeft(FTree* tree, size_t index);

FMeld FTree_deleteItemRight(FTree* tree, size_t index);

FMeld FTree_deleteItemMiddle(FTree* tree, size_t index);

FMeld FTree_deleteItem(FTree* tree, size_t index);

PSequence* PSequence_deleteItem(PSequence* self, Py_ssize_t index);

PSequence* PSequence_deleteItemS(PSequence* self, Py_ssize_t index);

// }}}

// {{{ contains

int FNode_contains(FNode* node, PyObject* arg);

int FDigit_contains(FDigit* digit, PyObject* arg);

int FTree_contains(FTree* tree, PyObject* arg);

int PSequence_contains(PSequence* self, PyObject* arg);

// }}}

// {{{ indexItem

Py_ssize_t FNode_indexItem(FNode* node, PyObject* arg);

Py_ssize_t FDigit_indexItem(FDigit* digit, PyObject* arg);

Py_ssize_t FTree_indexItem(FTree* tree, PyObject* arg);

PyObject* PSequence_indexItem(PSequence* self, PyObject* args);

// }}}

// {{{ removeItem

PSequence* PSequence_removeItemN(PSequence* self, PyObject* arg);

// }}}

// {{{ countItem

Py_ssize_t FNode_countItem(FNode* node, PyObject* arg);

Py_ssize_t FDigit_countItem(FDigit* digit, PyObject* arg);

Py_ssize_t FTree_countItem(FTree* tree, PyObject* arg);

PyObject* PSequence_countItem(PSequence* self, PyObject* arg);

// }}}

// {{{ splitView

FSplit FDeep_splitViewLeft(FDeep* deep, size_t index);

FSplit FDeep_splitViewRight(FDeep* deep, size_t index);

FSplit FDeep_splitViewMiddle(FDeep* deep, size_t index);

FSplit FTree_splitView(FTree* tree, size_t index);

// splitAt has to split nodes anyway, so just reuse splitView
PyObject* PSequence_splitAt(PSequence* self, PyObject* arg);

PyObject* PSequence_view(PSequence* self, PyObject* args);

// }}}

// {{{ chunksOf

PSequence* PSequence_chunksOf(PSequence* self, Py_ssize_t chunk);

PSequence* PSequence_chunksOfN(PSequence* self, PyObject* arg);

// }}}

// {{{ takeLeft

FView FDeep_takeLeftLeft(FDeep* deep, size_t index);

FView FDeep_takeLeftRight(FDeep* deep, size_t index);

FView FDeep_takeLeftMiddle(FDeep* deep, size_t index);

FView FTree_takeLeft(FTree* tree, size_t index);

PSequence* PSequence_takeLeft(PSequence* self, Py_ssize_t index);

// }}}

// {{{ takeRight

FView FDeep_takeRightLeft(FDeep* deep, size_t index);

FView FDeep_takeRightRight(FDeep* deep, size_t index);

FView FDeep_takeRightMiddle(FDeep* deep, size_t index);

FView FTree_takeRight(FTree* tree, size_t index);

PSequence* PSequence_takeRight(PSequence* self, Py_ssize_t index);

// }}}

// {{{ repr

PyObject* PSequence_repr(PSequence* self);

// }}}

// {{{ compare

PyObject* PObj_compare(PyObject* x, PyObject* y, int op);

PyObject* PIter_compare(PyObject* xs, PyObject* ys, int op);

PyObject* PSequence_compare(PyObject* xs, PyObject* ys, int op);

// }}}

// {{{ hash


Py_uhash_t FNode_hash(FNode* node, Py_uhash_t acc);

Py_uhash_t FDigit_hash(FDigit* digit, Py_uhash_t acc);

Py_uhash_t FTree_hash(FTree* tree, Py_uhash_t acc);

Py_hash_t PSequence_hash(PSequence* self);

// }}}

// {{{ reverse

FNode* FNode_reverse(FNode* node);

FDigit* FDigit_reverse(FDigit* digit);

FTree* FTree_reverse(FTree* tree);

PSequence* PSequence_reverse(PSequence* self);

// }}}

// {{{ getSlice

bool FNode_getSlice(FNode* node, FSlice* slice);

bool FDigit_getSlice(FDigit* digit, FSlice* slice);

bool FTree_getSlice(FTree* tree, FSlice* slice);

PSequence* PSequence_getSlice(PSequence* self, PyObject* slice);

PyObject* PSequence_subscr(PSequence* self, PyObject* arg);

// }}}

// {{{ deleteSlice

PSequence* PSequence_deleteSlice(
	PSequence* self,
	PyObject* slice
);

PSequence* PSequence_deleteSubscr(PSequence* self, PyObject* index);

// }}}

// {{{ setSlice

FNode* FNode_setSlice(FNode* node, FSlice* slice);

FDigit* FDigit_setSlice(FDigit* digit, FSlice* slice);

FTree* FTree_setSlice(FTree* tree, FSlice* slice);

PSequence* PSequence_setSlice(
	PSequence* self,
	PyObject* slice,
	PyObject* value
);

PSequence* PSequence_setSubscr(
	PSequence* self,
	PyObject* index,
	PyObject* value
);

PSequence* PSequence_setSubscrN(PSequence* self, PyObject* args);

// }}}

// {{{ reduce

extern PyObject* PSEQUENCE_FUNCTION;

PyObject* PSequence_reduce(PSequence* self);

// }}}

// {{{ transform

extern PyObject* TRANSFORM_FUNCTION;

PSequence* PSequence_transform(PSequence* self, PyObject* args);

// }}}

// {{{ sort

PSequence* PSequence_sort(
	PSequence*  self,
	PyObject* args,
	PyObject* kwargs
);

// }}}

// {{{ PSequence

Py_ssize_t PSequence_length(PSequence* self);

PyObject* PSequence_refcount(PyObject* self, PyObject* args);

PSequence* PSequence_fromItems(PyObject* self, PyObject* args);

extern PySequenceMethods PSequence_asSequence;

extern PyMappingMethods PSequence_asMapping;

extern PyGetSetDef PSequence_getSet[];

extern PyMethodDef PSequence_methods[];

extern PyTypeObject PSequenceType;

// }}}

// {{{ iter next

FIter* FIter_pushStack(
	FIter* iter,
	FIterT type,
	int index,
	void* item
);

FIter* FIter_swapStack(
	FIter* iter,
	FIterT type,
	int index,
	void* item
);

FIter* FIter_popStack(FIter* iter);

FIter* FIter_nextStack(FIter* iter);

FIter* FIter_prevStack(FIter* iter);

PyObject* PSequenceIter_next(PSequenceIter* self);

// }}}

// {{{ PSequenceIter

PSequenceIter* PSequence_iter(PSequence* self);

PSequenceIter* PSequence_reversed(PSequence* self);

PyObject* PSequenceIter_lenHint(PSequenceIter* self);

int PSequenceIter_traverse(
	PSequenceIter *self,
	visitproc visit,
	void* arg
);

extern PyMethodDef PSequenceIter_methods[];

extern PyTypeObject PSequenceIterType;

// }}}

// {{{ evolver inherit

#define inherit_query0(name, rettype) \
	rettype PSequenceEvolver_##name \
	(PSequenceEvolver* self);
#define inherit_query1(name, rettype, type1) \
	rettype PSequenceEvolver_##name \
	(PSequenceEvolver* self, type1 arg1);
#define inherit_query2(name, rettype, type1, type2) \
	rettype PSequenceEvolver_##name \
	(PSequenceEvolver* self, type1 arg1, type2 arg2);

#define inherit_method0(name) \
	PSequenceEvolver* PSequenceEvolver_##name \
	(PSequenceEvolver* self);
#define inherit_method1(name, type1) \
	PSequenceEvolver* PSequenceEvolver_##name \
	(PSequenceEvolver* self, type1 arg1);
#define inherit_method2(name, type1, type2) \
	PSequenceEvolver* PSequenceEvolver_##name \
	(PSequenceEvolver* self, type1 arg1, type2 arg2);
#define inherit_methodN(name) \
	PSequenceEvolver* PSequenceEvolver_##name \
	(PSequenceEvolver* self, PyObject* args);

#define inherit_new1(name, type1) \
	PSequenceEvolver* PSequenceEvolver_##name##New \
	(PSequenceEvolver* self, type1 arg1);

inherit_query0(length, Py_ssize_t)
inherit_method1(repeat, Py_ssize_t)
inherit_new1(repeat, Py_ssize_t)

inherit_query1(getItem, PyObject*, Py_ssize_t)
inherit_query1(subscr, PyObject*, PyObject*)

inherit_methodN(appendRight)
inherit_methodN(appendLeft)
inherit_query1(peekRight, PyObject*, void*)
inherit_query1(peekLeft, PyObject*, void*)

inherit_query0(viewRight, PyObject*)
inherit_query0(viewLeft, PyObject*)
inherit_query1(view, PyObject*, PyObject*)

inherit_query1(splitAt, PyObject*, PyObject*)
inherit_query1(chunksOfN, PSequence*, PyObject*)

inherit_methodN(extendLeft)
inherit_methodN(extendRight)
inherit_new1(extendRight, PyObject*)

inherit_method0(reverse)
inherit_query0(reversed, PSequenceIter*)

inherit_methodN(setSubscrN)
inherit_methodN(msetItemN)
inherit_methodN(insertItemN)
inherit_methodN(deleteSubscr)
inherit_methodN(removeItemN)

inherit_query1(indexItem, PyObject*, PyObject*)
inherit_query1(countItem, PyObject*, PyObject*)
inherit_query1(contains, int, PyObject*)

inherit_query0(toList, PyObject*)
inherit_query0(toTuple, PyObject*)
inherit_query0(toTree, PyObject*)

inherit_method2(sort, PyObject*, PyObject*)
inherit_query0(reduce, PyObject*)
inherit_query2(traverse, int, visitproc, void*)
inherit_query0(iter, PSequenceIter*)
inherit_methodN(transform)

#undef inherit_query0
#undef inherit_query1
#undef inherit_query2
#undef inherit_method0
#undef inherit_method1
#undef inherit_method2
#undef inherit_methodN
#undef inherit_new1

// }}}

// {{{ pop

PyObject* PSequenceEvolver_popLeft(PSequenceEvolver* self);

PyObject* PSequenceEvolver_popRight(PSequenceEvolver* self);

PyObject* PSequenceEvolver_pop(PSequenceEvolver* self, PyObject* args);

// }}}

// {{{ PSequenceEvolver

PSequenceEvolver* PSequence_evolver(PSequence* self);

PyObject* PSequenceEvolver_repr(PSequenceEvolver* self);

PSequence* PSequenceEvolver_persistent(PSequenceEvolver* self);

PSequenceEvolver* PSequenceEvolver_copy(PSequenceEvolver* self);

PSequenceEvolver* PSequenceEvolver_clear(PSequenceEvolver* self);

int PSequenceEvolver_assItem(
	PSequenceEvolver* self,
	Py_ssize_t index,
	PyObject* value
);

int PSequenceEvolver_assSubscr(
	PSequenceEvolver* self,
	PyObject* index,
	PyObject* value
);

extern PyGetSetDef PSequenceEvolver_getSet[];

extern PyMethodDef PSequenceEvolver_methods[];

extern PySequenceMethods PSequenceEvolver_asSequence;

extern PyMappingMethods PSequenceEvolver_asMapping;

extern PyTypeObject PSequenceEvolverType;

// }}}

// {{{ module def

extern struct PyModuleDef moduleDef;

void* PObj_getDoc(const char* name, PyObject* base);

bool pyrsistent_psequence_inheritDocs();

PyMODINIT_FUNC PyInit__c_ext();

// }}}

#ifdef __cplusplus
}
#endif

// vim: set foldmethod=marker foldlevel=0 nocindent:
