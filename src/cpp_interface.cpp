#include "parser.h"
#include <iostream>
#include <vector>
#include <cstdint>
#include <iomanip>
#include "logger.h"
#include <sstream>

// Helper function to print price and quantity in hex
void print_price_quantity(const std::string& label, uint32_t price, uint32_t quantity, const std::string& stock_code) {
    std::stringstream ss;
    ss << label << ": Price = 0x" << std::hex << price
       << ", Quantity = 0x" << quantity << std::dec;
    Logger::getInstance().log(ss.str(), stock_code);
}

// Analyze the packet
void analyze_packet(const Packet& packet, const std::string& stock_code) {
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
    Logger::getInstance().log(ss.str(), stock_code);

    // Extract deal price and quantity
    size_t offset = 0;
    if (has_deal_price_quantity) {
        uint32_t deal_price = packet.prices[offset];
        uint32_t deal_quantity = packet.quantities[offset];
        print_price_quantity("Deal", deal_price, deal_quantity, stock_code);
        offset++;
    }

    // Extract bid prices and quantities
    for (uint8_t i = 0; i < bid_count; ++i) {
        uint32_t bid_price = packet.prices[offset];
        uint32_t bid_quantity = packet.quantities[offset];
        print_price_quantity("Bid " + std::to_string(i + 1), bid_price, bid_quantity, stock_code);
        offset++;
    }

    // Extract ask prices and quantities
    for (uint8_t i = 0; i < ask_count; ++i) {
        uint32_t ask_price = packet.prices[offset];
        uint32_t ask_quantity = packet.quantities[offset];
        print_price_quantity("Ask " + std::to_string(i + 1), ask_price, ask_quantity, stock_code);
        offset++;
    }

    // Check if the deal price is at bid or ask
    if (has_deal_price_quantity && has_bids && has_asks) {
        uint32_t deal_price = packet.prices[0]; // Deal price is always the first price
        uint32_t best_bid = packet.prices[has_deal_price_quantity ? 1 : 0]; // First bid price
        uint32_t best_ask = packet.prices[has_deal_price_quantity ? 1 + bid_count : bid_count]; // First ask price

        if (deal_price == best_bid) {
            Logger::getInstance().log("Deal price is at bid", stock_code);
        } else if (deal_price == best_ask) {
            Logger::getInstance().log("Deal price is at ask", stock_code);
        } else {
            Logger::getInstance().log("Deal price is neither at bid nor ask", stock_code);
        }
    } else {
        Logger::getInstance().log("Not enough information to determine deal price position", stock_code);
    }

    Logger::getInstance().log("Stock code is " + stock_code, stock_code);
}

// Callback function to handle received packets
void handle_packet(const Packet& packet) {
    std::string stock_code(packet.stock_code, 6);
    std::stringstream ss;
    
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
    
    Logger::getInstance().log(ss.str(), stock_code);

    // Print prices and quantities
    for (size_t i = 0; i < packet.prices.size(); ++i) {
        std::stringstream price_ss;
        price_ss << "Price " << i + 1 << ": " << packet.prices[i] << ", Quantity: ";
        if (i < packet.quantities.size()) {
            price_ss << packet.quantities[i];
        } else {
            price_ss << "N/A";
        }
        Logger::getInstance().log(price_ss.str(), stock_code);
    }

    std::stringstream checksum_ss;
    checksum_ss << "Checksum: " << static_cast<int>(packet.checksum);
    Logger::getInstance().log(checksum_ss.str(), stock_code);

    std::stringstream terminal_ss;
    terminal_ss << "Terminal Code: 0x" << std::hex << packet.terminal_code << std::dec;
    Logger::getInstance().log(terminal_ss.str(), stock_code);

    Logger::getInstance().log("=== Analyzed Packet ===", stock_code);
    analyze_packet(packet, stock_code); // Analyze the packet
    Logger::getInstance().log("========================", stock_code);
}

int main(int argc, char* argv[]) {
    // Initialize logger with timestamp in filename
    time_t now = time(nullptr);
    char timestamp[32];
    strftime(timestamp, sizeof(timestamp), "%Y%m%d_%H%M%S", localtime(&now));
    std::string log_filename = "parser_" + std::string(timestamp) + ".log";
    Logger::getInstance().init(log_filename);

    const int port = 10000;
    std::string multicast_group;
    std::string interface_ip;
    std::string logger_stock;
    
    // Parse command line arguments
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "-multicast" && i + 1 < argc) {
            multicast_group = argv[++i];
        } else if (arg == "-iface" && i + 1 < argc) {
            interface_ip = argv[++i];
        } else if (arg == "-stock" && i + 1 < argc) {
            logger_stock = argv[++i];
            Logger::getInstance().setStockFilter(logger_stock);
        }
    }

    // Create a parser instance
    Parser parser;

    // Configure multicast if specified
    if (!multicast_group.empty() && !interface_ip.empty()) {
        Logger::getInstance().log("Configuring multicast with group: " + multicast_group + 
                                " and interface: " + interface_ip);
        parser.set_multicast(multicast_group, interface_ip);
    }

    // Start the parser with the callback function
    parser.start_loop(port, handle_packet);
    Logger::getInstance().log("Parser is running. It will stop automatically after 60 seconds...");

    // Wait for 60 seconds
    std::this_thread::sleep_for(std::chrono::seconds(60));

    // Stop the parser
    parser.end_loop();

    return 0;
}