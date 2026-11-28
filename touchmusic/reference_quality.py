"""Streaming level heuristics for reference audio, without vocal classification."""
from dataclasses import dataclass

import numpy as np
import soundfile as sf


@dataclass(frozen=True)
class SelectionQuality:
    rms_db: float
    silent_fraction: float
    clipped_fraction: float

    def text(self):
        level = f'{self.rms_db:.1f} dBFS' if np.isfinite(self.rms_db) else 'silent'
        messages = []
        if self.silent_fraction > .2:
            messages.append('Choose a section with less silence.')
        elif self.rms_db < -35:
            messages.append('This section is quiet.')
        if self.clipped_fraction > .001:
            messages.append('Possible clipping. Try another section.')
        return (f'Level {level} · silence {self.silent_fraction:.0%} · '
                f'near-full-scale samples {self.clipped_fraction:.1%}. ' + ' '.join(messages)).strip()


class ReferenceQuality:
    def __init__(self, rate, frames, bin_frames, energy, clipped, count):
        self.rate, self.frames, self.bin_frames = rate, frames, bin_frames
        self.duration = frames / rate
        self.count = count
        self.energy = energy
        self.clipped = clipped
        self.silent = energy / np.maximum(count, 1) < 10 ** (-45 / 10)
        self.candidates = self._candidates()

    def report(self, start, end):
        first = max(0, min(len(self.count) - 1, int(start * self.rate / self.bin_frames)))
        last = max(first + 1, min(len(self.count), int(np.ceil(end * self.rate / self.bin_frames))))
        frame_starts = np.arange(first, last) * self.bin_frames
        frame_ends = np.minimum(self.frames, frame_starts + self.bin_frames)
        overlap = np.maximum(0, np.minimum(frame_ends, end * self.rate) -
                             np.maximum(frame_starts, start * self.rate))
        fractions = overlap / np.maximum(1, frame_ends - frame_starts)
        weights = self.count[first:last] * fractions
        total = max(1, weights.sum())
        mean_square = np.sum(self.energy[first:last] * fractions) / total
        return SelectionQuality(float(10 * np.log10(max(1e-12, mean_square))),
                                float(np.sum(weights * self.silent[first:last]) / total),
                                float(np.sum(self.clipped[first:last] * fractions) / total))

    def _candidates(self):
        # Rank sustained sections by level, quiet-frame coverage, and overloads.
        energy = np.r_[0., np.cumsum(self.energy)]
        clipped = np.r_[0., np.cumsum(self.clipped)]
        count = np.r_[0., np.cumsum(self.count)]
        silent = np.r_[0., np.cumsum(self.count * self.silent)]
        seconds_per_bin = self.bin_frames / self.rate
        usable = (~self.silent) & (self.clipped / np.maximum(self.count, 1) < .01)
        boundaries = np.flatnonzero(np.diff(np.r_[False, usable, False]))
        proposals = []
        for seconds in sorted({min(self.duration, value) for value in (1, 2, 4, 6, 8)}):
            width = min(len(self.count), max(1, round(seconds / seconds_per_bin)))
            starts = np.arange(0, len(self.count) - width + 1, max(1, round(.25 / seconds_per_bin)))
            starts = np.unique(np.clip(np.r_[starts, boundaries, boundaries - width],
                                       0, len(self.count) - width))
            ends = starts + width
            totals = np.maximum(1, count[ends] - count[starts])
            levels = 10 * np.log10(np.maximum(1e-12, (energy[ends] - energy[starts]) / totals))
            quiet = (silent[ends] - silent[starts]) / totals
            overload = (clipped[ends] - clipped[starts]) / totals
            scores = -np.abs(levels + 20) - quiet * 60 - overload * 500 + seconds * .8
            eligible = (quiet < .2) & (levels > -40) & (overload < .01)
            for index in np.flatnonzero(eligible)[np.argsort(scores[eligible])[-20:]]:
                start = starts[index] * seconds_per_bin
                end = min(self.duration, start + width * seconds_per_bin)
                if end - start >= 1 - 1e-9:
                    proposals.append((float(scores[index]), start, min(end, start + 8)))
        chosen = []
        for _, start, end in sorted(proposals, reverse=True):
            if all(min(end, other_end) - max(start, other_start) < .5 * min(end-start, other_end-other_start)
                   for other_start, other_end in chosen):
                chosen.append((start, end))
            if len(chosen) == 8:
                break
        return chosen


def analyze_reference(path, interrupted=lambda: False):
    """Return waveform and quality using bounded reads and compact summaries."""
    with sf.SoundFile(str(path)) as source:
        rate, frames = source.samplerate, source.frames
        if frames < rate:
            raise ValueError('Choose a recording at least one second long.')
        peak_width = max(1, int(np.ceil(frames / 4000)))
        bin_width = max(1, round(rate * .02), int(np.ceil(frames / 100000)))
        peak_count = int(np.ceil(frames / peak_width))
        bin_count = int(np.ceil(frames / bin_width))
        peaks = np.zeros((peak_count, 2), np.float32)
        energy, clipped, count = (np.zeros(bin_count) for _ in range(3))
        position = 0
        for block in source.blocks(blocksize=32768, dtype='float32', always_2d=True):
            if interrupted():
                return None
            if not np.isfinite(block).all():
                raise ValueError('This audio contains invalid samples.')
            mono = block.mean(axis=1)
            for width, is_peak in ((peak_width, True), (bin_width, False)):
                offset = 0
                while offset < len(block):
                    absolute = position + offset
                    index = absolute // width
                    end = min(len(block), offset + width - absolute % width)
                    if is_peak:
                        section = mono[offset:end]
                        peaks[index, 0] = min(peaks[index, 0], section.min())
                        peaks[index, 1] = max(peaks[index, 1], section.max())
                    else:
                        section = block[offset:end]
                        energy[index] += np.sum(section.astype(np.float64) ** 2)
                        clipped[index] += np.count_nonzero(np.abs(section) >= .999)
                        count[index] += section.size
                    offset = end
            position += len(block)
        quality = ReferenceQuality(rate, frames, bin_width, energy, clipped, count)
        return quality.duration, peaks, quality
