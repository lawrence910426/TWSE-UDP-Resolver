import twse_udp_resolver
import logging
import sys
import time
import argparse
import threading
import pandas as pd
import re
from datetime import datetime

# Logging configuration
logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s',
    level=logging.NOTSET,
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='main.log',
    encoding='utf-8'
)
logging.getLogger().setLevel(logging.NOTSET)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

# Global variables
packet_buffer = []
buffer_lock = threading.Lock()
flush_interval = 60  # seconds
time_of_next_flush = time.time() + flush_interval
output_file = 'packets.parquet'
filter_regex = None  # Compiled regex for stock filter

# Function to flush buffer to Parquet (overwrite same file)
def flush_to_parquet():
    with buffer_lock:
        data = list(packet_buffer)
    if not data:
        return
    df = pd.DataFrame(data)
    df.to_parquet(output_file, index=False)
    logging.info(f"Overwrote {output_file} with {len(data)} total packets")

# Packet handler builds structured fields, applies regex filter
def handle_packet(packet):
    try:
        if packet is None:
            logging.warning("Received None packet")
            return

        stock_code = packet.stock_code.strip()
        # Regex filter: skip if no match
        if filter_regex and not filter_regex.search(stock_code):
            return

        # Build record
        record = {
            'timestamp': datetime.now(),
            'message_length': packet.message_length,
            'business_type': packet.business_type,
            'format_code': packet.format_code,
            'format_version': packet.format_version,
            'transmission_number': packet.transmission_number,
            'stock_code': stock_code,
            'match_time': packet.match_time,
            'display_item': packet.display_item,
            'limit_up_limit_down': packet.limit_up_limit_down,
            'status_note': packet.status_note,
            'cumulative_volume': packet.cumulative_volume,
            'checksum': packet.checksum,
            'terminal_code': packet.terminal_code
        }

        # Decompose prices and quantities
        has_deal = (packet.display_item & 0b10000000) != 0
        bid_count = (packet.display_item & 0b01110000) >> 4
        ask_count = (packet.display_item & 0b00001110) >> 1
        offset = 0

        if has_deal:
            record['deal_price'] = packet.prices[offset]
            record['deal_volume'] = packet.quantities[offset]
            offset += 1
        else:
            record['deal_price'] = None
            record['deal_volume'] = None

        for i in range(1, bid_count + 1):
            record[f'bid_price_{i}'] = packet.prices[offset]
            record[f'bid_volume_{i}'] = packet.quantities[offset]
            offset += 1

        for j in range(1, ask_count + 1):
            record[f'ask_price_{j}'] = packet.prices[offset]
            record[f'ask_volume_{j}'] = packet.quantities[offset]
            offset += 1

        # Append record under lock
        with buffer_lock:
            packet_buffer.append(record)

    except Exception as e:
        logging.error(f"Error handling packet: {e}")
        import traceback
        logging.error(traceback.format_exc())

# Argument parsing
def parse_arguments():
    parser = argparse.ArgumentParser(description='TWSE UDP Resolver to Parquet')
    parser.add_argument('-multicast', type=str, help='Multicast group address')
    parser.add_argument('-iface', type=str, help='Interface IP address')
    parser.add_argument('-s', '--stock', type=str,
                        help='Regex to filter stock codes')
    parser.add_argument('-o', '--output', type=str, default='packets',
                        help='Output filename prefix (default: packets)')
    return parser.parse_args()

# Main execution
if __name__ == "__main__":
    try:
        args = parse_arguments()
        port = 10000

        # Setup output file
        output_file = f"{args.output.strip()}.parquet"

        # Compile stock regex if provided
        if args.stock:
            filter_regex = re.compile(args.stock)
            logging.info(f"Filtering stock codes with regex: {args.stock}")

        parser = twse_udp_resolver.Parser()
        if args.multicast and args.iface:
            parser.set_multicast(args.multicast, args.iface)
            logging.info(f"Configured multicast: group={args.multicast}, interface={args.iface}")

        logging.info(f"Starting parser on port {port}")
        parser.start_loop(port, handle_packet)

        # Main loop: flush buffer every minute (overwrite)
        while True:
            time.sleep(1)
            if time.time() >= time_of_next_flush:
                flush_to_parquet()
                time_of_next_flush = time.time() + flush_interval

    except KeyboardInterrupt:
        logging.info("Stopping parser...")
        flush_to_parquet()
        parser.end_loop()
    except Exception as e:
        logging.error(f"Error: {e}")
        parser.end_loop()
