'''
WSJT-X UDP Socket server
'''

import socket
import sys

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
    msgAndAddress = UDPServerSocket.recv(bufferSize)
    print("Got message")
    print(msgAndAddress)
