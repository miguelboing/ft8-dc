import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile

# Replace this with the path to your downloaded FT8 .wav file
wav_path = '210703_133430.wav'

# Load the audio file
sample_rate, audio_data = wavfile.read(wav_path)

# If stereo, take only one channel
if len(audio_data.shape) == 2:
    audio_data = audio_data[:, 0]

# Create time axis in seconds
time_axis = np.arange(len(audio_data)) / sample_rate

# Plotting the waveform
plt.figure(figsize=(12, 4))
plt.plot(time_axis, audio_data, linewidth=0.5)
plt.title('FT8 WAV Audio Sample')
plt.xlabel('Time [s]')
plt.ylabel('Amplitude')
plt.grid(True)
plt.tight_layout()
plt.show()
