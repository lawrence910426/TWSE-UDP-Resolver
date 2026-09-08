#include "parser.h"
#include <cstring>
#include <arpa/inet.h>
#include <unistd.h>
#include <sstream>
#include <algorithm>

// Constructor
Parser::Parser() : running(false), use_multicast(false) {
    // Initialize logger with timestamp in filename
    time_t now = time(nullptr);
    char timestamp[32];
    strftime(timestamp, sizeof(timestamp), "%Y%m%d_%H%M%S", localtime(&now));
    std::string log_filename = "parser_" + std::string(timestamp) + ".log";
    Logger::getInstance().init(log_filename);
}

// Destructor
Parser::~Parser() {
    end_loop();
}

// Start the UDP stream parsing loop in a new thread
void Parser::start_loop(int port, const PacketCallback& callback) {
    if (running) {
        log_message("Parser is already running!", true);
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
        if (sockfd != -1) {
            shutdown(sockfd, SHUT_RDWR);
            close(sockfd);
        }
        recv_thread.join();
    }
}

// Receive UDP packets and feed them into the parser
void Parser::receive_loop(int port) {
    sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sockfd < 0) {
        log_message("Socket creation failed: " + std::string(strerror(errno)), true);
        return;
    }

    // Enable SO_REUSEADDR
    int reuse = 1;
    if (setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse)) < 0) {
        log_message("Failed to set SO_REUSEADDR: " + std::string(strerror(errno)), true);
        close(sockfd);
        return;
    }

    // Enlarge the receive queue so brief consumer stalls don't drop packets.
    // SO_RCVBUFFORCE bypasses net.core.rmem_max but requires CAP_NET_ADMIN;
    // fall back to SO_RCVBUF (clamped to rmem_max) when unavailable.
    int rcvbuf = 64 * 1024 * 1024;
    if (setsockopt(sockfd, SOL_SOCKET, SO_RCVBUFFORCE, &rcvbuf, sizeof(rcvbuf)) < 0) {
        setsockopt(sockfd, SOL_SOCKET, SO_RCVBUF, &rcvbuf, sizeof(rcvbuf));
    }
    int actual_rcvbuf = 0;
    socklen_t rcvbuf_len = sizeof(actual_rcvbuf);
    getsockopt(sockfd, SOL_SOCKET, SO_RCVBUF, &actual_rcvbuf, &rcvbuf_len);
    log_message("recv buffer: " + std::to_string(actual_rcvbuf) + " bytes", false);

    sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    
    // Bind to the port
    if (bind(sockfd, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        log_message("Bind failed: " + std::string(strerror(errno)), true);
        close(sockfd);
        return;
    }

    if (use_multicast) {
        // Set up multicast request
        struct ip_mreq mreq{};
        mreq.imr_multiaddr.s_addr = inet_addr(multicast_group.c_str());
        mreq.imr_interface.s_addr = inet_addr(interface_ip.c_str());

        std::stringstream ss;
        ss << "Attempting to join multicast group " << multicast_group 
           << " on interface " << interface_ip;
        log_message(ss.str());

        if (setsockopt(sockfd, IPPROTO_IP, IP_ADD_MEMBERSHIP, &mreq, sizeof(mreq)) < 0) {
            log_message("Failed to join multicast group: " + std::string(strerror(errno)), true);
            close(sockfd);
            return;
        }

        // Set multicast interface
        struct in_addr local_interface{};
        local_interface.s_addr = inet_addr(interface_ip.c_str());
        if (setsockopt(sockfd, IPPROTO_IP, IP_MULTICAST_IF, &local_interface, sizeof(local_interface)) < 0) {
            log_message("Failed to set multicast interface: " + std::string(strerror(errno)), true);
            close(sockfd);
            return;
        }
    }

    std::stringstream init_ss;
    init_ss << "Successfully initialized socket on port " << port;
    if (use_multicast) {
        init_ss << " (multicast group: " << multicast_group 
                << ", interface: " << interface_ip << ")";
    }
    log_message(init_ss.str());

    char buffer[1500]; // Maximum UDP packet size

    while (running) {
        ssize_t len = recv(sockfd, buffer, sizeof(buffer), 0);
        if (len > 0) {
            process_datagram(reinterpret_cast<const uint8_t*>(buffer), static_cast<size_t>(len));
        } else if (len < 0) {
            if (errno != EINTR && errno != EBADF) {  // ignore EINTR and EBADF
                log_message("Error receiving data: " + std::string(strerror(errno)), true);
            }
            break;
        }
    }
}

void Parser::set_callback(const PacketCallback& callback) {
    packet_callback = callback;
}

void Parser::process_datagram(const uint8_t* data, size_t len) {
    if (len < 2) return;
    std::vector<uint8_t> raw_packet(data, data + len);

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
}

// Add a new method to configure multicast
void Parser::set_multicast(const std::string& group, const std::string& iface) {
    multicast_group = group;
    interface_ip = iface;
    use_multicast = true;
}

int hexStringToInt(const std::string& hex_str) {
    std::stringstream ss;
    ss << std::hex << hex_str;

    int value;
    ss >> value;

    if (ss.fail() && !ss.eof()) {
        throw std::runtime_error("Invalid hex string: " + hex_str);
    }

    return value;
}

