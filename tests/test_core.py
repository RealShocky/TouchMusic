import numpy as np
import soundfile as sf
from touchmusic.library import VoiceLibrary
from touchmusic.gestures import GestureMapper
from touchmusic.audio import LoopTrack, SamplePlayer


def test_library_import_is_deduplicated_and_preserves_source(tmp_path):
    source = tmp_path / 'voice.wav'
    sf.write(source, np.sin(np.arange(48000) * .05) * .2, 48000)
    library = VoiceLibrary(tmp_path / 'library')
    first = library.import_file(source)
    second = library.import_file(source)
    assert first['id'] == second['id']
    assert len(library.voices) == 1
    assert source.exists()
    library.rename(first['id'], 'My character')
    assert VoiceLibrary(tmp_path / 'library').voices[0]['name'] == 'My character'


def test_loop_repeats_exactly_and_clear_stops():
    loop = LoopTrack(48000)
    loop.toggle()
    assert np.array_equal(loop.process(np.array([1., 2., 3.])), np.zeros(3))
    loop.toggle()
    assert np.array_equal(loop.process(np.zeros(5)), [1, 2, 3, 1, 2])
    loop.clear()
    assert not loop.process(np.ones(4)).any()


def test_player_partial_block_and_restart():
    player = SamplePlayer()
    player.load(np.array([.1, .2, .3], dtype=np.float32))
    player.playing = True
    assert np.allclose(player.read(5), [.1, .2, .3, 0, 0])
    assert not player.playing
    player.restart()
    assert np.allclose(player.read(2), [.1, .2])


def test_pinch_is_edge_triggered_and_tracking_loss_resets():
    mapper = GestureMapper()
    points = np.zeros((21, 3))
    points[9] = [0, .5, 0]
    points[8] = [.01, 0, 0]
    first = mapper.update('Right', points, now=1)
    held = mapper.update('Right', points, now=2)
    assert first['pinch'] and not held['pinch']
    mapper.lost()
    assert mapper.update('Right', points, now=3)['pinch']
