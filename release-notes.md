# TouchMusic 0.4.0

A studio-oriented standalone update with a native VST3 control bridge.

- Menu bar and ten sidebar workspaces for performance, voice comparison, FX, songs, gestures, macros, chords, audio setup, MIDI and VST3 integration.
- Guided audio setup, saved routing profiles, readable runtime health, and local diagnostics export.
- Eight gesture macro slots with ordered actions and nested-macro protection.
- Voice comparison lab: the same source phrase through A/B reference and quality settings, with preview and WAV export.
- Four-slot VST3 vocal effect rack with eight gesture parameter bindings, bypass/order controls and parameter snapshots.
- Reverse, half/double-speed and eighth-note stutter loop actions. Varispeed changes pitch.
- Latest recovery plus up to five prior snapshots, with a 256 MiB budget for prior backups.
- Windows x64 native VST3 control bridge with ten automation parameters, tempo/PPQ following and optional backing-track transport chase.

## Downloads

- Windows Setup ZIP: Python 3.11 (64-bit) and Git are required. Extract, run Setup.cmd once, then Launch.cmd.
- Separate Control Bridge Windows ZIP: extract the complete VST3 bundle into a folder your DAW scans. See its README.
- Python wheel/source: `py -3.11 -m pip install --upgrade touchmusic`, then run `touchmusic`. Optional singing engine: `touchmusic --setup-ai`.

The native bridge passes DAW audio through unchanged. It sends automation/timing to the standalone app; wet AI audio requires its own route. Soft synchronization is not sample-accurate cross-application sync. Third-party effects run in-process, use generic controls, and fold stereo output to the mono vocal bus. Native plugin crash isolation and full DAW audio transport remain roadmap work. No third-party effect binaries or personal voices/models are redistributed.

85 Python behavior tests and 47 VST3 validator tests passed. Actual host loading, unchanged native audio passthrough, native-to-Python automation and TDR Nova 2.2.3 processing/parameter control were checked. Live FL Studio, microphone/speaker timing, GPU comparison quality and long-session tests remain pending. Supported release: Windows x64. macOS/Linux support is planned.
