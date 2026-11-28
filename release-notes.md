# TouchMusic 0.3.0

More expressive standalone gesture controls and a dedicated stage view.

- Five-second movement calibration, configurable pose hold and pinch cooldown, movement smoothing, sensitivity, and deadband.
- Freeze continuous movement while keeping deliberate finger and pinch actions available.
- Gesture control for tempo, key, chords, count-in, capture length, overdub feedback, and edge fades.
- Large stage view with four loop pads, voice switching, recording, setlist navigation, and fullscreen.
- F12 emergency mute disarms gestures and releases MIDI notes while preserving running recording and arrangement.
- Monitoring-only output test tone for diagnosing silent playback.
- Capture and overdub commands cancel the same pending count-in instead of leaving conflicting queued starts.
- Precision and calibration settings persist in presets, skits, recovery, and app settings.

## Downloads

The Windows Setup ZIP requires Python 3.11 (64-bit) and Git. Extract, run Setup.cmd once, then Launch.cmd. It downloads dependencies and optional singing runtime; it is not a dependency-free executable.

Install or upgrade with `py -3.11 -m pip install --upgrade touchmusic`, then run `touchmusic`. Install the optional singing engine with `touchmusic --setup-ai`.

Personal voices, recordings, model weights, and caches are excluded. Existing loop audio does not change speed when BPM changes. Live camera, hardware-output and FL Studio validation remain pending. FL Studio testing is paused until reinstallation.

72 automated tests passed. Desktop layouts and installed-wheel startup are checked for this release.
