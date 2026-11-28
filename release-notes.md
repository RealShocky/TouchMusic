# TouchMusic 0.5.0 development snapshot (unreleased)

This is **0.5.0.dev1**, the first stability increment toward the ten-feature v0.5.0 goal. It is not the complete v0.5.0 release. Stable public downloads remain v0.4.0.

- External VST3 effect processing moved to an owned child process with bounded JSON/PCM communication, watchdog, explicit restart and time-aligned dry fallback. The populated rack adds 2048 frames, approximately 42.7 ms at 48 kHz, excluding other latency.
- Plugin Center adds metadata-only discovery, custom search folders, explicit isolated scans, binary hash/version reports, quarantine and reviewed official publisher links. The first pinned archive download is TDR Nova 2.2.3; installation remains manual.
- Stereo external FX reach stereo device output and new performance/stem WAVs. The mono processing API and old loop assets remain compatible.
- Native editor broker opens the actual loaded plugin interface off the desktop process. Audio must be stopped. Actual vendor-window testing remains pending; exposed parameter persistence exists, opaque saved state does not.
- Gesture Learn binds a deliberate movement axis to a selected parameter with timeout, cancellation and performance disarming.
- Motion Score adds beat-based movement/pose recording, event editing/deletion, explicit replay, JSON import/export and optional saved-performance persistence. Current replay uses the 100 ms UI timer.
- Latest parameter targets are retained while a worker is busy; unchanged parameters are no longer redundantly applied every audio block.
- The authoritative roadmap consolidates all prior requirements and separates implementation from automated, listening, hardware and DAW verification. Architecture, technical debt, compatibility matrix and benchmark records are included.
- Development versions cannot automatically publish a stable GitHub/PyPI release.

Full DAW AI audio return, dedicated VST3 instrument hosting, opaque state, full stereo assets, sample-accurate Motion Score and broad plugin certification remain unfinished. Existing control bridge behavior is preserved. No microphone/camera/FL Studio validation is claimed in this snapshot.

112 Python regression tests and 47 native SDK validator checks passed. Actual native control hosting, wheel/sdist metadata, separate-target package startup, plugin child startup and setup ZIP contents were checked. Verification results and measured limitations are recorded in docs/PLUGIN_COMPATIBILITY.md and docs/BENCHMARKS.md. The v0.4.0 regression suite is retained and expanded with worker, framing, stereo, discovery, download-integrity, learning and score tests.

---

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
