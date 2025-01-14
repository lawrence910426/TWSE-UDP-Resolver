#ifndef LOGGER_H
#define LOGGER_H

#include <fstream>
#include <string>
#include <chrono>
#include <iomanip>
#include <sstream>
#include <iostream>
#include <sys/stat.h>   // for mkdir
#include <errno.h>      // for errno
#include <cstring>      // for strerror

class Logger {
public:
    static Logger& getInstance() {
        static Logger instance;
        return instance;
    }

    void init(const std::string& filename) {
        // Create logger directory if it doesn't exist
        if (mkdir("logger", 0777) == -1) {
            if (errno != EEXIST) {
                std::cerr << "Error creating logger directory: " << strerror(errno) << std::endl;
                return;
            }
        }

        // Open log file in logger directory
        std::string filepath = "logger/" + filename;
        if (!log_file.is_open()) {
            log_file.open(filepath, std::ios::out | std::ios::app);
            if (!log_file.is_open()) {
                std::cerr << "Error opening log file: " << filepath << std::endl;
            } else {
                log("Logger initialized: " + filepath);
            }
        }
    }

    void log(const std::string& message, bool error = false) {
        if (!log_file.is_open()) return;

        auto now = std::chrono::system_clock::now();
        auto now_time_t = std::chrono::system_clock::to_time_t(now);
        auto now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            now.time_since_epoch()).count() % 1000000000;

        char timestamp[32];
        std::tm tm_buf;
        localtime_r(&now_time_t, &tm_buf);
        strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", &tm_buf);

        log_file << "[" << timestamp << "." 
                << std::setfill('0') << std::setw(9) << now_ns << "] "
                << (error ? "ERROR: " : "INFO: ") 
                << message << std::endl;

        if (error) {
            std::cerr << message << std::endl;
        }
    }

    ~Logger() {
        if (log_file.is_open()) {
            log_file.close();
        }
    }

private:
    Logger() = default;
    std::ofstream log_file;
};

#endif // LOGGER_H 