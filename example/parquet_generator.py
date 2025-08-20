import twse_udp_resolver
import logging
import sys
import time
import argparse
import threading
import pandas as pd
import re
from datetime import datetime
import os, signal
import pyarrow as pa
import pyarrow.parquet as pq

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
SCHEMA = pa.schema([
    ("timestamp", pa.timestamp("us")),
    ("message_length", pa.int32()),
    ("business_type", pa.int32()),
    ("format_code", pa.int32()),
    ("format_version", pa.int32()),
    ("transmission_number", pa.int32()),
    ("stock_code", pa.string()),
    ("match_time", pa.int64()),
    ("display_item", pa.int32()),
    ("limit_up_limit_down", pa.int32()),
    ("status_note", pa.int32()),
    ("cumulative_volume", pa.int32()),
    ("checksum", pa.int32()),
    ("terminal_code", pa.int32()),

    ("deal_price", pa.float64()),
    ("deal_volume", pa.int32()),
    *[(f"bid_price_{i}",  pa.float64()) for i in range(1, 6)],
    *[(f"bid_volume_{i}", pa.int32())   for i in range(1, 6)],
    *[(f"ask_price_{i}",  pa.float64()) for i in range(1, 6)],
    *[(f"ask_volume_{i}", pa.int32())   for i in range(1, 6)],
])

packet_buffer_size = 0
packet_buffer = {name: [] for name in SCHEMA.names}
buffer_lock = threading.Lock()

flush_interval = 60  # seconds
output_file = 'packets.parquet'
filter_regex = None  # Compiled regex for stock filter
last_receive_packet = time.time()

# Helper: convert PACK BCD integer to normal integer
def bcd_to_int(value, num_bytes):
    """Convert PACK BCD stored in an integer into a normal integer, given its byte-length."""
    digits = []
    for pos in range(num_bytes * 2):
        shift = (num_bytes * 2 - 1 - pos) * 4
        digits.append(str((value >> shift) & 0xF))
    return int(''.join(digits))

def atomic_write_parquet(table, path):
    """Write table to a tmp file, fsync, then atomically replace final path."""
    tmp = f"{path}.tmp"
    pq.write_table(
        table, tmp,
        compression="zstd",
        write_statistics=True,
        coerce_timestamps="us",
    )
    fd = os.open(tmp, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)  # atomic on POSIX

# Function to flush buffer to Parquet (overwrite same file)
def flush_to_parquet():
    with buffer_lock:        
        arrays = [
            pa.array(packet_buffer[name], type=SCHEMA[i].type) for i, name in enumerate(SCHEMA.names)
        ]
    
    logging.info("Buidling pyarrow Table")
    table = pa.Table.from_arrays(arrays, names=SCHEMA.names)
    logging.info(f"Writing parquet with {packet_buffer_size} rows")
    atomic_write_parquet(table, output_file)
    logging.info(f"File {output_file} wrote with {table.num_rows} lines.")
    return packet_buffer_size

# Packet handler builds structured fields, applies regex filter
def handle_packet(packet):
    global packet_buffer_size, last_receive_packet

    last_receive_packet = time.time()

    try:
        with buffer_lock:
            if packet is None:
                logging.warning("Received None packet")
                return

            stock_code = packet.stock_code.strip()
            # Regex filter: skip if no match
            if filter_regex and not filter_regex.search(stock_code):
                return

            # Build record with BCD fields parsed
            packet_buffer['timestamp'].append(datetime.now())
            packet_buffer['message_length'].append(bcd_to_int(packet.message_length, 2))
            packet_buffer['business_type'].append(packet.business_type)
            packet_buffer['format_code'].append(packet.format_code)
            packet_buffer['format_version'].append(packet.format_version)
            packet_buffer['transmission_number'].append(bcd_to_int(packet.transmission_number, 4))
            packet_buffer['stock_code'].append(stock_code)
            packet_buffer['match_time'].append(bcd_to_int(packet.match_time, 6))
            packet_buffer['display_item'].append(packet.display_item)
            packet_buffer['limit_up_limit_down'].append(packet.limit_up_limit_down)
            packet_buffer['status_note'].append(packet.status_note)
            packet_buffer['cumulative_volume'].append(bcd_to_int(packet.cumulative_volume, 4))
            packet_buffer['checksum'].append(packet.checksum)
            packet_buffer['terminal_code'].append(packet.terminal_code)

            # Decompose prices and quantities
            has_deal = (packet.display_item & 0b10000000) != 0
            bid_count = (packet.display_item & 0b01110000) >> 4
            ask_count = (packet.display_item & 0b00001110) >> 1
            offset = 0

            # Deal price & volume
            if has_deal:
                packet_buffer['deal_price'].append(bcd_to_int(packet.prices[offset], 5) / 10000)
                packet_buffer['deal_volume'].append(bcd_to_int(packet.quantities[offset], 4))
                offset += 1
            else:
                packet_buffer['deal_price'].append(None)
                packet_buffer['deal_volume'].append(None)

            # Bid price/volume levels
            for i in range(1, 6): 
                if i <= bid_count:
                    packet_buffer[f'bid_price_{i}'].append(bcd_to_int(packet.prices[offset], 5) / 10000)
                    packet_buffer[f'bid_volume_{i}'].append(bcd_to_int(packet.quantities[offset], 4))
                    offset += 1
                else:
                    packet_buffer[f'bid_price_{i}'].append(None)
                    packet_buffer[f'bid_volume_{i}'].append(None)

            # Ask price/volume levels
            for j in range(1, 6):
                if j <= ask_count:
                    packet_buffer[f'ask_price_{j}'].append(bcd_to_int(packet.prices[offset], 5) / 10000)
                    packet_buffer[f'ask_volume_{j}'].append(bcd_to_int(packet.quantities[offset], 4))
                    offset += 1
                else:
                    packet_buffer[f'ask_price_{j}'].append(None)
                    packet_buffer[f'ask_volume_{j}'].append(None)

            packet_buffer_size += 1

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
    parser.add_argument('-o', '--output', type=str, default='packets.parquet',
                        help='Output filename prefix (default: packets.parquet)')
    parser.add_argument('-p', '--port', type=int, default=10000,
                        help='UDP port number (default: 10000)')
    return parser.parse_args()

# Main execution
if __name__ == "__main__":
    try:
        args = parse_arguments()
        port = args.port

        # Setup output file
        output_file = f"{args.output.strip()}"

        # Compile stock regex if provided
        if args.stock:
            if args.stock == "all":
                filter_regex = re.compile("[0-9]{4,}")
            else:
                filter_regex = re.compile(args.stock)
            logging.info(f"Filtering stock codes with regex: {filter_regex}")

        parser = twse_udp_resolver.Parser()
        if args.multicast and args.iface:
            parser.set_multicast(args.multicast, args.iface)
            logging.info(f"Configured multicast: group={args.multicast}, interface={args.iface}")

        logging.info(f"Starting parser on port {port}")
        parser.start_loop(port, handle_packet)

        # Main loop: flush buffer every minute (overwrite)
        while True:
            time.sleep(30)
            no_packet_duration = time.time() - last_receive_packet
            logging.info(f"Last packet received {no_packet_duration} seconds ago.")

            if no_packet_duration > 5 * 60:
                logging.info(f"5 minutes no packets. Flush and exit.")
                flush_to_parquet()
                logging.info(f"Completed.")
                raise KeyboardInterrupt()

    except KeyboardInterrupt:
        logging.info("Stopping parser...")
        flush_to_parquet()
        parser.end_loop()
    except Exception as e:
        logging.error(f"Error: {e}")
        parser.end_loop()
