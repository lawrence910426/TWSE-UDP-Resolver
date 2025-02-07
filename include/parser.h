#ifndef PARSER_H
#define PARSER_H

#include <thread>
#include <functional>
#include <string>
#include <vector>
#include <atomic>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <cstdint>
#include <fstream>
#include "logger.h"

// Callback type for handling recorded packets
using PacketCallback = std::function<void(const struct Packet&)>;

// Packet structure based on specifications
struct Packet {
    // ESC-CODE
    uint8_t esc_code; // ASCII 27 (0x1B)

    // HEADER
    uint16_t message_length;      // 2 bytes, PACK BCD
    uint8_t business_type;        // 1 byte, PACK BCD "01"
    uint8_t format_code;          // 1 byte, PACK BCD "06"
    uint8_t format_version;       // 1 byte, PACK BCD "04"
    uint32_t transmission_number; // 4 bytes, PACK BCD

    // BODY
    char stock_code[6];           // 6 bytes, ASCII
    uint64_t match_time;          // 6 bytes, PACK BCD
    uint8_t display_item;         // 1 byte, BIT MAP
    uint8_t limit_up_limit_down;        // 1 byte, BIT MAP
    uint8_t status_note;          // 1 byte, BIT MAP
    uint32_t cumulative_volume;   // 4 bytes, PACK BCD
    std::vector<uint32_t> prices; // Prices (each 5 bytes, PACK BCD)
    std::vector<uint32_t> quantities; // Quantities (each 4 bytes, PACK BCD)

    // CHECKSUM
    uint8_t checksum; // 1 byte, XOR of all bytes from ESC-CODE to the byte before TERMINAL-CODE

    // TERMINAL-CODE
    uint16_t terminal_code; // 2 bytes, HEXACODE 0x0D 0x0A
};

class Parser {
public:
    Parser();
    ~Parser();

    // Start the UDP stream parsing loop in a new thread
    void start_loop(int port, const PacketCallback& callback);

    // Stop the parsing loop and clean up resources
    void end_loop();

    // Configure multicast settings
    void set_multicast(const std::string& group, const std::string& iface);

    // Configure stock filter
    void set_stock_filter(const std::string& stock);

private:
    // Parsing automaton logic
    void parse_packet(const std::vector<uint8_t>& raw_packet);

    // Packet reading thread logic
    void receive_loop(int port);

    // Helper methods for parsing
    bool parse_header(const std::vector<uint8_t>& raw_packet, Packet& packet, size_t& offset);
    bool parse_body(const std::vector<uint8_t>& raw_packet, Packet& packet, size_t& offset);
    bool validate_checksum(const std::vector<uint8_t>& raw_packet, const Packet& packet);
    bool validate_terminal_code(const std::vector<uint8_t>& raw_packet, const Packet& packet);

    // Determine checksum position dynamically based on packet length
    size_t calculate_checksum_position(size_t packet_length) const;

    // Network-related members
    std::thread recv_thread;
    std::atomic<bool> running;

    // Callback for handling valid packets
    PacketCallback packet_callback;

    // Synchronization for thread-safe packet handling
    std::mutex packet_mutex;
    std::condition_variable packet_cv;
    std::queue<std::vector<uint8_t>> packet_queue;

    // Constants for parsing
    static constexpr uint8_t ESC_CODE = 0x1B;
    static constexpr size_t TERMINAL_CODE_SIZE = 2;
    static constexpr size_t HEADER_LENGTH = 9;

    // Multicast settings
    std::string multicast_group;
    std::string interface_ip;
    bool use_multicast;
    
    int sockfd = -1;  // 初始化為 -1
    
    void log_message(const std::string& message, bool error = false);
};

#endif // PARSER_H
