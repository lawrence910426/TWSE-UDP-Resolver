#include "parser.h"
#include <iostream>
#include <vector>
#include <cstdint>

// Callback function to handle received packets
void handle_packet(const Packet& packet) {
    // Print basic information from the packet
    std::cout << "Received Packet:" << std::endl;
    std::cout << "Message Length: " << packet.message_length << std::endl;
    std::cout << "Business Type: " << static_cast<int>(packet.business_type) << std::endl;
    std::cout << "Format Code: " << static_cast<int>(packet.format_code) << std::endl;
    std::cout << "Format Version: " << static_cast<int>(packet.format_version) << std::endl;
    std::cout << "Transmission Number: " << packet.transmission_number << std::endl;
    std::cout << "Stock Code: " << std::string(packet.stock_code, 6) << std::endl;
    std::cout << "Match Time: " << packet.match_time << std::endl;
    std::cout << "Display Item: " << static_cast<int>(packet.display_item) << std::endl;
    std::cout << "Unusual Event: " << static_cast<int>(packet.unusual_event) << std::endl;
    std::cout << "Status Note: " << static_cast<int>(packet.status_note) << std::endl;
    std::cout << "Cumulative Volume: " << packet.cumulative_volume << std::endl;

    // Print prices and quantities
    for (size_t i = 0; i < packet.prices.size(); ++i) {
        std::cout << "Price " << i + 1 << ": " << packet.prices[i] << ", Quantity: ";
        if (i < packet.quantities.size()) {
            std::cout << packet.quantities[i] << std::endl;
        } else {
            std::cout << "N/A" << std::endl;
        }
    }

    std::cout << "Checksum: " << static_cast<int>(packet.checksum) << std::endl;
    std::cout << "Terminal Code: 0x" << std::hex << packet.terminal_code << std::dec << std::endl;
}

int main() {
    // Port to listen on
    const int port = 12345;

    // Create a parser instance
    Parser parser;

    // Start the parser with the callback function
    parser.start_loop(port, handle_packet);

    std::cout << "Parser is running. It will stop automatically after 60 seconds..." << std::endl;

    // Wait for 60 seconds
    std::this_thread::sleep_for(std::chrono::seconds(60));

    // Stop the parser
    parser.end_loop();

    std::cout << "Parser has stopped after 60 seconds." << std::endl;
    return 0;
}