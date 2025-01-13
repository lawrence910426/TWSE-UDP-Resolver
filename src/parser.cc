#include "parser.h"
#include <iostream>
#include <cstring>
#include <arpa/inet.h>
#include <unistd.h>

// Constructor
Parser::Parser() : running(false), use_multicast(false) {}

// Destructor
Parser::~Parser() {
    end_loop();
}

// Start the UDP stream parsing loop in a new thread
void Parser::start_loop(int port, const PacketCallback& callback) {
    if (running) {
        std::cerr << "Parser is already running!" << std::endl;
        return;
    }

    running = true;
    packet_callback = callback;
    recv_thread = std::thread(&Parser::receive_loop, this, port);
}

// Stop the parsing loop and clean up resources
void Parser::end_loop() {
    if (!running) return;

    running = false;
    if (recv_thread.joinable()) {
        recv_thread.join();
    }
}

// Receive UDP packets and feed them into the parser
void Parser::receive_loop(int port) {
    int sockfd;
    sockaddr_in server_addr{};
    char buffer[1500]; // Maximum UDP packet size

    // Create a UDP socket
    if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        std::cerr << "Socket creation failed: " << strerror(errno) << std::endl;
        return;
    }

    // Enable SO_REUSEADDR
    int reuse = 1;
    if (setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse)) < 0) {
        std::cerr << "Failed to set SO_REUSEADDR: " << strerror(errno) << std::endl;
        close(sockfd);
        return;
    }

    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    
    // Bind to the port
    if (bind(sockfd, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        std::cerr << "Bind failed: " << strerror(errno) << std::endl;
        close(sockfd);
        return;
    }

    if (use_multicast) {
        // Set up multicast request
        struct ip_mreq mreq{};
        mreq.imr_multiaddr.s_addr = inet_addr(multicast_group.c_str());
        mreq.imr_interface.s_addr = inet_addr(interface_ip.c_str());

        std::cout << "Attempting to join multicast group " << multicast_group 
                 << " on interface " << interface_ip << std::endl;

        if (setsockopt(sockfd, IPPROTO_IP, IP_ADD_MEMBERSHIP, &mreq, sizeof(mreq)) < 0) {
            std::cerr << "Failed to join multicast group: " << strerror(errno) << std::endl;
            close(sockfd);
            return;
        }

        // Set multicast interface
        struct in_addr local_interface{};
        local_interface.s_addr = inet_addr(interface_ip.c_str());
        if (setsockopt(sockfd, IPPROTO_IP, IP_MULTICAST_IF, &local_interface, sizeof(local_interface)) < 0) {
            std::cerr << "Failed to set multicast interface: " << strerror(errno) << std::endl;
            close(sockfd);
            return;
        }
    }

    std::cout << "Successfully initialized socket on port " << port;
    if (use_multicast) {
        std::cout << " (multicast group: " << multicast_group 
                 << ", interface: " << interface_ip << ")";
    }
    std::cout << std::endl;

    while (running) {
        ssize_t len = recv(sockfd, buffer, sizeof(buffer), 0);
        if (len > 0) {
            std::vector<uint8_t> raw_packet(buffer, buffer + len);
            
            // Split packets by 0D 0A delimiter
            size_t start_pos = 0;
            for (size_t i = 0; i < raw_packet.size() - 1; i++) {
                if (raw_packet[i] == 0x0D && raw_packet[i + 1] == 0x0A) {
                    // Found a complete packet
                    size_t packet_length = i + 2 - start_pos;  // Including 0D 0A
                    std::vector<uint8_t> single_packet(raw_packet.begin() + start_pos, 
                                                     raw_packet.begin() + start_pos + packet_length);
                    
                    // Process single packet
                    parse_packet(single_packet);
                    
                    // Update start position for next packet
                    start_pos = i + 2;
                }
            }
        } else if (len < 0) {
            std::cerr << "Error receiving data: " << strerror(errno) << std::endl;
        }
    }

    close(sockfd);
}

// Add a new method to configure multicast
void Parser::set_multicast(const std::string& group, const std::string& iface) {
    multicast_group = group;
    interface_ip = iface;
    use_multicast = true;
}

