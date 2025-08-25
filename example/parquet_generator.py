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
SCHEMA_06 = pa.schema([
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

SCHEMA_14 = pa.schema([
    ("brief_name", pa.string()),
    ("separator", pa.string()),
    ("underlying", pa.string()),
    ("exp_date", pa.string()),
    ("style", pa.string()),
    ("w_type", pa.string()),
    ("category", pa.string()),
    ("reserved", pa.string()),
])

packet_buffer_size_06 = 0
packet_buffer_06 = {name: [] for name in SCHEMA_06.names}

packet_buffer_size_14 = 0
packet_buffer_14 = {name: [] for name in SCHEMA_14.names}

buffer_lock = threading.Lock()

output_file = 'packets.parquet'
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
        if packet_buffer_size_06 > 0 and packet_buffer_size_14 > 0:
            raise Exception("Received both foramt 06 and 14")
        
        if packet_buffer_size_06 == 0 and packet_buffer_size_14 == 0:
            array = []
            logging.info("Building empty pyarrow Table")
            table = pa.Table.from_arrays(arrays)

        if packet_buffer_size_06 > 0:  
            logging.info(f"Building array of size = {packet_buffer_size_06}")
            t = time.time()
            arrays = [
                pa.array(packet_buffer_06[name], type=SCHEMA_06[i].type) for i, name in enumerate(SCHEMA_06.names)
            ]
            logging.info(f"Building array takes {t - time.time()} seconds. Building pyarrow Table for format 06.")
            
            t = time.time()
            table = pa.Table.from_arrays(arrays, names=SCHEMA_06.names)
            logging.info(f"Building takes {t - time.time()} seconds. Writing parquet with {packet_buffer_size_06} rows")
        
        if packet_buffer_size_14 > 0:
            logging.info(f"Building array of size = {packet_buffer_size_14}")
            arrays = [
                pa.array(packet_buffer_14[name], type=SCHEMA_14[i].type) for i, name in enumerate(SCHEMA_14.names)
            ]
            logging.info("Building pyarrow Table for format 14")
            table = pa.Table.from_arrays(arrays, names=SCHEMA_14.names)
            logging.info(f"Writing parquet with {packet_buffer_size_14} rows")

    t = time.time()
    atomic_write_parquet(table, output_file)
    logging.info(f"Writing takes {t - time.time()} seconds. File {output_file} wrote with {table.num_rows} lines.")

# Packet handler
def handle_packet(packet):
    """
    A unified packet handler that dispatches to specific handlers based on format_code.
    """
    if packet is None:
        logging.warning("Received None packet")
        return
    
    if packet.format_code == 0x06 or packet.format_code == 0x17:
        handle_packet_06(packet)
    elif packet.format_code == 0x14:
        handle_packet_14(packet)
    else:
        logging.warning(f"Received unhandled format code: {packet.format_code}")

# Packet handler that builds structured fields, applies regex filter
def handle_packet_06(packet):
    global packet_buffer_size_06, last_receive_packet

    last_receive_packet = time.time()

    try:
        with buffer_lock:
            if packet is None:
                logging.warning("Received None packet")
                return

            stock_code = packet.stock_code.strip()

            # Build record with BCD fields parsed
            packet_buffer_06['timestamp'].append(datetime.now())
            packet_buffer_06['message_length'].append(bcd_to_int(packet.message_length, 2))
            packet_buffer_06['business_type'].append(packet.business_type)
            packet_buffer_06['format_code'].append(packet.format_code)
            packet_buffer_06['format_version'].append(packet.format_version)
            packet_buffer_06['transmission_number'].append(bcd_to_int(packet.transmission_number, 4))
            packet_buffer_06['stock_code'].append(stock_code)
            packet_buffer_06['match_time'].append(bcd_to_int(packet.match_time, 6))
            packet_buffer_06['display_item'].append(packet.display_item)
            packet_buffer_06['limit_up_limit_down'].append(packet.limit_up_limit_down)
            packet_buffer_06['status_note'].append(packet.status_note)
            packet_buffer_06['cumulative_volume'].append(bcd_to_int(packet.cumulative_volume, 4))
            packet_buffer_06['checksum'].append(packet.checksum)
            packet_buffer_06['terminal_code'].append(packet.terminal_code)

            # Decompose prices and quantities
            has_deal = (packet.display_item & 0b10000000) != 0
            bid_count = (packet.display_item & 0b01110000) >> 4
            ask_count = (packet.display_item & 0b00001110) >> 1
            offset = 0

            # Deal price & volume
            if has_deal:
                packet_buffer_06['deal_price'].append(bcd_to_int(packet.prices[offset], 5) / 10000)
                packet_buffer_06['deal_volume'].append(bcd_to_int(packet.quantities[offset], 4))
                offset += 1
            else:
                packet_buffer_06['deal_price'].append(None)
                packet_buffer_06['deal_volume'].append(None)

            # Bid price/volume levels
            for i in range(1, 6): 
                if i <= bid_count:
                    packet_buffer_06[f'bid_price_{i}'].append(bcd_to_int(packet.prices[offset], 5) / 10000)
                    packet_buffer_06[f'bid_volume_{i}'].append(bcd_to_int(packet.quantities[offset], 4))
                    offset += 1
                else:
                    packet_buffer_06[f'bid_price_{i}'].append(None)
                    packet_buffer_06[f'bid_volume_{i}'].append(None)

            # Ask price/volume levels
            for j in range(1, 6):
                if j <= ask_count:
                    packet_buffer_06[f'ask_price_{j}'].append(bcd_to_int(packet.prices[offset], 5) / 10000)
                    packet_buffer_06[f'ask_volume_{j}'].append(bcd_to_int(packet.quantities[offset], 4))
                    offset += 1
                else:
                    packet_buffer_06[f'ask_price_{j}'].append(None)
                    packet_buffer_06[f'ask_volume_{j}'].append(None)

            packet_buffer_size_06 += 1

    except Exception as e:
        logging.error(f"Error handling packet: {e}")
        import traceback
        logging.error(traceback.format_exc())

# Handler for basic information of warranty
def handle_packet_14(packet):
    global packet_buffer_size_14, last_receive_packet

    last_receive_packet = time.time()
        
    try:
        with buffer_lock:
            brief_name = packet.warrant_brief_name.rstrip(b'\x00').decode('big5', errors='replace')
            separator = packet.separator.rstrip(b'\x00').decode('ascii', errors='replace')
            underlying = packet.underlying_asset.rstrip(b'\x00').decode('big5', errors='replace')
            exp_date = packet.expiration_date.rstrip(b'\x00').decode('ascii', errors='replace')
            style = packet.warrant_type_D.rstrip(b'\x00').decode('big5', errors='replace')
            w_type = packet.warrant_type_E.rstrip(b'\x00').decode('big5', errors='replace')
            category = packet.warrant_type_F.rstrip(b'\x00').decode('big5', errors='replace')
            reserved = packet.reserved.rstrip(b'\x00').decode('ascii', errors='replace')

            packet_buffer_14['brief_name'].append(brief_name)
            packet_buffer_14['separator'].append(separator)
            packet_buffer_14['underlying'].append(underlying)
            packet_buffer_14['exp_date'].append(exp_date)
            packet_buffer_14['style'].append(style)
            packet_buffer_14['w_type'].append(w_type)
            packet_buffer_14['category'].append(category)
            packet_buffer_14['reserved'].append(reserved)

            packet_buffer_size_14 += 1

    except Exception as e:
        logging.error(f"Error decoding warrant data: {e}")

# Argument parsing
def parse_arguments():
    parser = argparse.ArgumentParser(description='TWSE UDP Resolver to Parquet')
    parser.add_argument('-multicast', type=str, help='Multicast group address')
    parser.add_argument('-iface', type=str, help='Interface IP address')
    parser.add_argument('-o', '--output', type=str, default='packets.parquet',
                        help='Output filename prefix (default: packets.parquet)')
    parser.add_argument('-p', '--port', type=int, default=10000,
                        help='UDP port number (default: 10000)')
    parser.add_argument('-format-codes', nargs='+', type=int, help='List of allowed format codes')
    return parser.parse_args()

# Main execution
if __name__ == "__main__":
    try:
        args = parse_arguments()
        port = args.port

        # Setup output file
        output_file = f"{args.output.strip()}"

        parser = twse_udp_resolver.Parser()

        # Configure allowed format codes if specified
        if args.format_codes:
            parser.set_allowed_format_codes(args.format_codes)
            logging.info(f"Configured allowed format codes: {args.format_codes}")

        # Configure multicast and interface
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

            if no_packet_duration > 1 * 60:
                logging.info(f"1 minutes no packets. Flush and exit.")
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
