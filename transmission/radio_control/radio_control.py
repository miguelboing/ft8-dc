import subprocess

class RadioControl:
    def __init__(self, m='2', port='localhost:4532'):
        self.m = m
        self.port= port

    def get_if_frequency(self):
        return subprocess.run(['rigctl', '-m', '2', '-r', 'localhost:4532', 'f'], capture_output=True, text=True).stdout.strip()

    def set_if_frequency(self, frequency=14074000):
        subprocess.run(['rigctl', '-m', '2', '-r', 'localhost:4532', 'F', str(frequency)])

        cur_freq = self.get_if_frequency()

        if (cur_freq != str(frequency)):
            print("Failed to set the frequency currently set to: {result}")
            return -1

        return 0

def main():
    radio = RadioControl()
    print("Hello World!")
    print(radio.get_if_frequency())

    radio.set_if_frequency(14075000)

    print(radio.get_if_frequency())

    return 0

if __name__ == '__main__':
    main()

# Get frequency
#result = subprocess.run(['rigctl', '-m', '2', '-r', 'localhost:4532', 'f'], capture_output=True, text=True)
#print("Frequency:", result.stdout.strip())
