import time
import numpy as np
import toml
import gzip

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
        if (self.radio = RadioControl(port=self.config['general_config']['cat_tcp_server'] + ':' + str(self.config['general_config']['cat_tcp_port']))

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

            iteration_datetime_utc = time.gmtime() # This will be used to catalogue the different iterations

            # Listening the channel for the specified time
            start_time = time.time()
            duration = itset['listening_time'] * 60  # duration in seconds

            while ((time.time() - start_time) < duration):
                print("Running loop...")
                pkt_type, pkt = wsjtx.receive_pkt({'DecodePacket', 'StatusPacket'})
                if (pkt_type == 'StatusPacket'):
                    # Update internal values
                    decode_dataset.set_status_info(pkt)

                elif (pkt_type == 'DecodePacket'):
                    decode_dataset.add_new_sample(pkt)

            # Transmission
            radio.transmit_samples(self, filename="", samples=samples, audio_device=self.config['tx_audio_channel'], sample_rate=self.config['sample_rate'])

            # Wait for PSK Reporter to update
            start_time = time.time()
            duration = 30 * 60  # duration in seconds
            print("Waiting 30 minutes to PSK Reporter to update...")
            while ((time.time() - start_time) < duration):
                pass

            # Assembling data to storage
            output = {}
            output['receive_reports'] = decode_dataset.df
            output['transmission_reports'] = decode_dataset.get_report(time=30)
            output_name = "./dataset/output/" + itset['callsign'] + "_" +
                str(iteration_datetime_utc.tm_year) +  "_" +
                str(iteration_datetime_utc.tm_mon) + "_" +
                str(iteration_datetime_utc.tm_mday) + "_" +
                str(iteration_datetime_utc.tm_hour) + "_" +
                str(iteration_datetime_utc.tm_min) + "_" +
                str(self.config['freq_band']) + "Hz_" +
                str(self.config['frequency']) + "Hz_" +
                str(self.config['tx_power']) + "W_" +
                str(self.config['listening_time'] + "min" +
                    + ".pkl.gz"

            # Store everything and compress it
            with gzip.open(output_name, 'wb') as f:
                pickle.dump(output, f)

            return 0

