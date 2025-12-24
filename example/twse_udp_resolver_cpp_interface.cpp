#include <iostream>
#include <vector>
#include <cstdint>
#include <iomanip>
#include "../include/logger.h"
#include <sstream>
#include <csignal>
#include <atomic>
#include "../include/parser.h"

// Helper function to print price and quantity in hex
void print_price_quantity(const std::string& label, uint32_t price, uint32_t quantity) {
    std::stringstream ss;
    ss << label << ": Price = 0x" << std::hex << price
       << ", Quantity = 0x" << quantity << std::dec;
    Logger::getInstance().log(ss.str());
}

// Analyze the packet
void analyze_packet(const Packet& packet) {
    // Check if the packet offers deal price/quantity
    std::stringstream ss;
    
    bool has_deal_price_quantity = (packet.display_item & 0b10000000) != 0;

    // Check if the packet offers bids
    uint8_t bid_count = (packet.display_item & 0b01110000) >> 4;
    bool has_bids = bid_count > 0;

    // Check if the packet offers asks
    uint8_t ask_count = (packet.display_item & 0b00001110) >> 1;
    bool has_asks = ask_count > 0;

    ss << "Deal Price/Quantity: " << (has_deal_price_quantity ? "Yes" : "No") << "\n"
       << "Bids: " << (has_bids ? "Yes" : "No") << " (" << static_cast<int>(bid_count) << " levels)\n"
       << "Asks: " << (has_asks ? "Yes" : "No") << " (" << static_cast<int>(ask_count) << " levels)";
    Logger::getInstance().log(ss.str());

    // Extract deal price and quantity
    size_t offset = 0;
    if (has_deal_price_quantity) {
        uint32_t deal_price = packet.prices[offset];
        uint32_t deal_quantity = packet.quantities[offset];
        print_price_quantity("Deal", deal_price, deal_quantity);
        offset++;
    }

    // Extract bid prices and quantities
    for (uint8_t i = 0; i < bid_count; ++i) {
        uint32_t bid_price = packet.prices[offset];
        uint32_t bid_quantity = packet.quantities[offset];
        print_price_quantity("Bid " + std::to_string(i + 1), bid_price, bid_quantity);
        offset++;
    }

    // Extract ask prices and quantities
    for (uint8_t i = 0; i < ask_count; ++i) {
        uint32_t ask_price = packet.prices[offset];
        uint32_t ask_quantity = packet.quantities[offset];
        print_price_quantity("Ask " + std::to_string(i + 1), ask_price, ask_quantity);
        offset++;
    }

    // Check if the deal price is at bid or ask
    if (has_deal_price_quantity && has_bids && has_asks) {
        uint32_t deal_price = packet.prices[0]; // Deal price is always the first price
        uint32_t best_bid = packet.prices[has_deal_price_quantity ? 1 : 0]; // First bid price
        uint32_t best_ask = packet.prices[has_deal_price_quantity ? 1 + bid_count : bid_count]; // First ask price

        if (deal_price == best_bid) {
            Logger::getInstance().log("Deal price is at bid");
        } else if (deal_price == best_ask) {
            Logger::getInstance().log("Deal price is at ask");
        } else {
            Logger::getInstance().log("Deal price is neither at bid nor ask");
        }
    } else {
        Logger::getInstance().log("Not enough information to determine deal price position");
    }
}

// Callback function to handle received packets
void handle_packet(const Packet& packet, const std::string& mode, const std::string& logger_stock) {
    std::string stock_code(packet.stock_code, 6);
    std::stringstream ss;

    // Check if logger_stock is set
    if (!logger_stock.empty()) {
        if (stock_code != logger_stock) {
            return;
        }
    }

    if (mode == "benchmark") {
        // benchmark mode
        ss << "Match Time: " <<  std::hex << packet.match_time;
        Logger::getInstance().log(ss.str());
        return;
    }

    ss << "Received Packet:\n"
       << "Message Length: " << std::hex << packet.message_length << "\n"
       << "Business Type: " << static_cast<int>(packet.business_type) << "\n"
       << "Format Code: " << static_cast<int>(packet.format_code) << "\n"
       << "Format Version: " << static_cast<int>(packet.format_version) << "\n"
       << "Transmission Number: " << packet.transmission_number << "\n"
       << "Stock Code: " << stock_code << "\n"
       << "Match Time: " << packet.match_time << "\n"
       << "Display Item: " << static_cast<int>(packet.display_item) << "\n"
       << "Limit Up Limit Down: " << static_cast<int>(packet.limit_up_limit_down) << "\n"
       << "Status Note: " << static_cast<int>(packet.status_note) << "\n"
       << "Cumulative Volume: " << packet.cumulative_volume;
    
    Logger::getInstance().log(ss.str());

    // Print prices and quantities
    for (size_t i = 0; i < packet.prices.size(); ++i) {
        std::stringstream price_ss;
        price_ss << "Price " << i + 1 << ": " << packet.prices[i] << ", Quantity: ";
        if (i < packet.quantities.size()) {
            price_ss << packet.quantities[i];
        } else {
            price_ss << "N/A";
        }
        Logger::getInstance().log(price_ss.str());
    }

    std::stringstream checksum_ss;
    checksum_ss << "Checksum: " << static_cast<int>(packet.checksum);
    Logger::getInstance().log(checksum_ss.str());

    std::stringstream terminal_ss;
    terminal_ss << "Terminal Code: 0x" << std::hex << packet.terminal_code << std::dec;
    Logger::getInstance().log(terminal_ss.str());

    Logger::getInstance().log("=== Analyzed Packet ===");
    analyze_packet(packet); // Analyze the packet
    Logger::getInstance().log("========================");
}

int main(int argc, char* argv[]) {
    // Create a parser instance

    Parser parser;

    int port = 10000;
    std::string multicast_group;
    std::string interface_ip;
    std::string logger_stock;
    std::string mode;
    std::vector<uint8_t> format_codes;
    
    // Parse command line arguments
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "-multicast" && i + 1 < argc) {
            multicast_group = argv[++i];
        } else if (arg == "-port" && i + 1 < argc) {
            port = std::stoi(argv[++i]);
        } else if (arg == "-iface" && i + 1 < argc) {
            interface_ip = argv[++i];
        } else if (arg == "-stock" && i + 1 < argc) {
            logger_stock = argv[++i];
            logger_stock.resize(6, ' ');
        } else if (arg == "-mode" && i + 1 < argc) {
            mode = argv[++i];
        } else if (arg == "-format-codes") {
            while (i + 1 < argc && argv[i + 1][0] != '-') {
                try {
                    format_codes.push_back(static_cast<uint8_t>(std::stoi(argv[++i])));
                } catch (const std::exception& e) {
                    std::cerr << "Invalid format code: " << argv[i] << std::endl;
                }
            }
        }
    }

    // Configure multicast if specified
    if (!multicast_group.empty() && !interface_ip.empty()) {
        Logger::getInstance().log("Configuring multicast with group: " + multicast_group + 
                                " and interface: " + interface_ip);
        parser.set_multicast(multicast_group, interface_ip);
    }

    // Set allowed format codes if specified
    if (!format_codes.empty()) {
        parser.set_allowed_format_codes(format_codes);
    }

    // Start the parser with the callback function
    parser.start_loop(port, [mode, logger_stock](const Packet& p) { handle_packet(p, mode, logger_stock); });

    // non stop looping
    while (true) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    // Stop the parser
    parser.end_loop();

    return 0;
}