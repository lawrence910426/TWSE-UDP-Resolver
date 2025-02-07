import twse_udp_resolver
import logging
import sys
import time
import argparse

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s',
    level=logging.NOTSET,
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='main.log',
    encoding='utf-8'
)
logging.getLogger().setLevel(logging.NOTSET)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

def handle_packet(packet):
    try:
        # Check if packet is None
        if packet is None:
            logging.warning("Received None packet")
            return
            
        # Access packet properties directly
        logging.info(f"Received packet for stock: {packet.stock_code}")
        logging.info(f"Match time: {hex(packet.match_time)}")
        logging.info(f"Cumulative volume: {packet.cumulative_volume}")
        
        # Output prices and quantities
        for i, (price, quantity) in enumerate(zip(packet.prices, packet.quantities)):
            logging.info(f"Level {i+1}: Price={price}, Quantity={quantity}")
            
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
        
        parser = twse_udp_resolver.Parser()
        
        # Configure multicast if specified
        if args.multicast and args.iface:
            parser.set_multicast(args.multicast, args.iface)
            logging.info(f"Configured multicast: group={args.multicast}, interface={args.iface}")
        
        # Set stock filter if specified
        if args.stock:
            logging.info(f"Setting stock filter: {args.stock}")
            parser.set_stock_filter(args.stock)
        
        # Start the parser
        logging.info(f"Starting parser on port {port}")
        parser.start_loop(port, handle_packet)
        
        # non stop looping
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping parser...")
        parser.end_loop()
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        parser.end_loop()