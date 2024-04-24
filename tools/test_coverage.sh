#!/usr/bin/env bash

set -e

export SKBUILD_CMAKE_BUILD_TYPE=Debug
export SKBUILD_BUILD_DIR=build/coverage
export HYPOTHESIS_PROFILE=${HYPOTHESIS_PROFILE:-coverage}

pip install --no-build-isolation --editable '.[test,coverage]'
coverage run -m pytest -vv

coverage html --directory .py-coverage

lcov --capture --directory $SKBUILD_BUILD_DIR --output-file $SKBUILD_BUILD_DIR/coverage.info
genhtml $SKBUILD_BUILD_DIR/coverage.info --output-directory .cpp-coverage

cpp-coveralls --root $SKBUILD_BUILD_DIR --dump $SKBUILD_BUILD_DIR/cpp-coveralls.json
python3 -m coveralls --merge $SKBUILD_BUILD_DIR/cpp-coveralls.json --output coveralls.json