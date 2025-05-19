import os
import sys
import pathlib

sys.path.append(str(pathlib.Path(os.path.realpath(__file__)).parents[1]))

from dataset.dataset import DecodeDataset
from wsjtx_server.wsjtx_server import WSJTXUDPServer

import signal

def main():

    while(True):
        output.add_new_sample(server.receive_pkt({'DecodePacket'}))


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

