import numpy as np

from touchmusic.music import chord_notes
from touchmusic.vocal import FormantShifter, VocalAnalysis, harmony_shift


RATE = 48000
BLOCK = 512


def tone(frequency):
    clock = np.arange(BLOCK * 16) / RATE
    return (.2 * np.sin(2 * np.pi * frequency * clock)).astype(np.float32)


def track(analysis, source, vocal_range):
    notes = [analysis.process(source[i:i + BLOCK], vocal_range)
             for i in range(0, len(source), BLOCK)]
    return notes[-1]


def test_vocal_ranges_extend_low_tracking_and_exclude_high_input():
    analysis = VocalAnalysis(RATE)
    assert track(analysis, tone(63), 'Wide') is None
    assert track(analysis, tone(63), 'Low') is not None
    assert abs(analysis.pitch - 63) < 1
    assert track(analysis, tone(440), 'Low') is None
    assert track(analysis, tone(440), 'High') is not None
    assert abs(analysis.pitch - 440) < 1
    assert track(analysis, tone(1200), 'Wide') is None


def test_vibrato_preservation_retains_modulation_around_the_target_note():
    analysis = VocalAnalysis(RATE)
    clock = np.arange(2 * RATE) / RATE
    source_notes = 68.7 + .38 * np.sin(2 * np.pi * 5 * clock)
    frequencies = 440 * 2 ** ((source_notes - 69) / 12)
    source = (.2 * np.sin(np.cumsum(2 * np.pi * frequencies / RATE))).astype(np.float32)
    natural, corrected = [], []
    for offset in range(0, len(source), BLOCK):
        note = analysis.process(source[offset:offset + BLOCK], 'Wide')
        if note is not None and offset >= RATE:
            corrected.append(note + analysis.correction(note, 69, 0))
            natural.append(note + analysis.correction(note, 69, 1))
    np.testing.assert_allclose(corrected, 69)
    assert abs(np.mean(natural) - 69) < .05
    assert np.ptp(natural) > .40
    assert analysis.process(np.zeros(BLOCK), 'Wide') is None
    assert analysis.center is None


def test_chord_harmony_follows_chord_and_direction():
    tonic = chord_notes(0, 'Major', 0)
    dominant = chord_notes(0, 'Major', 4)
    assert harmony_shift(60.1, tonic, 'Chord above') == 4
    assert harmony_shift(60.1, dominant, 'Chord above') == 7
    assert harmony_shift(59.9, tonic, 'Chord below') == -5
    assert harmony_shift(59.9, dominant, 'Chord below') == -5
    assert harmony_shift(None, dominant, 'Chord above') is None
    assert harmony_shift(None, tonic, 'Fixed fifth') == 7


def test_formant_shifting_moves_resonance_without_transposing_pitch():
    processor = FormantShifter(RATE)
    clock = np.arange(RATE * 2) / RATE
    source = .55 * np.sin(2 * np.pi * 125 * clock)
    for frequency in range(250, 2500, 125):
        amplitude = .18 / (1 + ((frequency - 1000) / 160) ** 2)
        source += amplitude * np.sin(2 * np.pi * frequency * clock)
    source = source.astype(np.float32)

    def spectrum(audio):
        return np.abs(np.fft.rfft(audio[-RATE:] * np.hanning(RATE)))

    harmonics = np.arange(500, 1600, 125)
    for semitones, direction in ((4, 1), (-4, -1)):
        processor.reset()
        rendered = np.concatenate([processor.process(source[i:i + BLOCK], semitones)
                                   for i in range(0, len(source), BLOCK)])
        bands = spectrum(rendered)
        assert bands.argmax() == 125
        centroid = np.average(harmonics, weights=bands[harmonics] ** 2)
        assert direction * (centroid - 1000) > 125


def test_formant_neutral_reconstructs_irregular_blocks_with_constant_latency():
    processor = FormantShifter(RATE)
    source = np.random.default_rng(13).normal(size=8192).astype(np.float32)
    rendered = np.concatenate([processor.process(source[i:i + 311], 0.)
                               for i in range(0, len(source), 311)])
    np.testing.assert_allclose(rendered[processor.size:], source[:-processor.size], atol=1e-6)
