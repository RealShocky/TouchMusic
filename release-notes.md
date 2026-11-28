# TouchMusic 0.1.0

First public release of the standalone Windows vocal and gesture instrument.

- Reference-import player with waveform, zoom, and draggable 1–8 second voice selection.
- Live pitch correction, vocal effects, local Seed-VC character conversion, and chord pad.
- Four-track looper with tap tempo, metronome, and beat/bar scheduling.
- Gesture-to-MIDI CC, notes, and chords for FL Studio and other DAWs.
- Portable skits, WAV stems, and automatic vocal alignment.
- Installable Python wheel and command-line launcher.

## Download choices

- **TouchMusic-0.1.0-Windows-Setup.zip** is the full source setup folder. Install 64-bit Python 3.11 and Git, extract it, run Setup.cmd, then Launch.cmd. Setup downloads dependencies and the optional singing runtime.
- **touchmusic-0.1.0-py3-none-any.whl** installs with Python 3.11 using pip. Run touchmusic to launch the desktop app and touchmusic --setup-ai to install the optional singing engine.
- **touchmusic-0.1.0.tar.gz** is the Python source distribution.
- **SHA256SUMS.txt** provides SHA-256 checksums.

Bring your own reference audio. Personal voices, recordings, model weights, and caches are excluded.

On Windows, create a virtual MIDI port in loopMIDI and enable it in FL Studio. In TouchMusic, open MIDI / FL, connect that port, then map gestures to MIDI CC, notes, or a chord. MIDI transports control messages. Use the documented audio route to send vocals into FL Studio.

PyPI publication requires a trusted publisher configured by the PyPI project owner. Until published there, install the wheel from this release.
