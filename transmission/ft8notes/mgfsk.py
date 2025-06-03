import numpy as np
import ft8
import matplotlib.pyplot as plt
import scipy.signal
import scipy.special

def gaussian_boxcar(b, t):
    """Function to calculate gaussian filtered boxcar pulse waveform to perform M-GFSK modulation.
    The boxcar function is assumed to be centered around t = 0 with width 1.0 and amplitude 1.0.
    This function will return the value of the gaussian filtered boxcar at time t.
    The parameter t can be a scalar or a numpy array.
    The parameter b controls the bandwidth of the gaussian filter."""
    c = b * np.pi * np.sqrt(2.0 / np.log(2.0))
    return 0.5 * (scipy.special.erf(c * (t + 0.5)) - scipy.special.erf(c * (t - 0.5)))

def modulation_waveform(symbols, samples_per_symbol, pulse):
    """Generate a modulation waveform from a list of symbols using the provided pulse waveform
    The pulse waveform must have a length that is equal to three symbol periods."""

    assert pulse.size == 3 * samples_per_symbol
    w = np.zeros((len(symbols) + 4) * samples_per_symbol)
    s = 0

    # Pad start and end of waveform with first and last symbol respectively
    for symbol in ([symbols[0]] + symbols + [symbols[-1]]):
        w[s: s + pulse.size] += symbol * pulse
        s += samples_per_symbol

    return w[samples_per_symbol * 2: samples_per_symbol * (2 + len(symbols))]

def mgfsk(if_freq, offset, symbols, pulse, sample_rate = 12000):
    """Synthesize M-GFSK modulated carrier

    if_freq - Carrier frequency in Hz
    offset - Time offset in seconds
    symbols - Encoded message symbols
    pulse - Symbol pulse waveform
    sample_rate - Sample rate in Hz"""

    # Derived constants
    two_pi = 2.0 * np.pi
    samples_per_symbol = int(sample_rate / ft8.baud_rate)
    total_samples = ft8.tr_period * sample_rate
    cycle = 2.0 * np.pi / sample_rate
    dphase_symbol = cycle * ft8.freq_shift
    dphase_if_freq = cycle * if_freq

    # Calculate signal phases
    phases = np.zeros(total_samples)
    phase = 0
    sample_init = int(sample_rate * (ft8.start_delay + offset))
    sample_end = sample_init + samples_per_symbol * len(symbols)
    sample = sample_init # Preserving the init value for amp. shaping
    mod_wave = modulation_waveform(symbols, samples_per_symbol, pulse)
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
    amplitude_ramp = np.linspace(0, 1,num=int(samples_per_symbol/8))

    signal_array[sample_init:sample_init + int(samples_per_symbol/8)] *= amplitude_ramp
    signal_array[sample_end - len(amplitude_ramp):sample_end] *= amplitude_ramp[::-1]

    print(signal_array)

    imag_part = np.array([y.imag for y in signal_array], dtype=np.float32)
    real_part = np.array([y.real for y in signal_array], dtype=np.float32)

    return imag_part

def main():
    symbols = [3, 1, 4, 0, 6, 5, 2, 7, 0, 2, 7, 4, 1, 3, 2, 3, 6, 4, 1, 0, 0, 7, 6, 0, 2, 4, 1, 4, 3, 5, 3, 5, 3, 2, 4, 2, 3, 1, 4, 0, 6, 5, 2, 1, 1, 6, 3, 7, 4, 6, 4, 0, 2, 7, 7, 3, 5, 6, 4, 2, 2, 5, 4, 3, 0, 0, 0, 2, 5, 3, 0, 1, 3, 1, 4, 0, 6, 5, 2]

    samples_per_symbol = 512
    bandwidth = 2.0 # FT8 uses a bandwidth that is twice the baud rate
    duration = 2.0
    symbol_count = duration * ft8.baud_rate
    samples = int(samples_per_symbol * symbol_count)

    t = np.linspace(-1.5, 1.5, 3 * samples_per_symbol, endpoint=False)
    filtered_boxcar = gaussian_boxcar(bandwidth, t)
#    plt.plot(t, filtered_boxcar)
#    plt.show()

    t = np.linspace(0, ft8.tr_period, num=samples)
    plt.plot(t, modulation_waveform(symbols, samples_per_symbol, filtered_boxcar)[:samples] ) #* ft8.freq_shift)
    plt.show()

    if_freq = 14074000
    offset = 0
    mgfsk_wave = mgfsk(if_freq, offset, symbols, filtered_boxcar, int(ft8.baud_rate * samples_per_symbol))

    t = np.linspace(0, ft8.tr_period, num=len(mgfsk_wave))
    plt.plot(t, mgfsk_wave)
    plt.show()

    return 0

if __name__ == "__main__":
    main()
