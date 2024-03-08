cmake_minimum_required(VERSION 3.15)

project(pyrsistent-extras C CXX)

include(CTest)
include(FetchContent)

set(CMAKE_CXX_STANDARD 17)

find_package(Python 3.7
	REQUIRED COMPONENTS Interpreter Development.Module
	OPTIONAL_COMPONENTS Development.SABIModule)
find_package(nanobind CONFIG REQUIRED)

python_add_library(_c_ext MODULE
	pyrsistent_extras/_psequence/_c_ext.c WITH_SOABI)
install(TARGETS _c_ext
	LIBRARY DESTINATION pyrsistent_extras/_psequence)

