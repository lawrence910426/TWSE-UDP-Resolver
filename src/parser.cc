#include "parser.h"
#include <iostream>
#include <cstring>
#include <arpa/inet.h>
#include <unistd.h>

// Constructor
Parser::Parser() : running(false) {}

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
        std::cerr << "Socket creation failed!" << std::endl;
        return;
    }

    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(port);

    // Bind the socket to the specified port
    if (bind(sockfd, (const struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        std::cerr << "Socket bind failed!" << std::endl;
        close(sockfd);
        return;
    }

    struct ip_mreq mreq;
    mreq.imr_multiaddr.s_addr = inet_addr("224.0.100.100");
    mreq.imr_interface.s_addr = inet_addr("192.168.205.30");

    if (setsockopt(sockfd, IPPROTO_IP, IP_ADD_MEMBERSHIP, &mreq, sizeof(mreq)) < 0) {
	        std::cerr << "Failed to join multicast group on interface 192.168.205.30" << std::endl;
		    close(sockfd);
		        return;
    }

    while (running) {
        ssize_t len = recv(sockfd, buffer, sizeof(buffer), 0);
	std::cout << "Packet size: " << len << std::endl;
        if (len > 0) {
            std::vector<uint8_t> raw_packet(buffer, buffer + len);
            parse_packet(raw_packet);

	    if (len < 200) {
		        for (uint8_t v : raw_packet)
				        std::cout << std::hex << +v << " ";
			return;
	    }
        }
    }

    close(sockfd);
}

// Parse the received packet
void Parser::parse_packet(const std::vector<uint8_t>& raw_packet) {
    if (raw_packet.empty() || raw_packet[0] != ESC_CODE) {
        return; // Ignore packets that don't start with ESC-CODE
    }

    Packet packet{};
    size_t offset = 1; // Start parsing after ESC-CODE

    // Parse the header
    if (!parse_header(raw_packet, packet, offset)) {
        return; // Ignore invalid packets
    }

    // Parse the body
    if (!parse_body(raw_packet, packet, offset)) {
        return; // Ignore invalid packets
    }

    // Validate the checksum
    if (!validate_checksum(raw_packet, packet)) {
        return; // Ignore invalid packets
    }

    // Validate the terminal code
    if (!validate_terminal_code(raw_packet, packet)) {
        return; // Ignore invalid packets
    }

    // If all checks pass, invoke the callback
    if (packet_callback) {
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
    for (size_t i = 0; i < checksum_position; ++i) {
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
