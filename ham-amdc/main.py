import wsjtx_server.wsjtx_socket
import dataset.dataset

import signal

def main():

    dataset = DecodeDataset()
    server = WSJTXUDPServer()

    while(True):
        dataset.add_new_sample(server.receive_pkt({'DecodePacket'}))


def exit_program():
    dataset.save_csv()

    exit (0)

if __name__ == '__main__':

    signal.signal(signal.SIGINT, exit_program)

    main()

