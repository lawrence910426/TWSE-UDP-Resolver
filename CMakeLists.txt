cmake_minimum_required(VERSION 3.4...3.18)

# Specify the C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Set project name and version
project(twse_udp_resolver VERSION 1.0 LANGUAGES CXX)

# 1. Create an object library for parser
add_library(parser_obj OBJECT src/parser.cc)
target_include_directories(parser_obj PRIVATE include)
set_target_properties(parser_obj PROPERTIES POSITION_INDEPENDENT_CODE ON)

# 2. Create a static library (parser.a) from the object library
add_library(parser_static STATIC $<TARGET_OBJECTS:parser_obj>)
target_include_directories(parser_static PRIVATE include)
set_target_properties(parser_static PROPERTIES POSITION_INDEPENDENT_CODE ON)

# Add the pybind11 subdirectory and create the pybind11 module
add_subdirectory(extern/pybind11)
pybind11_add_module(twse_udp_resolver src/pybind.cpp)

# Define the VERSION_INFO macro for the pybind11 module
target_compile_definitions(twse_udp_resolver
                           PRIVATE VERSION_INFO=${VERSION_INFO})

# Include directories for the pybind11 module
target_include_directories(twse_udp_resolver PRIVATE include)

# Link the pybind11 module with the parser static library and pthread
target_link_libraries(twse_udp_resolver PRIVATE parser_static pthread)

# Add the cpp executable
add_executable(${PROJECT_NAME}_cpp_interface example/twse_udp_resolver_cpp_interface.cpp)

# Include directories for the main executable
target_include_directories(${PROJECT_NAME}_cpp_interface PRIVATE include)

# Link the cpp executable with the parser static library and pthread
target_link_libraries(${PROJECT_NAME}_cpp_interface PRIVATE parser_static pthread)

# Set the runtime output directory for the executable
set_target_properties(${PROJECT_NAME}_cpp_interface PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/build"
)

# ----------------------------------------------------------------------------
# After building, copy the parser object file and static library to ./build
# ----------------------------------------------------------------------------

# The location of the object file may vary by generator and platform.
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    set(PARSER_OBJ ${CMAKE_BINARY_DIR}/CMakeFiles/parser_obj.dir/src/parser.cc.o)
    set(PARSER_A ${CMAKE_BINARY_DIR}/libparser_static.a)
elseif(MSVC)
    set(PARSER_OBJ ${CMAKE_BINARY_DIR}/CMakeFiles/parser_obj.dir/src/parser.cc.obj)
    set(PARSER_A ${CMAKE_BINARY_DIR}/parser_static.lib)
endif()

