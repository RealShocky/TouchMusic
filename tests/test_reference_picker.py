import numpy as np
import pytest
import soundfile as sf

from touchmusic.library import VoiceLibrary


def test_import_uses_the_selected_section_and_preserves_source(tmp_path):
    source = tmp_path / 'song.wav'
    rate = 24000
    audio = np.r_[np.full(rate * 10, .1), np.full(rate * 8, .4), np.full(rate * 2, .2)]
    sf.write(source, audio, rate, subtype='FLOAT')
    library = VoiceLibrary(tmp_path / 'voices')
    voice = library.import_file(source, 'Chorus', start_seconds=10, duration_seconds=8)
    selected, sample_rate = sf.read(library.path(voice))
    assert sample_rate == rate and len(selected) == rate * 8
    np.testing.assert_allclose(selected, .4, atol=1e-4)
    assert voice['name'] == 'Chorus'
    assert sf.info(source).frames == len(audio)


def test_segment_is_bounded_and_duplicate_selection_is_reused(tmp_path):
    source = tmp_path / 'song.wav'
    sf.write(source, np.sin(np.arange(48000 * 12) * .03) * .2, 48000)
    library = VoiceLibrary(tmp_path / 'voices')
    voice = library.import_file(source, start_seconds=3, duration_seconds=8)
    same = library.import_file(source, start_seconds=3, duration_seconds=8)
    assert voice['id'] == same['id']
    assert len(library.voices) == 1
    for start, duration in [(-1, 8), (0, 9), (11.5, 1), (0, .5), (float('nan'), 2)]:
        with pytest.raises(ValueError):
            library.import_file(source, start_seconds=start, duration_seconds=duration)


def test_fractional_selection_end_and_mp3(tmp_path):
    rate = 44100
    source = tmp_path / 'song.mp3'
    sf.write(source, np.sin(np.arange(rate * 12) * .04) * .2, rate, format='MP3')
    library = VoiceLibrary(tmp_path / 'voices')
    voice = library.import_file(source, start_seconds=4., duration_seconds=8.000000000000002)
    assert sf.info(library.path(voice)).frames == 24000 * 8


def test_dragged_reference_and_cancel_through_import_button(tmp_path, monkeypatch):
    import os
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    from PySide6.QtCore import QTimer
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QDialog
    from touchmusic import ui
    from touchmusic.reference_picker import ReferencePicker

    app = QApplication.instance() or QApplication([])
    source = tmp_path / 'long.wav'
    sf.write(source, np.r_[np.zeros(24000 * 10), np.full(24000 * 8, .4)], 24000)
    library = VoiceLibrary(tmp_path / 'voices')
    monkeypatch.setattr(ui, 'DATA', tmp_path)
    monkeypatch.setattr(ui, 'VoiceLibrary', lambda: library)
    monkeypatch.setattr(ui.QFileDialog, 'getOpenFileNames', lambda *args: ([str(source)], ''))
    original_exec = ReferencePicker.exec
    cancel = False

    def choose_section(dialog):
        def choose_when_loaded():
            if not dialog.ready:
                QTimer.singleShot(10, choose_when_loaded)
                return
            assert dialog.use_button.isEnabled()
            assert dialog.waveform.peaks.shape[0] <= 4000
            dialog.waveform.set_selection(10, 18)
            assert dialog.start.value() == 10
            assert dialog.length.value() == 8
            dialog.name.setText('Selected chorus')
            dialog.reject() if cancel else dialog.accept()
        QTimer.singleShot(10, choose_when_loaded)
        QTimer.singleShot(8000, dialog.reject)
        return original_exec(dialog)

    monkeypatch.setattr(ReferencePicker, 'exec', choose_section)
    window = ui.MainWindow()
    try:
        window.import_voice()
        assert len(library.voices) == 1
        assert window.current_voice()['name'] == 'Selected chorus'
        np.testing.assert_allclose(sf.read(library.path(library.voices[0]))[0], .4, atol=1e-4)
        cancel = True
        window.import_voice()
        assert len(library.voices) == 1
    finally:
        window.close()
        app.processEvents()


def test_waveform_drag_handles_and_zoom():
    import os
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from touchmusic.waveform import Waveform

    app = QApplication.instance() or QApplication([])
    wave = Waveform()
    wave.resize(824, 200)
    wave.set_audio(120, np.zeros((4000, 2), np.float32))
    wave.set_selection(4, 12)
    wave.show()
    app.processEvents()
    point = lambda seconds: QPoint(round(wave.x_at(seconds)), 80)
    QTest.mousePress(wave, Qt.LeftButton, pos=point(8))
    QTest.mouseMove(wave, point(10))
    QTest.mouseRelease(wave, Qt.LeftButton, pos=point(10))
    assert abs(wave.start - 6) < .05
    assert abs(wave.end - 14) < .05
    QTest.mousePress(wave, Qt.LeftButton, pos=point(wave.end))
    QTest.mouseMove(wave, point(12))
    QTest.mouseRelease(wave, Qt.LeftButton, pos=point(12))
    assert abs(wave.end - 12) < .05
    wave.zoom(.5)
    assert wave.view_seconds == 10
    wave.scroll_to(110)
    assert wave.view_start == 110
    wave.set_selection(119.5, 120.5)
    assert wave.start == 119 and wave.end == 120
    wave.close()
