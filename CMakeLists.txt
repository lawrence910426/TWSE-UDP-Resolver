cmake_minimum_required(VERSION 3.4...3.18)

# Specify the C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Set project name and version
project(twse_udp_resolver VERSION 1.0 LANGUAGES CXX)

# Create a library for parser
add_library(parser OBJECT src/parser.cc)

# Include directories for the parser library
target_include_directories(parser PRIVATE include)

# Enable position-independent code for the parser library
set_target_properties(parser PROPERTIES POSITION_INDEPENDENT_CODE ON)

# Add the pybind11 subdirectory and create the pybind11 module
add_subdirectory(extern/pybind11)
pybind11_add_module(twse_udp_resolver src/pybind.cpp)

# Define the VERSION_INFO macro for the pybind11 module
target_compile_definitions(twse_udp_resolver
                           PRIVATE VERSION_INFO=${VERSION_INFO})

# Include directories for the pybind11 module
target_include_directories(twse_udp_resolver PRIVATE include)

# Link the pybind11 module with the parser library
target_link_libraries(twse_udp_resolver PRIVATE parser pthread)

# Add the cpp executable
add_executable(${PROJECT_NAME}_twse_udp_resolver_cpp_interface example/twse_udp_resolver_cpp_interface.cpp)

# Include directories for the main executable
target_include_directories(${PROJECT_NAME}_twse_udp_resolver_cpp_interface PRIVATE include)

# Link the cpp executable with the parser library and pthread
target_link_libraries(${PROJECT_NAME}_twse_udp_resolver_cpp_interface PRIVATE parser pthread)

# Set the runtime output directory for the executable
set_target_properties(${PROJECT_NAME}_twse_udp_resolver_cpp_interface PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/build"
)
