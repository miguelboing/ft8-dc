import socket
import time

def flex6xxx_atu():
    UDP_IP = "" # INADDR_ANY
    UDP_PORT = 4992
    TCP_PORT = 4992
    BUFFER_SIZE = 16384

    BASE_CMD_NUM = 1000000  # Start at 1 million
    MAX_CMD_NUM = 1500000 # Ends at 1.5 million and then loops back

    if not hasattr(flex6xxx_atu, "cmd_counter"):
        flex6xxx_atu.cmd_counter = BASE_CMD_NUM

    # This checks if the discovery step is already done
    if not hasattr(flex6xxx_atu, "tcp_addr"):
        print("atu: Starting discovery...")
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(5)
        s.bind((UDP_IP, UDP_PORT))

        try:
            data, addr = s.recvfrom(1024)
            print (f"atu: Discovered address: {addr[0]}")
            flex6xxx_atu.tcp_addr = addr[0] #169.254.52.32
        except socket.timeout:
            raise RuntimeError("atu: Discovery failed, no radio found")
        finally:
            s.close()

    # This checks if the connection is already established
    if getattr(flex6xxx_atu, "tcp_socket", None) is None:
        print("Establishing TCP Connection...")

        flex6xxx_atu.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        flex6xxx_atu.tcp_socket.settimeout(10)

        try:
            flex6xxx_atu.tcp_socket.connect((flex6xxx_atu.tcp_addr, TCP_PORT))
            time.sleep(1)

            data_tcp = flex6xxx_atu.tcp_socket.recv(BUFFER_SIZE)
            print(data_tcp)

        except(socket.error, socket.timeout) as e:
            try:
                flex6xxx_atu.tcp_socket.close()
            except:
                pass

            flex6xxx_atu.tcp_socket = None
            raise RuntimeError(f"atu: Failed to connect to radio: {e}")

    try:
        # Before sending the ATU command, drain any pending data
        try:
            flex6xxx_atu.tcp_socket.settimeout(0.1)  # Short timeout
            while True:
                flex6xxx_atu.tcp_socket.recv(BUFFER_SIZE)  # Drain buffer
        except socket.timeout:
            pass  # Buffer is now empty
        finally:
            flex6xxx_atu.tcp_socket.settimeout(10)  # Restore normal timeout
        print("atu: Sending tuning command...")

        flex6xxx_atu.tcp_socket.send(f"C{flex6xxx_atu.cmd_counter}|atu start\n".encode("cp1252"))

        time.sleep(1)
        data_tcp = flex6xxx_atu.tcp_socket.recv(BUFFER_SIZE)
        print(data_tcp)

        expected_response = f"R{flex6xxx_atu.cmd_counter}|0|"

        flex6xxx_atu.cmd_counter += 1
        if (flex6xxx_atu.cmd_counter > MAX_CMD_NUM):
            flex6xxx_atu.cmd_counter = BASE_CMD_NUM

        if not data_tcp or (data_tcp.splitlines()[0] != expected_response.encode()):
            raise ValueError("atu: Failed to tune the radio with the antenna!")

        # Wait 15s for the wc of tunning time
        time.sleep(15)
        print("atu: Tuning successfully completed.")

    except (socket.error, socket.timeout, BrokenPipeError) as e:
        print(f"atu: Connection error: {e}")

        try: # Close the broken connection
            flex6xxx_atu.tcp_socket.close()
        except:
            pass
        flex6xxx_atu.tcp_socket = None
        raise RuntimeError(f"atu: Connection failed: {e}")

    return 0

def no_atu():
    return 0

