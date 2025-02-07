import twse_udp_resolver
import logging
import sys
import time
import argparse
from functools import partial

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s',
    level=logging.NOTSET,
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='main.log',
    encoding='utf-8'
)
logging.getLogger().setLevel(logging.NOTSET)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

def handle_packet(packet, mode, logger_stock):
    try:
        # Check if packet is None
        if packet is None:
            logging.warning("Received None packet")
            return
        
        # Check if logger_stock is set
        if logger_stock:
            logging.info(f"logger_stock: {logger_stock} type: {type(logger_stock)}")
            logging.info(f"packet.stock_code: {packet.stock_code} type: {type(packet.stock_code)}")
            if packet.stock_code != logger_stock:
                return
            
        # benchmark mode
        if mode == "benchmark":
            message = f"Match Time: {packet.match_time}"
            logging.info(message)
            return
            
        # Access packet properties directly
        message = f"Received Packet:\n"
        message += f"Message Length: {packet.message_length}\n"
        message += f"Business Type: {packet.business_type}\n"
        message += f"Format Code: {packet.format_code}\n"
        message += f"Format Version: {packet.format_version}\n"
        message += f"Transmission Number: {packet.transmission_number}\n"
        message += f"Stock Code: {packet.stock_code}\n"
        message += f"Match Time: {packet.match_time}\n"
        message += f"Display Item: {packet.display_item}\n"
        message += f"Limit Up Limit Down: {packet.limit_up_limit_down}\n"
        message += f"Status Note: {packet.status_note}\n"
        message += f"Cumulative Volume: {packet.cumulative_volume}"
        logging.info(message)
        
        
        # Print prices and quantities
        for i in range(len(packet.prices)):
            price_ss = f"Price {i + 1}: {packet.prices[i]}, Quantity: "
            if i < len(packet.quantities):
                price_ss += str(packet.quantities[i])
            else:
                price_ss += "N/A"
            logging.info(price_ss)


        checksum_ss = f"Checksum: {packet.checksum}"
        logging.info(checksum_ss)

        terminal_ss = f"Terminal Code: 0x{packet.terminal_code:x}"
        logging.info(terminal_ss)

        logging.info("=== Analyzed Packet ===")
        # analyze_packet(packet, stock_code); # Analyze the packet
        logging.info("========================")
            
    except Exception as e:
        logging.error(f"Error handling packet: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())

def parse_arguments():
    parser = argparse.ArgumentParser(description='TWSE UDP Resolver Python Interface')
    parser.add_argument('-multicast', type=str, help='Multicast group address')
    parser.add_argument('-iface', type=str, help='Interface IP address')
    parser.add_argument('-stock', type=str, help='Stock code filter')
    parser.add_argument('-mode', type=str, help='Operation mode')
    return parser.parse_args()

if __name__ == "__main__":
    try:
        args = parse_arguments()
        port = 10000
        mode = args.mode if args.mode else "normal"
        stock = args.stock.ljust(6, ' ') if args.stock else None
        
        parser = twse_udp_resolver.Parser()
        
        # Configure multicast if specified
        if args.multicast and args.iface:
            parser.set_multicast(args.multicast, args.iface)
            logging.info(f"Configured multicast: group={args.multicast}, interface={args.iface}")
        
        # Create a partial function with mode and stock parameters
        packet_handler = partial(handle_packet, mode=mode, logger_stock=stock)
        
        # Start the parser with the partial function
        logging.info(f"Starting parser on port {port}")
        parser.start_loop(port, packet_handler)
        
        # non stop looping
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping parser...")
        parser.end_loop()
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        parser.end_loop()