import socket
import time

def flex6xxx_atu(tune_tx_power):
    UDP_IP = "" # INADDR_ANY
    UDP_PORT = 4992
    SWR_R_UDP_PORT = 4200
    TCP_PORT = 4992
    BUFFER_SIZE = 16384

    BASE_CMD_NUM = 1000000  # Start at 1 million
    MAX_CMD_NUM = 1500000 # Ends at 1.5 million and then loops back

    swr = -1

    def flush_tcp_buffer():
        try:
            flex6xxx_atu.tcp_socket.settimeout(0.1)  # Short timeout
            while True:
                flex6xxx_atu.tcp_socket.recv(BUFFER_SIZE)  # Drain buffer
        except socket.timeout:
            pass  # Buffer is now empty
        finally:
            flex6xxx_atu.tcp_socket.settimeout(10)  # Restore normal timeout

    def send_tcp_command(command):
        flush_tcp_buffer()

        message = f"C{flex6xxx_atu.cmd_counter}|{command}\n"
        print(message)
        flex6xxx_atu.tcp_socket.send(message.encode("cp1252"))

        time.sleep(1)
        data_tcp = flex6xxx_atu.tcp_socket.recv(BUFFER_SIZE)
        print(data_tcp)

        expected_response = f"R{flex6xxx_atu.cmd_counter}|0|"

        flex6xxx_atu.cmd_counter += 1
        if (flex6xxx_atu.cmd_counter > MAX_CMD_NUM):
            flex6xxx_atu.cmd_counter = BASE_CMD_NUM

        if not data_tcp or (expected_response.encode() not in data_tcp.splitlines()):
                raise ValueError(f"atu: Failed to confirm the error code: {message}!")


    def swr_enable_socket():
        # UDP Port to the SWR
        flex6xxx_atu.udp_swr_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        flex6xxx_atu.udp_swr_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        flex6xxx_atu.udp_swr_socket.settimeout(10)
        flex6xxx_atu.udp_swr_socket.bind(("", SWR_R_UDP_PORT))  # Add this line

        return

    def swr_disable_socket():
        flex6xxx_atu.udp_swr_socket.close()

        return

    def swr_read_value(tune_tx_power):
        swr = -1

        send_tcp_command(f"transmit tune on")
        time.sleep(1)

        swr_enable_socket()
        for i in range(15):
            data, _ = flex6xxx_atu.udp_swr_socket.recvfrom(1024)

            if (data.hex()[-6:-4] == "0a"): # Checking if the received parameter is actually the SWR
                swr_r = int.from_bytes(data[-2:], byteorder='big')/128
                if (swr_r > swr): # Get the biggest value of swr
                    swr = swr_r

        send_tcp_command(f"transmit tune off")
        swr_disable_socket()

        print(f"SWR: {swr}!")

        return swr

    if not hasattr(flex6xxx_atu, "cmd_counter"):
        flex6xxx_atu.cmd_counter = BASE_CMD_NUM

    # This checks if the discovery step has been done
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

        # TCP Port to send API commands
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

    # Adding swr metric to dedicated udp port.
    if getattr(flex6xxx_atu, "is_configured", None) is None:
        send_tcp_command(f"transmit set tunepower=10")
        send_tcp_command(f"sub meter 10")
        send_tcp_command(f"client udpport {SWR_R_UDP_PORT}")

        flex6xxx_atu.is_configured = True

    try:
        print("atu: Starting atu sequence...")
        send_tcp_command(f"atu start")

        # Wait 15s for the wc of tunning time
        time.sleep(15)
        print("atu: Tuning successfully completed.")

        swr = swr_read_value(tune_tx_power)

    except (socket.error, socket.timeout, BrokenPipeError) as e:
        print(f"atu: Connection error: {e}")

        try: # Close the broken connection
            flex6xxx_atu.tcp_socket.close()
        except:
            pass
        flex6xxx_atu.tcp_socket = None
        raise RuntimeError(f"atu: Connection failed: {e}")

    return swr

def no_atu():
    return 0

