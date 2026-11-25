"""Pitch analysis, note selection, and a lightweight live chord pad."""
import numpy as np
from scipy.fft import irfft, rfft

NOTES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
DEGREES = ('I', 'II', 'III', 'IV', 'V', 'VI', 'VII')
SCALES = {'Major': (0, 2, 4, 5, 7, 9, 11), 'Minor': (0, 2, 3, 5, 7, 8, 10)}


def chord_notes(key, scale, degree):
    intervals = SCALES[scale]
    return tuple(key + intervals[i % 7] + 12 * (i // 7)
                 for i in (degree, degree + 2, degree + 4))


def chord_name(notes):
    suffix = {(4, 7): '', (3, 7): 'm', (3, 6): 'dim'}
    return NOTES[notes[0] % 12] + suffix[(notes[1] - notes[0], notes[2] - notes[0])]


def nearest_note(midi, notes):
    return int(round(midi + min(((note - midi + 6) % 12 - 6 for note in notes), key=abs)))


class PitchDetector:
    def __init__(self, rate):
        self.rate = rate
        self.history = np.zeros(3072, np.float32)
        self.lags = np.arange(min(len(self.history) - 2, rate // 50 + 2))
        self.low_lag = max(2, rate // 1600 - 1)
        self.reset()

    def reset(self):
        self.history.fill(0)
        self.samples = 0
        self.pitch = None

    def process(self, block, limits=(72, 1100)):
        if not len(block):
            return self.pitch
        if np.max(np.abs(block)) < .003:
            self.reset()
            return None
        size = min(len(block), len(self.history))
        self.history[:-size] = self.history[size:]
        self.history[-size:] = block[-size:]
        self.samples += size
        if self.samples < 1024:
            return self.pitch
        self.samples = 0
        waveform = self.history - self.history.mean()
        spectrum = rfft(waveform, 8192)
        correlation = irfft(spectrum * spectrum.conj())
        minimum, maximum = limits
        # Check short lags outside the chosen range to reject subharmonics
        # of a tone just above the range.
        low = self.low_lag
        high = min(len(self.lags) - 1, self.rate // minimum + 2)
        lags = self.lags[:high + 1]
        energy = np.r_[0., np.cumsum(waveform * waveform)]
        normalizer = np.sqrt(np.maximum(1e-9, energy[len(waveform) - lags] * (energy[-1] - energy[lags])))
        values = correlation[:high + 1] / normalizer
        peaks = np.flatnonzero((values[low:high] > values[low-1:high-1]) &
                               (values[low:high] >= values[low+1:high+1])) + low
        self.pitch = None
        if len(peaks):
            threshold = max(.76, .91 * float(values[peaks].max()))
            candidates = peaks[values[peaks] >= threshold]
            if len(candidates):
                lag = candidates[0]
                left, center, right = values[lag-1:lag+2]
                correction = .5 * (left - right) / (left - 2 * center + right)
                pitch = self.rate / (lag + correction)
                if minimum <= pitch <= maximum:
                    self.pitch = pitch
        return self.pitch


class ChordPad:
    def __init__(self, rate):
        self.rate = rate
        midi = np.arange(48, 78)
        self.speed = 2 * np.pi * 440 * 2 ** ((midi - 69) / 12) / rate
        self.phase = np.zeros(len(midi))
        self.level = np.zeros(len(midi))

    def process(self, count, notes, level):
        targets = np.zeros(len(self.level))
        if level:
            targets[list(notes)] = level * .15
        decay = np.exp(-np.arange(1, count + 1) / (self.rate * .025))
        signal = np.zeros(count, np.float32)
        for i in np.flatnonzero((targets > 0) | (self.level > .00001)):
            angle = self.phase[i] + self.speed[i] * np.arange(count)
            envelope = targets[i] + (self.level[i] - targets[i]) * decay
            signal += envelope * (.85 * np.sin(angle) + .15 * np.sin(2 * angle))
            self.level[i] = envelope[-1]
        self.phase = (self.phase + self.speed * count) % (2 * np.pi)
        return signal
