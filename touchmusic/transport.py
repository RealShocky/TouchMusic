"""Sample-clock scheduling and a headphone-only metronome."""
import math

import numpy as np

QUANTIZE = ('Immediate', 'Next beat', 'Next bar')
BEATS_PER_BAR = 4


class BeatClock:
    def __init__(self, rate):
        self.rate = rate
        self.frame = self.origin = 0
        self.bpm = 120
        self.mode = 'Immediate'
        self.pending = {}
        time = np.arange(round(rate * .025)) / rate
        self.clicks = tuple((.16 * np.sin(2 * np.pi * hz * time) * np.exp(-220 * time)).astype(np.float32)
                            for hz in (1500, 1050))

    @property
    def period(self):
        return self.rate * 60 / self.bpm

    @property
    def beat(self):
        return math.floor((self.frame - self.origin + .5) / self.period)

    def set_tempo(self, bpm, mode):
        if bpm == self.bpm and mode == self.mode:
            return
        if bpm != self.bpm:
            position = (self.frame - self.origin) / self.period
            self.bpm = bpm
            self.origin = round(self.frame - position * self.period)
        self.mode = mode
        for key, (_, command) in self.pending.items():
            self.pending[key] = self.boundary(mode), command

    def boundary(self, mode):
        if mode == 'Immediate':
            return self.frame
        period = self.period * (BEATS_PER_BAR if mode == 'Next bar' else 1)
        step = math.ceil((self.frame - self.origin - .5) / period)
        return self.origin + round(step * period)

    def click(self, count):
        output = np.zeros(count, np.float32)
        first = self.beat
        for beat in range(first, first + int(count / self.period) + 2):
            offset = self.origin + round(beat * self.period) - self.frame
            sample = self.clicks[bool(beat % BEATS_PER_BAR)]
            start = max(0, offset)
            end = min(count, offset + len(sample))
            if start < end:
                output[start:end] += sample[start-offset:end-offset]
        return output
