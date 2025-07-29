import time
import numpy as np
import toml
import gzip
import datetime
import os
import pickle
import random

from transmission.radio_control.radio_control import RadioControl
from wsjtx_server.wsjtx_server import WSJTXUDPServer
from dataset.dataset import DecodeDataset
from transmission.modulation.modulator import FT8Modulator
import transmission.atu as atu

class FT8DC():
    def __init__(self):
        # Read the config file
        with open('config.toml', 'r') as f:
            self.config = toml.load(f)

        print(self.config)

        self.curr_freq_offset = 0

        # Initialize the radio
        self.radio = RadioControl(port=self.config['general_config']['cat_tcp_server'] + ':' + str(self.config['general_config']['cat_tcp_port']))

        # Initialize the UDP Server
        self.wsjtx = WSJTXUDPServer(ip=self.config['general_config']['wsjtx_udp_server'], port=self.config['general_config']['wsjtx_udp_port'])
        self.wsjtx.disable_socket()

        # Initialize the FT8 Modulator
        self.modulator = FT8Modulator(sample_rate=self.config['general_config']['sample_rate'])

        if (self.config['general_config']['end_behaviour'] == "stop"):
            for i, iteration_set in enumerate(self.config['iteration_sets']):
                is_last = (i == len(self.config['iteration_sets']) - 1)
                self.__interpret_iteration_set(iteration_set, is_last)

        elif (self.config['general_config']['end_behaviour'] == "loop"):
            while(True):
                for iteration_set in self.config['iteration_sets']:
                    self.__interpret_iteration_set(iteration_set, False)

    def __interpret_iteration_set(self, itset, is_last):
        for i in range(itset['n_iterations']): #This will run n_iterations times the iteration

            # If iteration_set_contais scheduled time wait for the time
            wait_for_time(itset['schedule_time'])

            print_with_time(f"Running iteration {i+1}/{itset['n_iterations']} of iteration_set {itset['iteration_set_id']}...")

            # Setting radio configurations
            self.radio.rx_mode()
            print(f"Configuring radio with TX_power={itset['tx_power']}W bandwidth={itset['passband']} Hz and central frequency={itset['freq_band']}...")
            if ((self.radio.set_tx_power(itset['tx_power']) != 0) or (self.radio.set_mode(mode='USB', passband=itset['passband']) != 0) or (self.radio.set_if_frequency(itset['freq_band']) != 0)):
                  return -1

            # ATU
            atu_handler = getattr(atu, self.config['general_config']['atu_handler'], None)

            if not callable(atu_handler): # Check if a valid function is being passed
                print("Invalid atu handler, check the atu_handler parameter.")
                exit()

            skip_iteration = False
            for attempt in range(1, self.config['general_config']['atu_max_retries'] + 1): # Tries to tune 5 times
                try:
                    atu_handler()
                    break

                except ValueError as ve:
                    print(f"Attempt {attempt} failed: {ve}")
                    if (attempt == self.config['general_config']['atu_max_retries']):
                        skip_iteration = True

            if (skip_iteration == True):
                print("Failed to tune the radio, returning...")

                exit()

            if (itset['freq_offset'] == -1): # Set a new random frequency
                self.curr_freq_offset = random.randint(500, 1500)
                print(f"Generating random frequency {self.curr_freq_offset}")

            elif (itset['freq_offset'] == 0): # Just uses the same frequency
                print(f"Using frequency from the previous iteration...")

            else:
                print(f"Changing the frequency to {itset['freq_offset']}...")
                self.curr_freq_offset = itset['freq_offset']

            # Create the signal to be transmitted
            print(f"Generating transmission signal with callsign={itset['callsign']}, locator={itset['locator']} and frequency={self.curr_freq_offset}...")
            signals = [self.modulator.create_signal('CQ', itset['callsign'], itset['locator'], self.curr_freq_offset, 0.0),]
            samples = self.modulator.generate_msg_samples(signals, filename="", norm_factor=0.89, dtype=np.float32)

            # Initialize the Receiver DF and PSK Reporter HTTP Server
            decode_dataset = DecodeDataset(itset['callsign'])

            # Program starts after collecting status info
            print_with_time("Waiting for WSJTX to start collecting data...")
            self.wsjtx.enable_socket()
            _, pkt = self.wsjtx.receive_pkt({'StatusPacket'})
            decode_dataset.set_status_info(pkt) # Updating status information

            iteration_datetime_utc = time.gmtime() # This will be used to catalogue the different iterations

            # Listening the channel for the specified time
            print_with_time(f"Listening the channel ({itset['listening_time']} minutes)...")
            start_time = time.time()
            duration = itset['listening_time'] * 60  # duration in seconds

            while ((time.time() - start_time) < duration):
                pkt_type, pkt = self.wsjtx.receive_pkt({'DecodePacket', 'StatusPacket'})
                if (pkt_type == 'StatusPacket'):
                    # Update internal values
                    decode_dataset.set_status_info(pkt)

                elif (pkt_type == 'DecodePacket'):
                    decode_dataset.add_new_sample(pkt)

            self.wsjtx.disable_socket()

            # Transmission
            print_with_time("Finished listening to the channel, scheduling transmission...")
            self.radio.transmit_samples(filename="", samples=samples, audio_device=self.config['general_config']['tx_audio_channel'], sample_rate=self.config['general_config']['sample_rate'])

            # Wait for PSK Reporter to update
            print_with_time(f"Waiting {self.config['general_config']['psk_reporter_delay']} minutes before requesting report to PSKReporter...")
            start_time = time.time()
            duration = self.config['general_config']['psk_reporter_delay'] * 60  # duration in seconds
            while ((time.time() - start_time) < duration):
                pass

            # Assembling data to storage
            output = {}
            output['receive_reports'] = decode_dataset.df
            output['transmission_reports'] = decode_dataset.get_report(time=15)

            output_name = (
                f"./dataset/output/serialized_samples/{itset['callsign']}_"
                f"{iteration_datetime_utc.tm_year}_"
                f"{iteration_datetime_utc.tm_mon}_"
                f"{iteration_datetime_utc.tm_mday}_"
                f"{iteration_datetime_utc.tm_hour}_"
                f"{iteration_datetime_utc.tm_min}_"
                f"{itset['freq_band']}Hz_"
                f"{self.curr_freq_offset}Hz_"
                f"{itset['tx_power']}W_"
                f"{itset['listening_time']}min.pkl.gz"
            )

            # Store everything and compress it
            os.makedirs(os.path.dirname("./dataset/output/serialized_samples/"), exist_ok=True)
            with gzip.open(output_name, 'wb') as f:
                pickle.dump(output, f)

            print_with_time(f"Finished iteration! Data is stored as {output_name}.")

            # Waiting time between iterations, skip this if it is the last iteraction of the last iteraction_set
            if not((is_last == True) and ((i+1) == itset['n_iterations'])):
                print_with_time(f" Waiting for {itset['waiting_time']} minutes before starting next iteration")
                start_time = time.time()
                duration = itset['waiting_time'] * 60  # duration in seconds
                while ((time.time() - start_time) < duration):
                    pass

def print_with_time(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def wait_for_time(time_string):
    if (time_string == "-1"):
        return

    now = datetime.datetime.now()

    # Define the target time
    target_time = now.replace(hour=int(time_string[:2]), minute=int(time_string[3:]), second=0, microsecond=0)

    # If the target time has already passed today, schedule for tomorrow
    if target_time < now:
        target_time += datetime.timedelta(days=1)

    # Calculate the time difference in seconds
    sleep_duration = (target_time - now).total_seconds()

    print_with_time(f"Sleeping for {sleep_duration} seconds until {target_time.strftime('%H:%M:%S')}...")

    # Sleep until the target time
    time.sleep(sleep_duration)

