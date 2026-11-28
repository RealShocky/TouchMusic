import os

import numpy as np
import soundfile as sf

from touchmusic.reference_quality import analyze_reference

_APP = None


def test_suggestions_avoid_silence_and_clipping(tmp_path):
    rate = 24000
    clock = np.arange(rate * 8) / rate
    clean = .18 * np.sin(2 * np.pi * 220 * clock)
    source = tmp_path / 'sections.wav'
    sf.write(source, np.r_[np.zeros(rate * 8), clean, np.ones(rate * 8)], rate, subtype='FLOAT')
    duration, peaks, quality = analyze_reference(source)
    assert duration == 24
    assert len(peaks) <= 4000
    assert quality.candidates
    start, end = quality.candidates[0]
    assert 8 <= start < end <= 16
    assert 1 <= end - start <= 8
    report = quality.report(start, end)
    assert -20 < report.rms_db < -15
    assert report.silent_fraction == 0
    assert report.clipped_fraction == 0
    assert quality.report(0, 4).silent_fraction == 1
    clipped = quality.report(18, 23)
    assert clipped.clipped_fraction == 1
    assert 'Possible clipping' in clipped.text()


def test_antiphase_stereo_retains_level_and_channel_clipping(tmp_path):
    source = tmp_path / 'stereo.wav'
    signal = np.full(48000, 1., np.float32)
    sf.write(source, np.column_stack((signal, -signal)), 24000, subtype='FLOAT')
    _, _, quality = analyze_reference(source)
    report = quality.report(.01, 1.99)
    assert report.rms_db == 0
    assert report.silent_fraction == 0
    assert report.clipped_fraction == 1
    assert not quality.candidates


def test_silent_audio_has_no_suggestions_and_scan_can_cancel(tmp_path):
    source = tmp_path / 'silent.wav'
    sf.write(source, np.zeros(24000 * 5), 24000)
    _, _, quality = analyze_reference(source)
    assert not quality.candidates
    assert 'less silence' in quality.report(0, 2).text()
    assert analyze_reference(source, lambda: True) is None


def test_streaming_reads_are_bounded(tmp_path, monkeypatch):
    import touchmusic.reference_quality as module
    source = tmp_path / 'long.wav'
    sf.write(source, np.zeros(24000 * 30), 24000)
    original = module.sf.SoundFile
    blocks = []

    class ObservedFile(original):
        def blocks(self, *args, **kwargs):
            blocks.append(kwargs['blocksize'])
            yield from super().blocks(*args, **kwargs)

    monkeypatch.setattr(module.sf, 'SoundFile', ObservedFile)
    _, peaks, quality = analyze_reference(source)
    assert max(blocks) <= 32768
    assert len(peaks) <= 4000
    assert len(quality.count) <= 100000


def test_picker_suggestions_and_manual_selection_update_quality(tmp_path):
    global _APP
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication
    from touchmusic.reference_picker import ReferencePicker
    app = QApplication.instance() or QApplication([])
    _APP = app
    source = tmp_path / 'voice.wav'
    signal = .2 * np.sin(2 * np.pi * 220 * np.arange(24000 * 8) / 24000)
    sf.write(source, np.r_[np.zeros(24000 * 8), signal, np.zeros(24000 * 4), signal], 24000)
    dialog = ReferencePicker(source)
    loop = QEventLoop()
    dialog.loader.finished.connect(loop.quit)
    QTimer.singleShot(5000, loop.quit)
    try:
        loop.exec()
        app.processEvents()
        assert dialog.ready and dialog.quality is not None
        assert dialog.suggest_button.isEnabled()
        dialog.suggest_button.click()
        assert dialog.waveform.start >= 8
        assert 'silence 0%' in dialog.quality_label.text()
        dialog.waveform.set_selection(0, 4)
        assert 'less silence' in dialog.quality_label.text()
        dialog.next_button.click()
        assert dialog.waveform.start >= 8
    finally:
        dialog.reject()
        app.processEvents()
    assert not dialog.loader.isRunning()


def test_picker_cancel_during_analysis_stays_closed(tmp_path):
    global _APP
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    from PySide6.QtWidgets import QApplication
    from touchmusic.reference_picker import ReferencePicker
    app = QApplication.instance() or QApplication([])
    _APP = app
    source = tmp_path / 'cancel.wav'
    sf.write(source, np.zeros(24000 * 12), 24000)
    dialog = ReferencePicker(source)
    dialog.reject()
    app.processEvents()
    assert dialog.closing
    assert not dialog.ready
    assert not dialog.loader.isRunning()
