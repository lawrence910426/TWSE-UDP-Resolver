import twse_udp_resolver
import logging
import sys
import time

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
    print(packet)
    logging.info(f"Received packet with match time: {hex(packet.match_time)}")

if __name__ == "__main__":
    port = 10000
    mode = "test"
    
    parser = twse_udp_resolver.Parser()
    parser.start_loop(port, handle_packet)
    
    # non stop loopingpython test bash
    while True:
        time.sleep(1)

    # Stop the parser
    parser.end_loop()