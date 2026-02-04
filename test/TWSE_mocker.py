import socket
import time

def calculate_checksum(data):
    """Calculate the XOR checksum of the given data."""
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum

def create_packet_1():
    # ESC-CODE (ASCII 27)
    esc_code = bytes([0x1B])

    # HEADER
    header = bytes([0x01, 0x13, 0x01, 0x06, 0x04, 0x00, 0x00, 0x45, 0x67])

    # BODY
    body = (
        b'\x32\x33\x33\x30\x20\x20'  # Stock code: "2330  "
        b'\x09\x04\x15\x06\x12\x78'  # Match time: 9:04:15.61.278
        b'\xD6'                      # Display item bitmap
        b'\x00'                      # Unusual indicator
        b'\x00'                      # Status indicator
        b'\x00\x01\x64\x23'          # Cumulative trading volume: 16423
        b'\x00\x00\x99\x50\x00'      # Current price: 99.5000
        b'\x00\x00\x12\x34'          # Current quantity: 1234
        # Buy Prices and Quantities
        b'\x00\x00\x99\x50\x00\x00\x00\x02\x50'
        b'\x00\x00\x99\x00\x00\x00\x00\x01\x75'
        b'\x00\x00\x98\x50\x00\x00\x00\x04\x77'
        b'\x00\x00\x97\x50\x00\x00\x00\x06\x69'
        b'\x00\x00\x97\x00\x00\x00\x00\x01\x25'
        # Sell Prices and Quantities
        b'\x00\x01\x00\x00\x00\x00\x00\x00\x80'
        b'\x00\x01\x00\x50\x00\x00\x00\x06\x75'
        b'\x00\x01\x01\x50\x00\x00\x00\x04\x60'
    )

    # Calculate checksum
    checksum = bytes([calculate_checksum(header + body)])

    # TERMINAL-CODE
    terminal_code = b'\x0D\x0A'

    return esc_code + header + body + checksum + terminal_code

def create_packet_2():
    esc_code = bytes([0x1B])
    header = bytes([0x00, 0x86, 0x01, 0x06, 0x04, 0x00, 0x06, 0x43, 0x23])
    body = (
        b'\x32\x30\x30\x32\x20\x20'  # Stock code: "2002  "
        b'\x10\x27\x33\x16\x50\x41'  # Match time: 10:27:33.165.041
        b'\xD0'                      # Display item bitmap
        b'\xA0'                      # Unusual indicator
        b'\x00'                      # Status indicator
        b'\x00\x01\x19\x21'          # Cumulative trading volume: 11921
        b'\x00\x00\x13\x85\x00'      # Current price: 13.8500
        b'\x00\x00\x19\x21'          # Current quantity: 1921
        # Buy Prices and Quantities
        b'\x00\x00\x13\x85\x00\x00\x00\x05\x40'
        b'\x00\x00\x13\x80\x00\x00\x00\x02\x30'
        b'\x00\x00\x13\x75\x00\x00\x00\x00\x72'
        b'\x00\x00\x13\x70\x00\x00\x00\x00\x69'
        b'\x00\x00\x13\x65\x00\x00\x00\x00\x81'
    )
    checksum = bytes([calculate_checksum(header + body)])
    terminal_code = b'\x0D\x0A'

    return esc_code + header + body + checksum + terminal_code

def create_packet_3():
    esc_code = bytes([0x1B])
    header = bytes([0x00, 0x86, 0x01, 0x06, 0x04, 0x00, 0x04, 0x12, 0x34])
    body = (
        b'\x31\x35\x30\x34\x20\x20'  # Stock code: "1504  "
        b'\x09\x50\x23\x27\x15\x34'  # Match time: 9:50:23.271.534
        b'\x8A'                      # Display item bitmap
        b'\x44'                      # Unusual indicator
        b'\x00'                      # Status indicator
        b'\x00\x00\x06\x50'          # Cumulative trading volume: 650
        b'\x00\x00\x11\x50\x00'      # Current price: 11.5000
        b'\x00\x00\x00\x17'          # Current quantity: 17
        # Sell Prices and Quantities
        b'\x00\x00\x11\x50\x00\x00\x00\x00\x70'
        b'\x00\x00\x11\x55\x00\x00\x00\x00\x35'
        b'\x00\x00\x11\x60\x00\x00\x00\x00\x46'
        b'\x00\x00\x11\x65\x00\x00\x00\x00\x28'
        b'\x00\x00\x11\x70\x00\x00\x00\x00\x19'
    )
    checksum = bytes([calculate_checksum(header + body)])
    terminal_code = b'\x0D\x0A'

    return esc_code + header + body + checksum + terminal_code

