cmake_minimum_required(VERSION 3.10) # Minimum CMake version supporting C++17

# Set project name and version
project(MyProject VERSION 1.0 LANGUAGES CXX)

# Specify the C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Add the executable (update the source files as needed)
add_executable(${PROJECT_NAME} src/main.cpp)

# Include directories (if you have header files in "include/")
target_include_directories(${PROJECT_NAME} PRIVATE include)
