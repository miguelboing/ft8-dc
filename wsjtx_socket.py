'''
WSJT-X UDP Socket server
'''

import socket
import sys
import pywsjtx_packets.wsjtx_packets

def main():
    ip = ''
    port = 5000

    bufferSize = 1024

    # Create socket
    UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

    # Enable multiple connections
    UDPServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind the address and IP
    UDPServerSocket.bind((ip, port))

    print("UDP server up and listening")

    # Receive messages from the client
    while(True):
        pkt, addr_port = UDPServerSocket.recvfrom(bufferSize)  # buffer size is 1024 bytes
        if (pkt != None):
            print("Got message")
            decoded_packet = pywsjtx_packets.wsjtx_packets.WSJTXPacketClassFactory.from_udp_packet(addr_port, pkt)
            print (decoded_packet)

if __name__ == "__main__":
    main()