// Add a new method to set allowed format codes
void Parser::set_allowed_format_codes(const std::vector<uint8_t>& codes) {
    // Store the codes verbatim (the API expects numeric format codes)
    for (const auto& code : codes) {
        allowed_format_codes.push_back(hexStringToInt(std::to_string(code)));
    }
    std::stringstream ss;
    ss << "C++: Received allowed format codes (hex): [ ";
    for (const auto& code : allowed_format_codes) {
        ss << std::hex << static_cast<int>(code) << " ";
    }
    ss << "]";
    log_message(ss.str());
}

// Parse the received packet
// Decode one framed record. Split out of parse_packet so the decoding path can
// be exercised without a socket: start_loop() is otherwise the only way in, and
// a unit test cannot bind a multicast group.
bool Parser::decode_packet(const std::vector<uint8_t>& raw_packet, Packet& packet) {
    packet = Packet{};

    if (raw_packet.empty() || raw_packet[0] != ESC_CODE) {
        log_message("Invalid packet");
        // log raw_packet
        std::stringstream ss;
        for (auto byte : raw_packet) {
            ss << std::hex << static_cast<int>(byte) << " ";
        }
        log_message(ss.str());
        return false; // Ignore packets that don't start with ESC-CODE
    }

    size_t offset = 1; // Start parsing after ESC-CODE

    // Parse the header
    if (!parse_header(raw_packet, packet, offset)) {
        log_message("Invalid header");
        // log raw_packet
        std::stringstream ss;
        for (auto byte : raw_packet) {
            ss << std::hex << static_cast<int>(byte) << " ";
        }
        log_message(ss.str());
        return false; // Ignore invalid packets
    }
    if (packet.format_code == 0x01) {
        if (!parse_body_01(raw_packet, packet, offset)) {
            log_message("Invalid body for format code 0x01");
            return false;
        }
    } else if (packet.format_code == 0x06 || packet.format_code == 0x17) {
        if (!parse_body_06(raw_packet, packet, offset)) {
            log_message("Invalid body for format code 0x06");
            return false;
        }
    } else if (packet.format_code == 0x14) {
        if (!parse_body_14(raw_packet, packet, offset)) {
            log_message("Invalid body for format code 0x14");
            return false;
        }
    } else if (packet.format_code == 0x23) {
        if (!parse_body_23(raw_packet, packet, offset)) {
            log_message("Invalid body for format code 0x23");
            return false;
        }
    } else {
        // log_message("Unsupported format code: " + std::to_string(packet.format_code));
        return false; // Ignore unsupported format codes
    }

    // Validate the checksum
    if (!validate_checksum(raw_packet, packet)) {
        log_message("Invalid checksum");
        // log raw_packet
        std::stringstream ss;
        for (auto byte : raw_packet) {
            ss << std::hex << static_cast<int>(byte) << " ";
        }
        log_message(ss.str());
        return false; // Ignore invalid packets
    }

    // Validate the terminal code
    if (!validate_terminal_code(raw_packet, packet)) {
        log_message("Invalid terminal code");
        return false; // Ignore invalid packets
    }

    return true;
}

