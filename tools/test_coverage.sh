#!/usr/bin/env bash

set -e

export SKBUILD_CMAKE_BUILD_TYPE=Debug
export SKBUILD_BUILD_DIR=build/coverage
export HYPOTHESIS_PROFILE=coverage

pip install --no-build-isolation --editable '.[test]'
coverage run -m pytest -vv

lcov --capture --directory $SKBUILD_BUILD_DIR --output-file $SKBUILD_BUILD_DIR/coverage.info
genhtml $SKBUILD_BUILD_DIR/coverage.info --output-directory .covreport