// Parse the received packet
void Parser::parse_packet(const std::vector<uint8_t>& raw_packet) {
    if (raw_packet.empty() || raw_packet[0] != ESC_CODE) {
        std::cout << "Invalid packet" << std::endl;
        return; // Ignore packets that don't start with ESC-CODE
    }

    Packet packet{};
    size_t offset = 1; // Start parsing after ESC-CODE

    // Parse the header
    if (!parse_header(raw_packet, packet, offset)) {
        std::cout << "Invalid header" << std::endl;
        return; // Ignore invalid packets
    }

    // Parse the body
    if (!parse_body(raw_packet, packet, offset)) {
        std::cout << "Invalid body" << std::endl;
        return; // Ignore invalid packets
    }

    // Validate the checksum
    if (!validate_checksum(raw_packet, packet)) {
        std::cout << "Invalid checksum" << std::endl;
        return; // Ignore invalid packets
    }

    // Validate the terminal code
    if (!validate_terminal_code(raw_packet, packet)) {
        std::cout << "Invalid terminal code" << std::endl;
        return; // Ignore invalid packets
    }

    // If all checks pass, invoke the callback
    if (packet_callback) {
        std::cout << "Received " << raw_packet.size() << " bytes" << std::endl;
        packet_callback(packet);
    }
}

// Parse the header
bool Parser::parse_header(const std::vector<uint8_t>& raw_packet, Packet& packet, size_t& offset) {
    if (offset + HEADER_LENGTH > raw_packet.size()) return false; // Ensure header length is valid

    packet.message_length = (raw_packet[offset] << 8) | raw_packet[offset + 1];
    packet.business_type = raw_packet[offset + 2];
    packet.format_code = raw_packet[offset + 3];
    packet.format_version = raw_packet[offset + 4];
    packet.transmission_number = (raw_packet[offset + 5] << 24) |
                                 (raw_packet[offset + 6] << 16) |
                                 (raw_packet[offset + 7] << 8) |
                                 raw_packet[offset + 8];
    offset += HEADER_LENGTH;

    if (packet.format_code != 0x06) return false;
    
    return true;
}

// Parse the body
bool Parser::parse_body(const std::vector<uint8_t>& raw_packet, Packet& packet, size_t& offset) {
    if (offset + 19 > raw_packet.size()) return false; // Minimum body size is 19 bytes

    std::memcpy(packet.stock_code, &raw_packet[offset], 6);
    offset += 6;

    packet.match_time = 0;
    for (size_t i = 0; i < 6; ++i) {
        packet.match_time = (packet.match_time << 8) | raw_packet[offset++];
    }

    packet.display_item = raw_packet[offset++];
    packet.limit_up_limit_down = raw_packet[offset++];
    packet.status_note = raw_packet[offset++];
    packet.cumulative_volume = (raw_packet[offset] << 24) |
                                (raw_packet[offset + 1] << 16) |
                                (raw_packet[offset + 2] << 8) |
                                raw_packet[offset + 3];
    offset += 4;

    // Parse dynamic prices and quantities (if present)
    while (offset + 9 <= raw_packet.size() - TERMINAL_CODE_SIZE - 1) {
        // Warning: It is reasonable to discard the first byte since the stock price is likely 
        // not to exceed 9,999.
        uint32_t price = (raw_packet[offset + 1] << 24) |
                         (raw_packet[offset + 2] << 16) |
                         (raw_packet[offset + 3] << 8) |
                         raw_packet[offset + 4];
        packet.prices.push_back(price);
        offset += 5;

        if (offset + 4 > raw_packet.size()) break;

        uint32_t quantity = (raw_packet[offset] << 24) |
                            (raw_packet[offset + 1] << 16) |
                            (raw_packet[offset + 2] << 8) |
                            raw_packet[offset + 3];
        packet.quantities.push_back(quantity);
        offset += 4;
    }

    return true;
}

// Validate the checksum
bool Parser::validate_checksum(const std::vector<uint8_t>& raw_packet, const Packet& packet) {
    size_t checksum_position = calculate_checksum_position(raw_packet.size());
    if (checksum_position >= raw_packet.size()) return false;

    uint8_t calculated_checksum = 0;
    for (size_t i = 1; i < checksum_position; ++i) {
        calculated_checksum ^= raw_packet[i];
    }

    return calculated_checksum == raw_packet[checksum_position];
}

// Validate the terminal code
bool Parser::validate_terminal_code(const std::vector<uint8_t>& raw_packet, const Packet& packet) {
    size_t terminal_position = raw_packet.size() - TERMINAL_CODE_SIZE;
    return raw_packet[terminal_position] == 0x0D &&
           raw_packet[terminal_position + 1] == 0x0A;
}

// Determine checksum position dynamically
size_t Parser::calculate_checksum_position(size_t packet_length) const {
    return packet_length - TERMINAL_CODE_SIZE - 1; // -1 for checksum byte
}
