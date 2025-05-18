import socket
import sys
import pywsjtx_packets.wsjtx_packets

class UDPServer:
    def __init__(ip = '', port = 2237, bufferSize = 1024):
        self.ip = ip
        self.port = port
        self.bufferSize = bufferSize

        # Create socket
        UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

        # Enable multiple connections
        UDPServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind the address and IP
        UDPServerSocket.bind((ip, port))

        print("UDP server up and listening")

    def __recv_pkt(self):
        pkt, addr_port = UDPServerSocket.recvfrom(bufferSize)
        return pywsjtx_packets.wsjtx_packets.WSJTXPacketClassFactory.from_udp_packet(addr_port, pkt)

    def receive_pkt(self, types): # Types is a list of strings of the relevant types, the rest will be ignored

        set_types = set()

        for type_name in types:
            match type_name:
                case 'HeartBeatPacket':
                    set_types.add(pywsjtx_packets.wsjtx_packets.HeartBeatPacket.TYPE_VALUE)
                case 'StatusPacket':
                    set_types.add(pywsjtx_packets.wsjtx_packets.StatusPacket.TYPE_VALUE)
                case 'DecodePacket':
                    set_types.add(pywsjtx_packets.wsjtx_packets.DecodePacket.TYPE_VALUE)
                case 'ClearPacket':
                    set_types.add(pywsjtx_packets.wsjtx_packets.ClearPacket.TYPE_VALUE)
                case 'ReplyPacket':
                    set_types.add(pywsjtx_packets.wsjtx_packets.ReplyPacket.TYPE_VALUE)
                case 'QSOLoggedPacket':
                    set_types.add(pywsjtx_packets.wsjtx_packets.QSOLoggedPacket.TYPE_VALUE)
                case 'ClosePacket':
                    set_types.add(pywsjtx_packets.wsjtx_packets.ClosePacket.TYPE_VALUE)
                case 'ReplayPacket':
                    set_types.add(pywsjtx_packets.wsjtx_packets.ReplayPacket.TYPE_VALUE)
                case 'HaltTxPacket':
                    set_types.add(pywsjtx_packets.wsjtx_packets.HaltTxPacket.TYPE_VALUE)
                case 'FreeTextPacket':
                    set_types.add(pywsjtx_packets.wsjtx_packets.FreeTextPacket.TYPE_VALUE)
                case 'WSPRDecodePacket':
                    set_types.add(pywsjtx_packets.wsjtx_packets.WSPRDecodePacket.TYPE_VALUE)
                case _:
                    print(f"Unknown packet type: {type_name}")

        # Will only leave here after a valid packet was received
        do{
            pkt = self.__recv_pkt()
        }
        while(pkt.TYPE_VALUE not in set_types)

        return pkt.to_dict()

