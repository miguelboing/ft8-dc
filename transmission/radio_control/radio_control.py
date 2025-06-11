import subprocess

import sounddevice as sd
import soundfile as sf

import sched
import time
from datetime import datetime, timedelta, UTC

class RadioControl:
    def __init__(self, m='2', port='localhost:4532', max_power_W=100):
        self.m = m
        self.port= port
        self.max_power_W = max_power_W

        self.s = sched.scheduler(time.time, time.sleep)

    def get_if_frequency(self):
        return subprocess.run(['rigctl', '-m', self.m, '-r', self.port, 'f'], capture_output=True, text=True).stdout.strip()

    def get_mode(self):
        return subprocess.run(['rigctl', '-m', self.m, '-r', self.port, 'm'], capture_output=True, text=True).stdout.strip()

    def get_tx_power(self):
        return round(self.max_power_W * float(subprocess.run(['rigctl', '-m', self.m, '-r', self.port, 'l', 'RFPOWER'], capture_output=True, text=True).stdout.strip()))

    def set_if_frequency(self, frequency=14074000):
        subprocess.run(['rigctl', '-m', self.m, '-r', self.port, 'F', str(frequency)])

        cur_freq = self.get_if_frequency()

        if (cur_freq != str(frequency)):
            print("Failed to set the frequency. Currently set to: {result}")
            return -1
        return 0

    def set_mode(self, mode='USB', passband=-1):
        # passband is in Hz. passband = -1 for no change, passband = 0 for radio backend default (2700 for FlexRadio 6400)
        subprocess.run(['rigctl', '-m', self.m, '-r', self.port, 'M', mode, str(passband)])

        cur_mode = self.get_mode()

        if (cur_mode != mode + '\n' + str(passband)):
            print(f"Failed to set mode. Currently set to: {cur_mode}, but and tried to set to {mode}")
            return -1
        return 0

    def set_tx_power(self, power_W):
        if (power_W > self.max_power_W):
            print(f"Failed to change the TX power, maximum power is {self.max_power_W} but request to set power to {power_W}")
            return -1

        power = round(power_W/self.max_power_W, 1)
        subprocess.run(['rigctl', '-m', self.m, '-r', self.port, 'L', 'RFPOWER', str(power)])

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


    def transmit_audio_file(self, filename):
        data, sample_rate = sf.read(filename)
        print(data)
        print(sample_rate)
#        print(sd.query_devices())
#
#        # Automatically find the index for the 'nDAX' output device
        output_device_name = 'nDAX'
        device_info = next(dev for dev in sd.query_devices() if output_device_name in dev['name'])

#       now = datetime.utcnow()
        self.wait_until_next_15s()
#        print("Finishrf")
#       # Enabling PPT fot the radio
        subprocess.run(['rigctl', '-m', self.m, '-r', self.port, 'T', '3'])
#
#        # Play audio
        sd.play(data, samplerate=samplerate, device=device_info['index'])
        sd.wait()
#
#       # Disabling PPT for the radio
        subprocess.run(['rigctl', '-m', self.m, '-r', self.port, 'T', '0'])
        return 0

def main():
    radio = RadioControl()
    print("Hello World!")

    print(radio.set_tx_power(10))

    radio.transmit_audio_file("../audio_files/ft8_audio.wav")

    return 0

if __name__ == '__main__':
    main()


# Get frequency
#result = subprocess.run(['rigctl', '-m', '2', '-r', 'localhost:4532', 'f'], capture_output=True, text=True)
#print("Frequency:", result.stdout.strip())
