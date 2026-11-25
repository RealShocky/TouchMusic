"""Pitch tracking, chord harmonies, and streaming vocal formant processing."""
from math import exp, log2

import numpy as np
from scipy.fft import irfft, rfft

from .music import PitchDetector


VOCAL_RANGES = {
    'Wide': (72, 1100),
    'Low': (50, 330),
    'Mid': (85, 660),
    'High': (150, 1100),
}
HARMONY_MODES = ('Fixed fifth', 'Chord above', 'Chord below')


class VocalAnalysis:
    def __init__(self, rate):
        self.rate = rate
        self.detector = PitchDetector(rate)
        self.reset()

    def reset(self):
        self.detector.reset()
        self.pitch = self.center = None
        self.vocal_range = None

    def process(self, audio, vocal_range):
        if vocal_range != self.vocal_range:
            self.reset()
            self.vocal_range = vocal_range
        self.pitch = self.detector.process(audio, VOCAL_RANGES[vocal_range])
        if self.pitch is None:
            self.center = None
            return None
        note = 69 + 12 * log2(self.pitch / 440)
        if self.center is None or abs(note - self.center) > 1.5:
            self.center = note
        else:
            tracking = 1 - exp(-len(audio) / (self.rate * .10))
            self.center += (note - self.center) * tracking
        return note

    def correction(self, note, target_midi, vibrato):
        return target_midi - note + (note - self.center) * vibrato


def harmony_shift(note, chord, mode):
    if mode == 'Fixed fifth':
        return 7
    if note is None:
        return None
    lead = round(note)
    direction = 1 if mode == 'Chord above' else -1
    chord_tones = {tone % 12 for tone in chord}
    # Use a third to fifth where the current triad allows it.
    for interval in range(3, 13):
        shift = interval * direction
        if (lead + shift) % 12 in chord_tones:
            return shift
    return None


class FormantShifter:
    """Translate the smoothed spectral envelope while preserving harmonic spacing."""

    def __init__(self, rate):
        self.size = 2048
        self.hop = self.size // 4
        self.window = np.sin(np.pi * (np.arange(self.size) + .5) / self.size).astype(np.float32)
        self.bins = np.arange(self.size // 2 + 1)
        frequencies = self.bins * (rate / self.size)
        self.gain_weight = np.clip((frequencies - 100) / 150, 0, 1) * np.clip(
            (12000 - frequencies) / 4000, 0, 1)
        quefrency = np.minimum(np.arange(self.size), np.arange(self.size, 0, -1)) / rate
        self.lifter = np.clip((.0015 - quefrency) / .00075, 0, 1).astype(np.float32)
        self.input = np.zeros(self.size, dtype=np.float32)
        self.overlap = np.zeros_like(self.input)
        self.output = np.zeros(self.hop, dtype=np.float32)
        self.reset()

    def reset(self):
        self.input.fill(0)
        self.overlap.fill(0)
        self.output.fill(0)
        self.pending = 0

    def process(self, audio, semitones):
        rendered = np.empty(len(audio), dtype=np.float32)
        start = 0
        while start < len(audio):
            count = min(len(audio) - start, self.hop - self.pending)
            stop = start + count
            incoming = slice(self.size - self.hop + self.pending,
                             self.size - self.hop + self.pending + count)
            outgoing = slice(self.pending, self.pending + count)
            self.input[incoming] = audio[start:stop]
            rendered[start:stop] = self.output[outgoing]
            self.pending += count
            if self.pending == self.hop:
                self._render_frame(semitones)
                self.pending = 0
            start = stop
        return rendered

    def _render_frame(self, semitones):
        spectrum = rfft(self.input * self.window)
        if semitones:
            magnitude = np.abs(spectrum)
            log_magnitude = np.log(np.maximum(magnitude, max(1e-6, magnitude.max() * .001)))
            cepstrum = irfft(log_magnitude) * self.lifter
            envelope = rfft(cepstrum).real
            source_bins = self.bins * 2 ** (-semitones / 12)
            shifted = np.interp(source_bins, self.bins, envelope)
            spectrum *= np.exp(np.clip(shifted - envelope, -1.8, 1.8) * self.gain_weight)
        self.overlap += irfft(spectrum) * self.window * .5
        self.output[:] = self.overlap[:self.hop]
        self.overlap[:-self.hop] = self.overlap[self.hop:]
        self.overlap[-self.hop:] = 0
        self.input[:-self.hop] = self.input[self.hop:]
