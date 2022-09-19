SPHINXOPTS  ?=
SPHINXBUILD ?= sphinx-build
SOURCEDIR    = source
BUILDDIR     = build

.PHONY: default
default: help

.PHONY: help
help:
	$(SPHINXBUILD) -b help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

.PHONY: Makefile
%: Makefile
	$(SPHINXBUILD) -b $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