void Parser::parse_packet(const std::vector<uint8_t>& raw_packet) {
    Packet packet{};
    if (decode_packet(raw_packet, packet) && packet_callback) {
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

    
    if (allowed_format_codes.empty()) {
        return false;
    }
    
    if (!allowed_format_codes.empty() &&
        std::find(allowed_format_codes.begin(), allowed_format_codes.end(), packet.format_code) == allowed_format_codes.end()) {
        return false; // Not in the allowed list, so we skip this packet
    }

    return true; 
}

// Decode an n-byte PACK BCD field to its numeric value: two decimal digits per
// byte, so 0x01 0x23 0x45 0x67 0x89 is 123456789. Returns false when a nibble is
// not a decimal digit -- the cheapest available evidence that the body is not
// aligned where we think it is, since a misread field almost always lands on one.
static bool decode_pack_bcd(const std::vector<uint8_t>& raw_packet, size_t offset,
                            size_t length, uint64_t& out) {
    uint64_t value = 0;
    for (size_t i = 0; i < length; ++i) {
        const uint8_t byte = raw_packet[offset + i];
        const uint8_t hi = byte >> 4;
        const uint8_t lo = byte & 0x0F;
        if (hi > 9 || lo > 9) return false;
        value = value * 100 + hi * 10 + lo;
    }
    out = value;
    return true;
}

// Parse the body for format code 0x01 (per-symbol reference data).
//
// Fixed 114-byte message carrying the day's reference, limit-up and limit-down
// prices -- the only message that does. Offsets below are relative to `offset`,
// which parse_header leaves pointing at the stock code (spec byte 11; spec bytes
// are 1-based and byte 1 is the ESC code). TPEx puts every price one byte later
// than TWSE because it carries an extra category-note field; business_type tells
// the two apart.
//
//                                  TWSE (business type 01)  TPEx (02)
//   reference price 9(5)V9(4) 5B       spec 41-45           spec 42-46
//   limit-up price            5B       spec 46-50           spec 47-51
//   limit-down price          5B       spec 51-55           spec 52-56
//
// No message-length or version equality check: the bounds check below plus BCD nibble
// validation plus the caller's checksum already reject a misparse, and pinning
// the version would reject a future revision with a compatible prefix.
bool Parser::parse_body_01(const std::vector<uint8_t>& raw_packet, Packet& packet, size_t& offset) {
    const bool is_otc = (packet.business_type == 0x02);
    const size_t price_base = offset + (is_otc ? 31 : 30);
    const size_t body_end = price_base + 15; // three consecutive 5-byte prices
    if (body_end > raw_packet.size()) return false;

    std::memcpy(packet.stock_code, &raw_packet[offset], 6);
    // The symbol count note is at spec 37-38, i.e. 26 bytes past the stock code.
    std::memcpy(packet.symbol_count_note, &raw_packet[offset + 26], 2);

    // Deliberately NOT the raw-BCD-bytes convention that the format 0x06 prices
    // below use: these three are decoded to their numeric value here, because
    // 9(5)V9(4) pins the scale at 4 decimals with no ambiguity. The decoded
    // integer therefore IS the price in 1/10000 NTD, and a field named
    // limit_up_price cannot be mistaken for undecoded bytes.
    if (!decode_pack_bcd(raw_packet, price_base,      5, packet.reference_price) ||
        !decode_pack_bcd(raw_packet, price_base +  5, 5, packet.limit_up_price) ||
        !decode_pack_bcd(raw_packet, price_base + 10, 5, packet.limit_down_price)) {
        return false;
    }

    offset = body_end;
    return true;
}

// Parse the body for format code 0x06, 0x17
bool Parser::parse_body_06(const std::vector<uint8_t>& raw_packet, Packet& packet, size_t& offset) {
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

// Parse the body for format code 0x14
bool Parser::parse_body_14(const std::vector<uint8_t>& raw_packet, Packet& packet, size_t& offset) {
    const size_t body_length = 56;

    if (offset + body_length > raw_packet.size()) return false;

    std::memcpy(packet.stock_code, &raw_packet[offset], 6);
    offset += 6;

    std::memcpy(packet.warrant_brief_name, &raw_packet[offset], 16);
    offset += 16;
    std::memcpy(packet.separator, &raw_packet[offset], 2);
    offset += 2;
    std::memcpy(packet.underlying_asset, &raw_packet[offset], 16);
    offset += 16;
    std::memcpy(packet.expiration_date, &raw_packet[offset], 8);
    offset += 8;
    std::memcpy(packet.warrant_type_D, &raw_packet[offset], 2);
    offset += 2;
    std::memcpy(packet.warrant_type_E, &raw_packet[offset], 2);
    offset += 2;
    std::memcpy(packet.warrant_type_F, &raw_packet[offset], 2);
    offset += 2;
    std::memcpy(packet.reserved, &raw_packet[offset], 2);
    offset += 2;

    return true;
}

// --- parse body for format 0x23 ---
bool Parser::parse_body_23(const std::vector<uint8_t>& raw_packet, Packet& packet, size_t& offset) {
    // Minimum required: stock_code(6) + match_time(6) + display_item(1) + limit_up_limit_down(1) + status_note(1) + cumulative_volume(6)
    const size_t min_body_len = 6 + 6 + 1 + 1 + 1 + 6;
    if (offset + min_body_len > raw_packet.size()) return false;

    std::memcpy(packet.stock_code, &raw_packet[offset], 6);
    offset += 6;

    packet.match_time = 0;
    for (size_t i = 0; i < 6; ++i) {
        packet.match_time = (packet.match_time << 8) | raw_packet[offset++];
    }

    packet.display_item = raw_packet[offset++];
    packet.limit_up_limit_down = raw_packet[offset++];
    packet.status_note = raw_packet[offset++];

    // cumulative volume is 6 bytes for format 0x23
    packet.cumulative_volume = 0;
    for (size_t i = 0; i < 6; ++i) {
        packet.cumulative_volume = (packet.cumulative_volume << 8) | raw_packet[offset++];
    }

    // Parse dynamic prices and quantities (if present) - same as format 0x23
    while (offset + 11 <= raw_packet.size() - TERMINAL_CODE_SIZE - 1) {
        
        // Price (5 bytes PACK BCD)
        uint64_t price = 0;
        for (int i = 0; i < 5; ++i) {
            price = (price << 8) | raw_packet[offset++];
        }
        packet.prices.push_back((uint32_t)price);

        // Check if remaining length is enough for quantity (6 bytes)
        if (offset + 6 > raw_packet.size()) break;

        // Quantity (Format 23 is 6 bytes PACK BCD)
        uint64_t quantity = 0;
        for (int i = 0; i < 6; ++i) {
            quantity = (quantity << 8) | raw_packet[offset++];
        }
        packet.quantities.push_back((uint32_t)quantity);
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

// Add logging function
void Parser::log_message(const std::string& message, bool error) {
#ifdef DEBUG
    Logger::getInstance().log(message, error);
#endif
}
