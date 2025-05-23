import os
import sys
import pathlib

sys.path.append(str(pathlib.Path(os.path.realpath(__file__)).parents[1]))

from dataset.dataset import DecodeDataset
from wsjtx_server.wsjtx_server import WSJTXUDPServer

import signal

def main():

    # Program starts after collecting status info
    _, pkt = server.receive_pkt({'StatusPacket'})
    output.set_status_info(pkt)

    print("Starting to collect samples...")

    while(True):
        # Hook that reads only the wanted packets
        pkt_type, pkt = server.receive_pkt({'DecodePacket', 'StatusPacket'})
        if (pkt_type == 'StatusPacket'):
            # Update internal values
            output.set_status_info(pkt)

        elif (pkt_type == 'DecodePacket'):
            output.add_new_sample(pkt)


def exit_program(sig, frame):
    print("\nSafely exiting the application...")
    output.save_csv()
    #TODO: Close port properly

    sys.exit(0)

if __name__ == '__main__':

    output = DecodeDataset()
    server = WSJTXUDPServer()

    signal.signal(signal.SIGINT, exit_program)

    main()

