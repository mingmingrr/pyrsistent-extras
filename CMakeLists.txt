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

python_add_library(_c_ext MODULE
	src/pyrsistent_extras/_psequence/_c_ext.c WITH_SOABI)
install(TARGETS _c_ext
	LIBRARY DESTINATION pyrsistent_extras/_psequence)

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

