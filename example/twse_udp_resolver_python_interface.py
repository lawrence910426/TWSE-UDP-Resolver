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
    # encoding='utf-8'
)
logging.getLogger().setLevel(logging.NOTSET)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

def analyze_packet(packet):
    # Check if the packet offers deal price/quantity
    has_deal_price_quantity = (packet.display_item & 0b10000000) != 0
    
    # Check if the packet offers bids
    bid_count = (packet.display_item & 0b01110000) >> 4
    has_bids = bid_count > 0
    
    # Check if the packet offers asks
    ask_count = (packet.display_item & 0b00001110) >> 1
    has_asks = ask_count > 0

    message = f"Deal Price/Quantity: {'Yes' if has_deal_price_quantity else 'No'}\n"
    message += f"Bids: {'Yes' if has_bids else 'No'} ({bid_count} levels)\n"
    message += f"Asks: {'Yes' if has_asks else 'No'} ({ask_count} levels)\n"
    
    # Extract deal price and quantity
    offset = 0
    if has_deal_price_quantity:
        deal_price = packet.prices[offset]
        deal_quantity = packet.quantities[offset]
        message += f"Deal: Price = 0x{deal_price:x}, Quantity = 0x{deal_quantity:x}\n"
        offset += 1
    
    # Extract bid prices and quantities
    for i in range(bid_count):
        bid_price = packet.prices[offset]
        bid_quantity = packet.quantities[offset]
        message += f"Bid {i + 1}: Price = 0x{bid_price:x}, Quantity = 0x{bid_quantity:x}\n"
        offset += 1
    
    # Extract ask prices and quantities
    for i in range(ask_count):
        ask_price = packet.prices[offset]
        ask_quantity = packet.quantities[offset]
        message += f"Ask {i + 1}: Price = 0x{ask_price:x}, Quantity = 0x{ask_quantity:x}\n"
        offset += 1
    
    # Check if deal price is at bid or ask
    if has_deal_price_quantity and has_bids and has_asks:
        deal_price = packet.prices[0]  # Deal price is always the first price
        best_bid = packet.prices[1 if has_deal_price_quantity else 0]  # First bid
        best_ask = packet.prices[1 + bid_count if has_deal_price_quantity else bid_count]  # First ask
        
        if deal_price == best_bid:
            message += "Deal price is at bid\n"
        elif deal_price == best_ask:
            message += "Deal price is at ask\n"
        else:
            message += "Deal price is neither at bid nor ask\n"
    else:
        message += "Not enough information to determine deal price position\n"
    
    return message

# Format code 0x06, 0x17
def handle_packet_06(packet, mode, logger_stock):
    try:
        # Check if packet is None
        if packet is None:
            logging.warning("Received None packet")
            return
        
        # Check if logger_stock is set
        if logger_stock:
            if packet.stock_code != logger_stock:
                return
            
        # benchmark mode
        if mode == "benchmark":
            message = f"Match Time: {packet.match_time}"
            logging.info(message)
            return
            
        # Access packet properties directly
        message = f"Received Packet:\n"
        message += f"Message Length: {packet.message_length:x}\n"
        message += f"Business Type: {packet.business_type}\n"
        message += f"Format Code: {packet.format_code}\n"
        message += f"Format Version: {packet.format_version}\n"
        message += f"Transmission Number: {packet.transmission_number:x}\n"
        message += f"Stock Code: {packet.stock_code}\n"
        message += f"Match Time: {packet.match_time:x}\n"
        message += f"Display Item: {packet.display_item:x}\n"
        message += f"Limit Up Limit Down: {packet.limit_up_limit_down:x}\n"
        message += f"Status Note: {packet.status_note:x}\n"
        message += f"Cumulative Volume: {packet.cumulative_volume:x}\n"
        
        
        # Print prices and quantities
        for i in range(len(packet.prices)):
            price_ss = f"Price {i + 1}: {packet.prices[i]}, Quantity: "
            if i < len(packet.quantities):
                price_ss += str(packet.quantities[i])
            else:
                price_ss += "N/A"
            message += price_ss + "\n"


        checksum_ss = f"Checksum: {packet.checksum}"
        message += checksum_ss + "\n"

        terminal_ss = f"Terminal Code: 0x{packet.terminal_code:x}"
        message += terminal_ss + "\n"

        message += "=== Analyzed Packet ===\n"
        message += analyze_packet(packet)
        message += "========================"

        logging.info(message)
        return
            
    except Exception as e:
        logging.error(f"Error handling packet: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())

def handle_packet_14(packet, mode, logger_stock):
    if packet.format_code != 0x14:
        return
        
    try:
        brief_name = packet.warrant_brief_name.rstrip(b'\x00').decode('big5', errors='replace')
        separator = packet.separator.rstrip(b'\x00').decode('ascii', errors='replace')
        underlying = packet.underlying_asset.rstrip(b'\x00').decode('big5', errors='replace')
        exp_date = packet.expiration_date.rstrip(b'\x00').decode('ascii', errors='replace')
        style = packet.warrant_type_D.rstrip(b'\x00').decode('big5', errors='replace')
        w_type = packet.warrant_type_E.rstrip(b'\x00').decode('big5', errors='replace')
        cat = packet.warrant_type_F.rstrip(b'\x00').decode('big5', errors='replace')
        res = packet.reserved.rstrip(b'\x00').decode('ascii', errors='replace')

        logging.info("--- Warrant Details (Format 14) ---")
        logging.info(f"  Stock Code: {packet.stock_code}")
        logging.info(f"  A. 權證簡稱: {brief_name}")
        logging.info(f"     區隔字元: {separator}")
        logging.info(f"  B. 權證標的: {underlying}")
        logging.info(f"  C. 到期日: {exp_date}")
        logging.info(f"  D. 權證形式: {style}")
        logging.info(f"  E. 權證種類: {w_type}")
        logging.info(f"  F. 權證類型: {cat}")
        logging.info(f"  G. 保留欄位: {res}")
        logging.info("------------------------------------")

    except Exception as e:
        logging.error(f"Error decoding warrant data: {e}")

def handle_packet(packet, mode, logger_stock):
    """
    A unified packet handler that dispatches to specific handlers based on format_code.
    """
    if packet is None:
        logging.warning("Received None packet")
        return
    
    if packet.format_code == 0x06 or packet.format_code == 0x17:
        handle_packet_06(packet, mode, logger_stock)
    elif packet.format_code == 0x14:
        handle_packet_14(packet, mode, logger_stock)
    else:
        logging.warning(f"Received unhandled format code: {packet.format_code}")

def parse_arguments():
    parser = argparse.ArgumentParser(description='TWSE UDP Resolver Python Interface')
    parser.add_argument('-multicast', type=str, help='Multicast group address')
    parser.add_argument('-iface', type=str, help='Interface IP address')
    parser.add_argument('-stock', type=str, help='Stock code filter')
    parser.add_argument('-port', type=int, help='Port number')
    parser.add_argument('-mode', type=str, help='Operation mode')
    parser.add_argument('-format-codes', nargs='+', type=int, help='List of allowed format codes')
    return parser.parse_args()

if __name__ == "__main__":
    try:
        args = parse_arguments()
        port = args.port if args.port else 10000
        mode = args.mode if args.mode else "normal"
        stock = args.stock.ljust(6, ' ') if args.stock else None
        
        parser = twse_udp_resolver.Parser()
        
        # Configure allowed format codes if specified
        if args.format_codes:
            parser.set_allowed_format_codes(args.format_codes)
            logging.info(f"Configured allowed format codes: {args.format_codes}")

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