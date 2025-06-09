import subprocess

class RadioControl:
    def __init__(self, m='2', port='localhost:4532', max_power_W=100):
        self.m = m
        self.port= port
        self.max_power_W = max_power_W

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




def main():
    radio = RadioControl()
    print("Hello World!")

#    print(radio.get_if_frequency())
#
#    radio.set_if_frequency(14074000)
#
#    print(radio.get_if_frequency())

    print(radio.get_tx_power())

    print(radio.set_tx_power(10))

    print(radio.get_tx_power())

#    print(radio.set_mode('USB', 2700))
#
#    print(radio.get_mode())

    return 0

if __name__ == '__main__':
    main()

# Get frequency
#result = subprocess.run(['rigctl', '-m', '2', '-r', 'localhost:4532', 'f'], capture_output=True, text=True)
#print("Frequency:", result.stdout.strip())
