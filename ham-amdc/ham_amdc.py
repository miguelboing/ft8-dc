import numpy as np
import toml

from transmission.radio_control.radio_control import RadioControl
from wsjtx_server.wsjtx_server import WSJTXUDPServer
from dataset.dataset import DecodeDataset
from transmission.modulation.modulatior import FT8Modulator

class HamAMDC():
    def __init__(self):
        # Read the config file
        with open('config.toml', 'r') as f:
            self.config = toml.load(f)

        print(self.config)

        # Initialize the radio
        self.radio = RadioControl(port=self.config['general_config']['cat_tcp_server'] + ':' + str(self.config['general_config']['cat_tcp_port']))

        # Initialize the UDP Server
        self.wsjtx = WSJTXUDPServer(ip=self.config['general_config']['wsjtx_udp_server'], port=self.config['general_config']['wsjtx_udp_port'])

        # Initialize the FT8 Modulator
        self.modulator = FT8Modulator(sample_rate=self.config['sample_rate'])

        for iteration_set in self.config['iteration_sets']:
            self.__interpret_iteration_set(iteration_set)

    def __interpret_iteration_set(self, itset):
        for i in range(itset['n_iterations']): #This will run n_iterations times the iteration
            # Setting radio configurations
            self.radio.set_tx_power(itset['tx_power'])
            self.radio.set_mode(mode='USB', passband=itset['passband'])
            self.radio.set_if_frequency(itset['freq_band'])

            # Create the signal to be transmitted
            signals = [self.modulator.create_signal('CQ', itset['callsign'], itset['locator'], itset['frequency'], 0.0),]
            samples = self.modulator.generate_msg_samples(signals, filename="", norm_factor=0.89, dtype=np.float32)

            # Initialize the Receiver DF and PSK Reporter HTTP Server
            decode_dataset = DecodeDataset(itset['callsign'])

            # Program starts after collecting status info
            _, pkt = self.wsjtx.receive_pkt({'StatusPacket'})
            decode_dataset.set_status_info(pkt) # Updating status information

            # TODO Listening time

            # TODO Transmission

            # TODO GET PSK Reporter data

            # TODO Store everything and compress it





