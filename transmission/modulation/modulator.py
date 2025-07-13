import numpy as np
import ft8notes.ft8 as ft8
import scipy.signal
import scipy.special
from scipy.io.wavfile import write

class FT8Modulator:
    def __init__(self, b=ft8.gaussian_bandwidth, sample_rate=12000):

        self.sample_rate = sample_rate
        self.samples_per_symbol = int(self.sample_rate / ft8.baud_rate)
        self.t = np.linspace(-1.5, 1.5, 3 * self.samples_per_symbol, endpoint=False)
        self.filtered_boxcar = self._gaussian_boxcar(ft8.gaussian_bandwidth, self.t)

    def create_signal(self, callsign_1, callsign_2, location, if_freq, t_offset):
        return (ft8.StandardMessage(ft8.Callsign(callsign_1), ft8.Callsign(callsign_2), ft8.LocationReport(location)), if_freq, t_offset)

    def _gaussian_boxcar(self, b, t):
        """Function to calculate gaussian filtered boxcar pulse waveform to perform M-GFSK modulation.
        The boxcar function is assumed to be centered around t = 0 with width 1.0 and amplitude 1.0.
        This function will return the value of the gaussian filtered boxcar at time t.
        The parameter t can be a scalar or a numpy array.
        The parameter b controls the bandwidth of the gaussian filter."""
        c = b * np.pi * np.sqrt(2.0 / np.log(2.0))
        return 0.5 * (scipy.special.erf(c * (t + 0.5)) - scipy.special.erf(c * (t - 0.5)))

    def _modulation_waveform(self, symbols):
        """Generate a modulation waveform from a list of symbols using the provided pulse waveform
        The pulse waveform must have a length that is equal to three symbol periods."""

        assert self.filtered_boxcar.size == 3 * self.samples_per_symbol
        w = np.zeros((len(symbols) + 4) * self.samples_per_symbol)
        s = 0

        # Pad start and end of waveform with first and last symbol respectively
        for symbol in ([symbols[0]] + symbols + [symbols[-1]]):
            w[s: s + self.filtered_boxcar.size] += symbol * self.filtered_boxcar
            s += self.samples_per_symbol

        return w[self.samples_per_symbol * 2: self.samples_per_symbol * (2 + len(symbols))]
    def _mgfsk(self, if_freq, offset, symbols):
        """Synthesize M-GFSK modulated carrier

        if_freq - Carrier frequency in Hz
        offset - Time offset in seconds
        symbols - Encoded message symbols
        pulse - Symbol pulse waveform
        sample_rate - Sample rate in Hz"""

        # Derived constants
        two_pi = 2.0 * np.pi
        total_samples = ft8.tr_period * self.sample_rate
        cycle = 2.0 * np.pi / self.sample_rate
        dphase_symbol = cycle * ft8.freq_shift
        dphase_if_freq = cycle * if_freq

        # Calculate signal phases
        phases = np.zeros(total_samples)
        phase = 0
        sample_init = int(self.sample_rate * (ft8.start_delay + offset))
        sample_end = sample_init + self.samples_per_symbol * len(symbols)
        sample = sample_init # Preserving the init value for amp. shaping
        mod_wave = self._modulation_waveform(symbols)
        dphases = mod_wave * dphase_symbol + dphase_if_freq
        for dphase in dphases:
            phase += dphase
            phase %= two_pi
            phases[sample] = phase
            sample += 1

        # Getting complex signal
        signal_array = np.exp(1j * phases)

        # Amplitude Shaping is 0.5 * [1 - cos(8pi * t / T)]
        #Generate the CosineRamp
        amplitude_ramp = np.linspace(0, 1, num=int(self.samples_per_symbol/8))

        signal_array[sample_init:sample_init + int(self.samples_per_symbol/8)] *= amplitude_ramp
        signal_array[sample_end - len(amplitude_ramp):sample_end] *= amplitude_ramp[::-1]

        signal_array[0:sample_init] = 0
        signal_array[sample_end:] = 0

        return signal_array

    def generate_msg_samples(self, signals, filename="", norm_factor=1000, dtype=np.int16):
        """Simulate a passband containing multiple FT8 signals and noise"""
        # signals is a list of signal tuples
        # filename is the desired name for the WAV file - samples are in a 16-bit signed mono format
        # noise_power is the noise power in dB - note that noise is not added when noise_power is zero.
        # sample_rate is the desired sample rate for the WAV file

        # Derived constants
        total_samples = self.sample_rate * ft8.tr_period

        samples = np.empty((total_samples,), dtype=dtype)
        for message, if_freq, offset in signals:

            # Encode the message
            symbols = message.encode()

            # Add signal into the mix
            samples = (norm_factor * np.real(self._mgfsk(if_freq, offset, symbols))).astype(dtype)

            t = np.linspace(0, ft8.tr_period, num=len(samples))

        # Saving in to wav format
        if (filename == ""):
            return samples.astype(dtype)
        else:
            write(filename, self.sample_rate, samples.astype(dtype))

        return 0