def create_packet_4():
    esc_code = bytes([0x1B])
    header = bytes([0x01, 0x22, 0x01, 0x06, 0x04, 0x08, 0x39, 0x24, 0x73])
    body = (
        b'\x36\x37\x37\x30\x20\x20'  # Stock code: "6770  "
        b'\x13\x08\x58\x99\x37\x12'  # Match time: 13:08:58.993.712
        b'\x5A'                      # Display item bitmap
        b'\x00'                      # Unusual indicator
        b'\x10'                      # Status indicator
        b'\x00\x00\x97\x49'          # Cumulative trading volume: 9749
        # Buy Prices and Quantities
        b'\x00\x00\x16\x70\x00\x00\x00\x00\x61'
        b'\x00\x00\x16\x65\x00\x00\x00\x02\x09'
        b'\x00\x00\x16\x60\x00\x00\x00\x06\x30'
        b'\x00\x00\x16\x55\x00\x00\x00\x11\x36'
        b'\x00\x00\x16\x50\x00\x00\x00\x12\x02'
        # Sell Prices and Quantities
        b'\x00\x00\x16\x75\x00\x00\x00\x01\x70'
        b'\x00\x00\x16\x80\x00\x00\x00\x01\x18'
        b'\x00\x00\x16\x85\x00\x00\x00\x01\x58'
        b'\x00\x00\x16\x90\x00\x00\x00\x04\x78'
        b'\x00\x00\x16\x95\x00\x00\x00\x02\x15'
    )
    checksum = bytes([calculate_checksum(header + body)])
    terminal_code = b'\x0D\x0A'

    return esc_code + header + body + checksum + terminal_code

def create_packet_useless_format():
    esc_code = bytes([0x1B])
    header = bytes([0x00, 0x86, 0x01, 0x07, 0x04, 0x00, 0x04, 0x12, 0x34])
    body = (
        b'\x31\x35\x30\x34\x20\x20'  # Stock code: "1504  "
        b'\x09\x50\x23\x27\x15\x34'  # Match time: 9:50:23.271.534
        b'\x8A'                      # Display item bitmap
        b'\x44'                      # Unusual indicator
        b'\x00'                      # Status indicator
        b'\x00\x00\x06\x50'          # Cumulative trading volume: 650
        b'\x00\x00\x11\x50\x00'      # Current price: 11.5000
        b'\x00\x00\x00\x17'          # Current quantity: 17
        # Sell Prices and Quantities
        b'\x00\x00\x11\x50\x00\x00\x00\x00\x70'
        b'\x00\x00\x11\x55\x00\x00\x00\x00\x35'
        b'\x00\x00\x11\x60\x00\x00\x00\x00\x46'
        b'\x00\x00\x11\x65\x00\x00\x00\x00\x28'
        b'\x00\x00\x11\x70\x00\x00\x00\x00\x19'
    )
    checksum = bytes([calculate_checksum(header + body)])
    terminal_code = b'\x0D\x0A'

    return esc_code + header + body + checksum + terminal_code

