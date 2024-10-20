cmake_minimum_required(VERSION 3.15)

project(pyrsistent-extras C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

include(CTest)
include(FetchContent)

find_package(Python 3.7
	REQUIRED COMPONENTS Interpreter Development.Module
	OPTIONAL_COMPONENTS Development.SABIModule)
find_package(nanobind CONFIG REQUIRED)

python_add_library(psequence_c MODULE
	src/pyrsistent_extras/_psequence/_c_ext.c WITH_SOABI)
set_target_properties(psequence_c
	PROPERTIES OUTPUT_NAME _c_ext)
install(TARGETS psequence_c
	LIBRARY DESTINATION pyrsistent_extras/_psequence)

nanobind_add_module(psequence_cpp
	NOMINSIZE LTO STABLE_ABI
	src/pyrsistent_extras/_psequence/_cpp_ext.cpp)
target_include_directories(psequence_cpp
	PRIVATE src/pyrsistent_extras)
set_target_properties(psequence_cpp
	PROPERTIES OUTPUT_NAME _cpp_ext)
install(TARGETS psequence_cpp
	LIBRARY DESTINATION pyrsistent_extras/_psequence)

option(BUILD_STUBS "Generate Python type stubs" ON)
if(BUILD_STUBS)
	nanobind_add_stub(
		psequence_cpp_stub
		INSTALL_TIME
		MODULE pyrsistent_extras._psequence._cpp_ext
		OUTPUT pyrsistent_extras/_psequence/_cpp_ext.pyi
		PYTHON_PATH $<TARGET_FILE_DIR:psequence_cpp>
		DEPENDS psequence_cpp)
endif()

option(BUILD_TESTS "Build with rapidcheck tests" OFF)
if(BUILD_TESTS)
	FetchContent_Declare(googletest
		GIT_REPOSITORY git@github.com:google/googletest.git
		GIT_TAG        f8d7d77c06936315286eb55f8de22cd23c188571)
	set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
	FetchContent_MakeAvailable(googletest)

	FetchContent_Declare(rapidcheck
		GIT_REPOSITORY git@github.com:emil-e/rapidcheck.git
		GIT_TAG        ff6af6fc683159deb51c543b065eba14dfcf329b)
	set(RC_ENABLE_GTEST ON CACHE BOOL "" FORCE)
	FetchContent_MakeAvailable(rapidcheck)

	find_package(Python 3.7 REQUIRED COMPONENTS Interpreter Development)
	message(Python_EXECUTABLE="${Python_EXECUTABLE}")
	execute_process(COMMAND
		"${Python_EXECUTABLE}" -m nanobind --cmake_dir
		OUTPUT_STRIP_TRAILING_WHITESPACE OUTPUT_VARIABLE NB_DIR)
	list(APPEND CMAKE_PREFIX_PATH "${NB_DIR}")
	find_package(nanobind CONFIG REQUIRED)

	add_executable(pyrsistent_tests
		tests/utility_test.cpp
		tests/psequence_test.cpp)
	target_link_libraries(pyrsistent_tests
		GTest::gtest_main
		rapidcheck_gtest)
	target_include_directories(pyrsistent_tests
		PRIVATE src/pyrsistent_extras)
endif()

option(BUILD_COVERAGE "Build with gcov support" OFF)
if(BUILD_COVERAGE)
	set(coverage_module "${CMAKE_BINARY_DIR}/cmake/CodeCoverage.cmake")
	if(NOT EXISTS ${coverage_module})
		string(CONCAT coverage_url "https://raw.githubusercontent.com/bilke/"
			"cmake-modules/1fcf7f4a2179a7b649be15473906882871ef5f0b/CodeCoverage.cmake")
		file(DOWNLOAD ${coverage_url} ${coverage_module})
	endif()
	include(${coverage_module})
	append_coverage_compiler_flags()
endif()

