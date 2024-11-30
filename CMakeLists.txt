cmake_minimum_required(VERSION 3.10) # Minimum CMake version supporting C++17

# Set project name and version
project(main VERSION 1.0 LANGUAGES CXX)

# Specify the C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Create a library for parser
add_library(parser OBJECT src/parser.cc)

# Include directories for the parser library
target_include_directories(parser PRIVATE include)

# Add the main executable and link it with parser.o
add_executable(${PROJECT_NAME} src/main.cpp)

# Include directories for the main executable
target_include_directories(${PROJECT_NAME} PRIVATE include)

# Link the main executable with the parser library object
target_link_libraries(${PROJECT_NAME} PRIVATE parser pthread)