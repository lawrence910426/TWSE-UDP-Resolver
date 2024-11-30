import socket
import time

def calculate_checksum(data):
    """Calculate the XOR checksum of the given data."""
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum

def create_udp_packet():
    # ESC-CODE (ASCII 27)
    esc_code = bytes([0x1B])

    # HEADER
    message_length = bytes([0x01, 0x13])  # 113 Bytes
    business_type = bytes([0x01])         # "01" for 集中市場普通股競價交易
    format_code = bytes([0x06])           # Format code "06"
    format_version = bytes([0x04])        # Format version "04"
    transmission_number = bytes([0x00, 0x00, 0x45, 0x67])  # Example sequence 4567

    header = message_length + business_type + format_code + format_version + transmission_number

    # BODY
    stock_code = b'\x32\x33\x33\x30\x20\x20'  # Stock code: "2330  "
    match_time = b'\x09\x04\x15\x06\x12\x78'  # Match time: 9:04:15:61.278
    display_item = bytes([0xD6])              # Display item bitmap
    unusual = bytes([0x00])                   # Unusual indicator
    status_note = bytes([0x00])               # Status indicator
    cumulative_trading_volume = bytes([0x00, 0x01, 0x64, 0x23])  # Volume: 16423
    current_price = b'\x00\x00\x99\x50\x00'   # Price: 99.5000
    current_quantity = b'\x00\x00\x12\x34'    # Quantity: 1234

    # Buy/Sell Prices and Quantities
    buy_prices = [
        b'\x00\x00\x99\x50\x00',  # Price 1: 99.5000
        b'\x00\x00\x99\x00\x00',  # Price 2: 99.0000
        b'\x00\x00\x98\x50\x00',  # Price 3: 98.5000
        b'\x00\x00\x97\x50\x00',  # Price 4: 97.5000
        b'\x00\x00\x97\x00\x00'   # Price 5: 97.0000
    ]
    buy_quantities = [
        b'\x00\x00\x02\x50',  # Quantity 1: 250
        b'\x00\x00\x01\x75',  # Quantity 2: 175
        b'\x00\x00\x04\x77',  # Quantity 3: 477
        b'\x00\x00\x06\x69',  # Quantity 4: 669
        b'\x00\x00\x01\x25'   # Quantity 5: 125
    ]
    sell_prices = [
        b'\x00\x01\x00\x00\x00',  # Price 1: 100.0000
        b'\x00\x01\x00\x50\x00',  # Price 2: 100.5000
        b'\x00\x01\x01\x50\x00'   # Price 3: 101.5000
    ]
    sell_quantities = [
        b'\x00\x00\x00\x80',  # Quantity 1: 80
        b'\x00\x00\x06\x75',  # Quantity 2: 675
        b'\x00\x00\x04\x60'   # Quantity 3: 460
    ]

    body = (
        stock_code + match_time + display_item + unusual +
        status_note + cumulative_trading_volume + current_price +
        current_quantity
    )

    # Add Buy/Sell Prices and Quantities
    for i in range(5):
        body += buy_prices[i] + buy_quantities[i]
    for i in range(3):
        body += sell_prices[i] + sell_quantities[i]

    # CHECKSUM
    checksum_data = esc_code + header + body
    checksum = calculate_checksum(checksum_data)
    checksum = bytes([checksum])

    # TERMINAL-CODE
    terminal_code = b'\x0D\x0A'  # Hex: 0D 0A

    # Combine all components
    udp_packet = esc_code + header + body + checksum + terminal_code

    return udp_packet


def send_udp_packet(packet, ip, port):
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Send the packet
        sock.sendto(packet, (ip, port))
        print("Packet sent successfully!", flush=True)
    except Exception as e:
        print(f"Failed to send packet: {e}", flush=True)
    finally:
        sock.close()


if __name__ == "__main__":
    # Target IP and Port
    target_ip = "127.0.0.1"
    target_port = 12345

    # Create and send the UDP packet
    while True:
        packet = create_udp_packet()
        print("Sending the UDP packet that contains real information", flush=True)
        send_udp_packet(packet, target_ip, target_port)
        time.sleep(1)

        print("Sending the UDP packet that contains garbage information", flush=True)
        send_udp_packet(packet[::-1], target_ip, target_port)
        time.sleep(1)
