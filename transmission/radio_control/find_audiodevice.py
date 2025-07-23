#import sounddevice as sd
#
#print("Available audio devices:\n")
#for i, dev in enumerate(sd.query_devices()):
#    print(f"{i}: {dev['name']} - Input Channels: {dev['max_input_channels']}, Output Channels: {dev['max_output_channels']}")

import pyaudio
import wave

# Step 1: List all output devices
p = pyaudio.PyAudio()
print("Available output devices:\n")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxOutputChannels'] > 0:
        print(f"{i}: {info['name']}")
