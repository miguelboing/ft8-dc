import socket
import sys
import wsjtx_server.pywsjtx_packets.wsjtx_packets as wsjtx_packets

class WSJTXUDPServer:
    def __init__(self, ip = '', port = 2237, bufferSize = 1024):
        self.ip = ip
        self.port = port
        self.bufferSize = bufferSize

        # Create socket
        self.UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

        # Enable multiple connections
        self.UDPServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind the address and IP
        self.UDPServerSocket.bind((ip, port))

        print("UDP server up and listening")

    def __recv_pkt(self):
        pkt, addr_port = self.UDPServerSocket.recvfrom(self.bufferSize)

        return wsjtx_packets.WSJTXPacketClassFactory.from_udp_packet(addr_port, pkt)

    def receive_pkt(self, types): # Types is a list of strings of the relevant types, the rest will be ignored

        set_types = set()

        for type_name in types:
            match type_name:
                case 'HeartBeatPacket':
                    set_types.add(wsjtx_packets.HeartBeatPacket.TYPE_VALUE)
                case 'StatusPacket':
                    set_types.add(wsjtx_packets.StatusPacket.TYPE_VALUE)
                case 'DecodePacket':
                    set_types.add(wsjtx_packets.DecodePacket.TYPE_VALUE)
                case 'ClearPacket':
                    set_types.add(wsjtx_packets.ClearPacket.TYPE_VALUE)
                case 'ReplyPacket':
                    set_types.add(wsjtx_packets.ReplyPacket.TYPE_VALUE)
                case 'QSOLoggedPacket':
                    set_types.add(wsjtx_packets.QSOLoggedPacket.TYPE_VALUE)
                case 'ClosePacket':
                    set_types.add(wsjtx_packets.ClosePacket.TYPE_VALUE)
                case 'ReplayPacket':
                    set_types.add(wsjtx_packets.ReplayPacket.TYPE_VALUE)
                case 'HaltTxPacket':
                    set_types.add(wsjtx_packets.HaltTxPacket.TYPE_VALUE)
                case 'FreeTextPacket':
                    set_types.add(wsjtx_packets.FreeTextPacket.TYPE_VALUE)
                case 'WSPRDecodePacket':
                    set_types.add(wsjtx_packets.WSPRDecodePacket.TYPE_VALUE)
                case _:
                    print(f"Unknown packet type: {type_name}")

        # Will only leave here after a valid packet was received
        while(True): # This loop's purpose is to emulate a do-while loop
            pkt = self.__recv_pkt()
            if (pkt.TYPE_VALUE in set_types):
                break;
            # TODO: Add a timout for this loop

        print(pkt)

        return pkt.get_class_name(), pkt.to_dict()

