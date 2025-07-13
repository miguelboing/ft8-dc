import time
import numpy as np
import toml
import gzip

from transmission.radio_control.radio_control import RadioControl
from wsjtx_server.wsjtx_server import WSJTXUDPServer
from dataset.dataset import DecodeDataset
from transmission.modulation.modulator import FT8Modulator

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

        if (self.config['end_behaviour'] == "stop"):
            for iteration_set in self.config['iteration_sets']:
                self.__interpret_iteration_set(iteration_set)
            return 0
        elif (self.config['end_behaviour'] == "loop"):
            while(True):
                for iteration_set in self.config['iteration_sets']:
                    self.__interpret_iteration_set(iteration_set)
        return -1

    def __interpret_iteration_set(self, itset):
        for i in range(itset['n_iterations']): #This will run n_iterations times the iteration
            print(f"Running iteration {i} of iteration_set {itset['iteration_set_id']}...")

            # Setting radio configurations
            print(f"Configuring radio with TX_power={itset['tx_power']}W bandwidth={itset['passband']} Hz and central frequency={itset['freq_band']}...")
            if ((self.radio.set_tx_power(itset['tx_power']) != 0) or (self.radio.set_mode(mode='USB', passband=itset['passband']) != 0) or (self.radio.set_if_frequency(itset['freq_band']):
                  return -1

            # Create the signal to be transmitted
            print(f"Generating transmission signal with callsign={itset['callsign'], locator={itset['locator']} and frequency={itset['frequency']}...")
            signals = [self.modulator.create_signal('CQ', itset['callsign'], itset['locator'], itset['frequency'], 0.0),]
            samples = self.modulator.generate_msg_samples(signals, filename="", norm_factor=0.89, dtype=np.float32)

            # Initialize the Receiver DF and PSK Reporter HTTP Server
            decode_dataset = DecodeDataset(itset['callsign'])

            # Program starts after collecting status info
            print("Waiting for WSJTX to start collecting data...")
            _, pkt = self.wsjtx.receive_pkt({'StatusPacket'})
            decode_dataset.set_status_info(pkt) # Updating status information

            iteration_datetime_utc = time.gmtime() # This will be used to catalogue the different iterations

            # Listening the channel for the specified time
            print(f"Listening the channel ({itset['listening_time']} minutes)...")
            start_time = time.time()
            duration = itset['listening_time'] * 60  # duration in seconds

            while ((time.time() - start_time) < duration):
                pkt_type, pkt = wsjtx.receive_pkt({'DecodePacket', 'StatusPacket'})
                if (pkt_type == 'StatusPacket'):
                    # Update internal values
                    decode_dataset.set_status_info(pkt)

                elif (pkt_type == 'DecodePacket'):
                    decode_dataset.add_new_sample(pkt)

            # Transmission
            print("Finished listening to the channel, scheduling transmission...")
            radio.transmit_samples(self, filename="", samples=samples, audio_device=self.config['tx_audio_channel'], sample_rate=self.config['sample_rate'])

            # Wait for PSK Reporter to update
            print(f"Waiting {self.config['general_config']['psk_reporter_delay']}")
            start_time = time.time()
            duration = self.config['general_config']['psk_reporter_delay'] * 60  # duration in seconds
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

            print(f"Finished iteration! Data is stored as {output_name}.")

            # Store everything and compress it
            with gzip.open(output_name, 'wb') as f:
                pickle.dump(output, f)

            return 0

