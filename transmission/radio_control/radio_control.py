import numpy as np
import subprocess

import sounddevice as sd
import soundfile as sf

import time
from datetime import datetime, timedelta, UTC

import os
import platform

if os.name == 'nt':
    # Running on windows with rigctl under wsjtx
    rigctl = 'rigctl-wsjtx'
    output_device_name = 'DAX Audio TX (FlexRadio Systems DAX TX)'
elif os.name == 'posix':
    # Running directly rigctl
    rigctl = 'rigctl'
    output_device_name = 'Flex slice A TX'

class RadioControl:
    def __init__(self, m='2', port='localhost:4532', max_power_W=100):
        self.m = m
        self.port= port
        self.max_power_W = max_power_W

        # Always start the radio in RX mode
        self.rx_mode()

    def get_if_frequency(self):
        return subprocess.run([rigctl, '-m', self.m, '-r', self.port, 'f'], capture_output=True, text=True).stdout.strip().splitlines()[-1]

    def get_mode(self):
        return subprocess.run([rigctl, '-m', self.m, '-r', self.port, 'm'], capture_output=True, text=True).stdout.strip().splitlines()[-2:]

    def get_tx_power(self):
        return round(self.max_power_W * float((subprocess.run(['rigctl-wsjtx', '-m', self.m, '-r', self.port, 'l', 'RFPOWER'], capture_output=True, text=True).stdout.strip()).splitlines()[-1]))


    def set_if_frequency(self, frequency=14074000):
        subprocess.run([rigctl, '-m', self.m, '-r', self.port, 'F', str(frequency)])

        cur_freq = self.get_if_frequency()

        if (cur_freq != str(frequency)):
            print(f"Failed to set the frequency. Currently set to: {cur_freq}, tried to set to {str(frequency)}")
            return -1

        return 0

    def set_mode(self, mode='USB', passband=-1):
        # passband is in Hz. passband = -1 for no change, passband = 0 for radio backend default (2700 for FlexRadio 6400)
        subprocess.run([rigctl, '-m', self.m, '-r', self.port, 'M', mode, str(passband)])

        cur_mode = self.get_mode()

        if  ((cur_mode[0] != mode) or (passband not in [-1, 0, int(cur_mode[1])])):
            print(f"Failed to set mode. Currently set to: {cur_mode[0]},{cur_mode[1]} tried to set to {mode}, {str(cur_mode[1])}")
            return -1
        return 0

    def rx_mode(self)
        subprocess.run([rigctl, '-m', self.m, '-r', self.port, 'T', '0'])

    def set_tx_power(self, power_W):
        if (power_W > self.max_power_W):
            print(f"Failed to change the TX power, maximum power is {self.max_power_W} but request to set power to {power_W}")
            return -1

        power = round(power_W/self.max_power_W, 2)
        subprocess.run(['rigctl-wsjtx', '-m', self.m, '-r', self.port, 'L', 'RFPOWER', str(power)])

        cur_power = self.get_tx_power()
        if (cur_power != power_W):
            print(f"Failed to change the TX power, tried to change to {power_W} ({power}), but current power is {cur_power} ({round(float(cur_power)/self.max_power_W,1)})")

            return -1

        return 0

    def wait_until_next_15s(self):
        now = datetime.now(UTC)
        # Calculate the next multiple of 15 seconds
        seconds = ((now.second // 15) + 1) * 15
        if seconds == 60:
            target = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        else:
            target = now.replace(second=seconds, microsecond=0)

        delay = (target - now).total_seconds()
        print(f"Current time : {now}")
        print(f"Waiting until: {target} (sleeping {delay:.3f} seconds)")
        time.sleep(delay)

    def transmit_samples(self, filename="", samples=None, sample_rate=None, audio_device=-1, dtype=np.float32):
        if (filename == ""):
            file_data = samples
            file_sample_rate = sample_rate
        else:
            file_data, file_sample_rate = sf.read(filename, dtype=dtype)

#        # Automatically find the index for the output_device_name
#        device_info = next(dev for dev in sd.query_devices() if output_device_name in dev['name'])

#        print(f"Selected device: {device_info['name']}")
#        print(f"Max output channels: {device_info['max_output_channels']}")

        self.wait_until_next_15s()

        # Enabling PPT fot the radio
        try:
            subprocess.run([rigctl, '-m', self.m, '-r', self.port, 'T', '3'])

            # Play audio
            sd.play(file_data, samplerate=file_sample_rate, device=audio_device, blocksize=int(0.025 * file_sample_rate), latency="low")# channels=1)
            sd.wait()

            # Disabling PPT for the radio
            subprocess.run([rigctl, '-m', self.m, '-r', self.port, 'T', '0'])
            return 0

        except Exception as e:
            subprocess.run([rigctl, '-m', self.m, '-r', self.port, 'T', '0'])
            print(f"An error occurred: {e}")
            print("Failed to transmit, returned to RX mode")

        return -1