def create_packet_format_23_OTC():
    # ESC-CODE (ASCII 27)
    esc_code = bytes([0x1B]) 
    
    # HEADER
    header = bytes([
        0x00, # 2.1 Message Length
        0x67,
        0x02, # 2.2 Business Type
        0x23, # 2.3 Format Code
        0x01, # 2.4 Format Version
        0x00, # 2.5 Transmission Number
        0x87,
        0x12, 
        0x34  
        ])
    
    # BODY
    body = (
        b'\x38\x30\x36\x39\x20\x20' # 3.1 Stock code: "8069  "
        b'\x11\x30\x45\x12\x34\x56' # 3.2 Match time: 11:30:45.123.456
        b'\x92' # 3.3 Display Flag 
        b'\x00' # 3.4 Limit Up/Limit Down Flag
        b'\x10' # 3.5 Status Flag
        b'\x00\x00\x00\x00\x12\x34' # 3.6 Cumulative Volume: 1234
        # 3.7 Prices(5) and Quantities(6)
        b'\x00\x01\x85\x50\x00' # trade price:185.5000
        b'\x00\x00\x00\x00\x00\x50' # trade quantity:50
        b'\x00\x01\x85\x00\x00' # buy price 1:185.0000
        b'\x00\x00\x00\x00\x01\x00' # buy quantity 1:100
        b'\x00\x01\x86\x00\x00' # sell price 1:186.0000
        b'\x00\x00\x00\x00\x02\x00' # sell quantity 1:200
    )
    
    # Calculate checksum
    checksum = bytes([calculate_checksum(header + body)])
    
    # TERMINAL-CODE
    terminal_code = b'\x0D\x0A'
    return esc_code + header + body + checksum + terminal_code

def create_packet_format_23_TWSE():
    # ESC-CODE (ASCII 27)
    esc_code = bytes([0x1B]) 
    
    # HEADER 
    header = bytes([
        0x00, # 2.1 Message Length 
        0x94, 
        0x01, # 2.2 Business Type 
        0x23, # 2.3 Format Code
        0x01, # 2.4 Format Version
        0x00, # 2.5 Transmission Number
        0x31, 
        0x24, 
        0x55  
        ])
    
    # BODY
    body = (
        b'\x32\x33\x33\x30\x20\x20' # 3.1 Stock code: "2330  "
        b'\x13\x15\x30\x99\x88\x77' # 3.2 Match time: 13:15:30.998.877
        b'\xB2'                     # 3.3 Display Flag: Deal(1), Bids(3), Asks(1) -> 1 011 001 0
        b'\x00'                     # 3.4 Limit Up/Limit Down Flag: Normal
        b'\x10'                     # 3.5 Status Flag: Normal
        b'\x00\x00\x00\x10\x50\x00' # 3.6 Cumulative Volume: 1,050,00
        
        # 3.7 Dynamic Prices(5) and Quantities(6)
        # --- Deal ---
        b'\x00\x05\x85\x50\x00'     # trade price: 585.5000
        b'\x00\x00\x00\x00\x00\x10' # trade quantity: 10
        
        # --- Bids ---
        b'\x00\x05\x85\x00\x00'     # buy price 1: 585.0000
        b'\x00\x00\x00\x00\x01\x00' # buy quantity 1: 100
        b'\x00\x05\x84\x50\x00'     # buy price 2: 584.5000
        b'\x00\x00\x00\x00\x05\x00' # buy quantity 2: 500
        b'\x00\x05\x84\x00\x00'     # buy price 3: 584.0000 
        b'\x00\x00\x00\x00\x08\x00' # buy quantity 3: 800
        
        # --- Asks ---
        b'\x00\x05\x86\x00\x00'     # sell price 1: 586.0000
        b'\x00\x00\x00\x00\x07\x00' # sell quantity 1: 700
    )
    
    # Calculate checksum
    checksum = bytes([calculate_checksum(header + body)])
    
    # TERMINAL-CODE
    terminal_code = b'\x0D\x0A'
    return esc_code + header + body + checksum + terminal_code

def create_packet_invalid():
    return create_packet_1()[::-1]

def send_udp_packet(packet, ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(packet, (ip, port))
        print("Packet sent successfully!", flush=True)
    except Exception as e:
        print(f"Failed to send packet: {e}", flush=True)
    finally:
        sock.close()

if __name__ == "__main__":
    target_ip = "127.0.0.1"
    target_port = 10000

    packets = [
        create_packet_1(), create_packet_2(), create_packet_3(), create_packet_4(),
        create_packet_useless_format(), create_packet_invalid(), create_packet_format_23_OTC(), create_packet_format_23_TWSE()
    ]
    packet_index = 0

    while True:
        print(f"Sending packet {packet_index + 1}", flush=True)
        send_udp_packet(packets[packet_index], target_ip, target_port)
        packet_index = (packet_index + 1) % len(packets)  # Round-robin
        time.sleep(1)
