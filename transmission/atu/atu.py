import socket
import time

def flex6xxx_atu():
    UDP_IP = "" # INADDR_ANY

    UDP_PORT = 4992

    print("atu: Starting discovery...")

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    s.bind((UDP_IP, UDP_PORT))

    data, addr = s.recvfrom(1024)

    print (addr[0])     # IP ADDRESS

    s.close()

    #169.254.52.32

    TCP_IP = addr[0]

    TCP_PORT = 4992

    BUFFER_SIZE = 16384

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    s.connect((TCP_IP, TCP_PORT))

    time.sleep(1)       # wait 1 second for receive buffer to fill

    data_tcp = s.recv(BUFFER_SIZE)

    print(data_tcp)

    print("atu: Sending tunning command...")

    s.send("C42|atu start\n".encode("cp1252"))

    time.sleep(1)

    data_tcp = s.recv(BUFFER_SIZE)

    print(data_tcp)

    s.close()

    if (data_tcp.splitlines()[0] != b'R42|0|'):
        raise ValueError("atu: Failed to tune the radio with the antenna!")

    print("atu: Tunning succesfully completed.")

    return 0

