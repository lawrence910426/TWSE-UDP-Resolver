# replay pcap file
# sudo tcpreplay -i lo --pps=3000 twseudp_20250722_0825.pcap
# and run this script
# python analyzing_pcap.py -multicast 224.0.100.100 -iface 127.0.0.1 -stock 2330 -o 0722_2330.csv


import twse_udp_resolver
import logging
import sys
import time
import argparse
from functools import partial
import csv
import datetime

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s',
    level=logging.NOTSET,
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)
logging.getLogger().setLevel(logging.NOTSET)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

def naive_hex_to_dec(price):
    ss = str(hex(price))
    ss = ss[2:]

    result = 0
    digit = 0
    for c in ss:
        digit = ord(c) - ord('0')
        result = result * 10 + digit

    return result

def handle_packet(packet, mode, logger_stock, csv_writer):
    try:
        if packet is None:
            logging.warning("Received None packet")
            return

        if logger_stock:
            if packet.stock_code != logger_stock:
                return

        if mode == "benchmark":
            return

        row_data = []

        formatted_time = "N/A"
        if hasattr(packet, 'match_time') and packet.match_time is not None:
            match_time_str = str(hex(packet.match_time))[2:].zfill(12)
            if len(match_time_str) == 12:
                 hh = match_time_str[0:2]
                 mm = match_time_str[2:4]
                 ss = match_time_str[4:6]
                 ffffff = match_time_str[6:12]
                 formatted_time = f"{hh}:{mm}:{ss}.{ffffff}"

        row_data.append(formatted_time)
        row_data.append(packet.transmission_number)
        row_data.append(packet.stock_code)
        row_data.append(packet.display_item)
        row_data.append(packet.limit_up_limit_down)
        row_data.append(packet.status_note)
        row_data.append(naive_hex_to_dec(packet.cumulative_volume))

        has_deal_price_quantity = (packet.display_item & 0b10000000) != 0

        bid_count = (packet.display_item & 0b01110000) >> 4
        ask_count = (packet.display_item & 0b00001110) >> 1
        max_levels = 5

        prices = packet.prices
        quantities = packet.quantities
        offset = 0

        if has_deal_price_quantity and len(prices) > offset and len(quantities) > offset:
            row_data.append(naive_hex_to_dec(prices[offset]) / 10000.0)
            row_data.append(naive_hex_to_dec(quantities[offset]))
            offset += 1
        else:
            row_data.extend(['', ''])

        bids_added = 0
        for i in range(bid_count):
            if i < max_levels and len(prices) > offset and len(quantities) > offset:
                row_data.append(naive_hex_to_dec(prices[offset]) / 10000.0)
                row_data.append(naive_hex_to_dec(quantities[offset]))
                bids_added += 1
            offset += 1
        row_data.extend(['', ''] * (max_levels - bids_added))

        asks_added = 0
        for i in range(ask_count):
             if i < max_levels and len(prices) > offset and len(quantities) > offset:
                row_data.append(naive_hex_to_dec(prices[offset]) / 10000.0)
                row_data.append(naive_hex_to_dec(quantities[offset]))
                asks_added += 1
             offset += 1
        row_data.extend(['', ''] * (max_levels - asks_added))

        row_data.append(packet.checksum)
        row_data.append(packet.terminal_code)

        csv_writer.writerow(row_data)

    except Exception as e:
        logging.error(f"Error handling packet for stock {packet.stock_code if packet else 'N/A'}: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())

def parse_arguments():
    parser = argparse.ArgumentParser(description='TWSE UDP Resolver Python Interface')
    parser.add_argument('-multicast', type=str, help='Multicast group address')
    parser.add_argument('-iface', type=str, help='Interface IP address')
    parser.add_argument('-stock', type=str, help='Stock code filter')
    parser.add_argument('-mode', type=str, help='Operation mode (normal/benchmark)')
    parser.add_argument('-o', '--output', type=str, default='output.csv', help='Output CSV file name')
    return parser.parse_args()

if __name__ == "__main__":
    csv_file = None
    csv_writer = None
    parser = None
    try:
        args = parse_arguments()
        # port = 10000
        port = 3000
        mode = args.mode if args.mode else "normal"
        stock = args.stock.ljust(6, ' ') if args.stock else None
        output_filename = args.output

        csv_file = open(output_filename, 'w', newline='', encoding='utf-8')
        csv_writer = csv.writer(csv_file)

        header = [
            'MatchTime', 'TransmissionNumber', 'StockCode',
            'DisplayItem', 'LimitUpDown', 'StatusNote',
            'CumulativeVolume',
            'DealPrice', 'DealQuantity',
            'BidPrice1', 'BidQuantity1', 'BidPrice2', 'BidQuantity2',
            'BidPrice3', 'BidQuantity3', 'BidPrice4', 'BidQuantity4',
            'BidPrice5', 'BidQuantity5',
            'AskPrice1', 'AskQuantity1', 'AskPrice2', 'AskQuantity2',
            'AskPrice3', 'AskQuantity3', 'AskPrice4', 'AskQuantity4',
            'AskPrice5', 'AskQuantity5'
        ]
        csv_writer.writerow(header)

        parser = twse_udp_resolver.Parser()

        if args.multicast and args.iface:
            parser.set_multicast(args.multicast, args.iface)
            logging.info(f"Configured multicast: group={args.multicast}, interface={args.iface}")

        packet_handler = partial(handle_packet, mode=mode, logger_stock=stock, csv_writer=csv_writer)

        logging.info(f"Starting parser on port {port}, writing output to {output_filename}")
        parser.start_loop(port, packet_handler)

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("Stopping parser...")
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
    finally:
        if parser:
             parser.end_loop()
             logging.info("Parser stopped.")
        if csv_file:
            csv_file.close()
            logging.info(f"CSV file '{output_filename}' closed.")