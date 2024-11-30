# Use an official Ubuntu base image
FROM ubuntu:20.04

# Set environment variables to avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary packages
RUN apt-get update && apt-get install -y \
    build-essential \       
    cmake \                 
    python3 \              
    python3-pip && \        
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy source files and CMakeLists.txt into the container
COPY ./src ./src
COPY ./include ./include
COPY ./CMakeLists.txt .
COPY ./test ./test

# Create a build directory and build the C++ project
RUN mkdir build && cd build && cmake .. && cmake --build .

# Set the default command to run the built C++ executable
CMD ["./build/main"]
