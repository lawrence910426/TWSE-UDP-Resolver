# Use an official Ubuntu base image
FROM ubuntu:24.04

# Set environment variables to avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary packages
# python3-venv is added to support standard environment creation
RUN apt-get update && apt-get install -y \
    build-essential \       
    cmake \                 
    python3 \    
    python3-dev \          
    python3-pip \
    python3-venv \
    netcat-openbsd && \        
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy source files and CMakeLists.txt into the container
COPY ./src ./src
COPY ./include ./include
COPY ./example ./example
COPY ./extern ./extern
COPY ./CMakeLists.txt .
COPY ./test ./test
COPY ./setup.py .

# Install uv (using --break-system-packages here is safe as we only use it to install the tool)
RUN pip install uv --break-system-packages

# Create a virtual environment and update the PATH so all subsequent 
# commands (like python or pip) use this environment automatically.
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create a build directory and build the C++ project
# RUN mkdir build && cd build && cmake .. && cmake --build .
# RUN pip install .

# Install the current project into the virtual environment
RUN uv pip install .