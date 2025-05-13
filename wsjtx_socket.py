'''
WSJT-X UDP Socket server
'''

import socket
import sys

ip = '127.0.0.1'
port = 5000

bufferSize = 1024

# Create socket
UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Bind the address and IP
UDPServerSocket.bind((ip, port))

print("UDP server up and listening")

# Receive messages from the client
while(True):
    msgAndAddress = UDPServerSocket.recvfrom(bufferSize)
    print(msgAndAddress[0].decode())
