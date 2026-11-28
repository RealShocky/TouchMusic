import numpy as np
import pytest
import soundfile as sf
from touchmusic.alignment import align_recording, mix_stems


def test_delayed_vocal_is_restored_to_capture_time(tmp_path):
    wet = tmp_path / 'wet.wav'
    provenance = tmp_path / 'frames.i64'
    output = tmp_path / 'aligned.wav'
    sf.write(wet, [0, 0, .1, .2, 0, .4], 48000, subtype='FLOAT')
    np.array([-1, -1, 100, 101, -1, 103], dtype='<i8').tofile(provenance)
    report = align_recording(wet, provenance, output, recording_start_frame=100, block_frames=2)
    actual, rate = sf.read(output)
    np.testing.assert_allclose(actual, [.1, .2, 0, .4, 0, 0], atol=1e-6)
    assert rate == 48000 and report['aligned_frames'] == 3


def test_alignment_preserves_large_absolute_frame_precision(tmp_path):
    wet, mapping, output = (tmp_path / name for name in ('wet.wav', 'frames.i64', 'out.wav'))
    start = 2 ** 35
    sf.write(wet, [.1, .2, .3, .4], 48000, subtype='FLOAT')
    np.array([start - 1, start, start + 2, start + 100], dtype='<i8').tofile(mapping)
    align_recording(wet, mapping, output, recording_start_frame=start)
    np.testing.assert_allclose(sf.read(output)[0], [.2, 0, .3, 0], atol=1e-6)


def test_invalid_mapping_does_not_replace_existing_output(tmp_path):
    wet, mapping, output = (tmp_path / name for name in ('wet.wav', 'frames.i64', 'out.wav'))
    sf.write(wet, [.1, .2], 48000)
    np.array([0], dtype='<i8').tofile(mapping)
    output.write_bytes(b'preserved')
    with pytest.raises(ValueError, match='length'):
        align_recording(wet, mapping, output)
    assert output.read_bytes() == b'preserved'


def test_mix_aligns_tracks_at_zero_and_limits_sum(tmp_path):
    one, two, output = (tmp_path / name for name in ('one.wav', 'two.wav', 'mix.wav'))
    sf.write(one, [.1, .2], 48000, subtype='FLOAT')
    sf.write(two, [.2, .3, .4], 48000, subtype='FLOAT')
    mix_stems([one, two], output, master_gain=.5, block_frames=2)
    np.testing.assert_allclose(sf.read(output)[0], np.tanh(np.array([.3, .5, .4]) * .5), atol=1e-6)
