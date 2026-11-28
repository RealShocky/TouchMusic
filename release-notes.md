# TouchMusic 0.5.0.dev3 (unreleased)

- Portable opaque native presets with bounded chunk transfer, content-addressed blobs, checksum/binary checks and transactional restore. Real Nova 2.2.3 and Surge XT 1.3.4 restoration checked; old v1/parameter-only sessions remain readable.
- Responsive background effect/instrument loading, shutdown cancellation, native editor event-close and parent-exit worker cleanup. Fixed a large-synth state-restore timeout caused by speculative parameter-name inference.
- Per-data-directory single-instance ownership and focus handoff prevent competing session writers.
- Audio sample-clock Motion Score scheduling for local DSP/loop-level/chord/note actions. UI-only actions use a 10 ms relay; native parameter changes remain worker-quantized. Bounded dense-score cancellation preserves audio processing.
- Inactive device streams stop/disarm safely; selected-device identity is checked before opening. Physical unplug/reconnect has not been tested.
- Nine rate/block cases plus parameter sweeps for actual effects. Nova/Lyra pass nine; SnapTune fails this host's 96 kHz full-block contract. Reviewed Surge XT download pin and real native-plugin CI probes added.
- 136 Python tests pass. Accelerated one-hour DSP endurance and ten real worker/state restart cycles pass with zero surviving owned workers. This is not a one-hour hardware soak.
- Paired RTX 5060 conversion benchmarks and actual native bridge GPU return recorded. The latter has 122 converter underruns, no packet gaps/dropped chunks and finite converted stereo output; no physical audio or DAW was used.

Stable public downloads remain v0.4.0. Full AI/FX delay compensation, stereo asset migration, visual Motion Score envelopes, pluginval, clean-machine/signing and combined-load hardware/listening gates remain. FL Studio testing is explicitly delegated to external testers. No production or hardware certification is claimed.

---

# TouchMusic 0.5.0.dev2 (unreleased)

- New isolated VST3 instrument bus and Instruments workspace: timed note/chord gestures, parameter knobs, level, note retrigger protection, panic, explicit saved-instrument restore and stereo instrument stem.
- New native TouchMusic Audio Bridge and DAW audio workspace: opt-in localhost stereo return through standalone DSP and the enabled converter path at 48 kHz. The existing ten-control VST3 bridge keeps its UID and behavior.
- Audio transport uses bounded queues off the native audio callback, fixed 4096-frame transport delay and delayed dry fallback. Actual native hosting returned 90 processed blocks matching standalone DSP; both native plugins passed 47 SDK validator checks each.
- Added MIDI lifecycle, native backend, bounded packet, duplicate rejection, stereo return and converter routing regressions. 121 Python tests passed.
- Version is visible in the application title. Updated package workflows build and validate both bridges, and include both in the native ZIP.

This remains a development snapshot. Full AI/FX delay compensation, fast offline return, further sample rates, vendor instrument compatibility, opaque plugin state and deterministic Motion Score scheduling are unfinished. Actual FL Studio, physical devices, editor windows and real AI-model DAW validation have not been performed. Stable public downloads remain v0.4.0.

---

# TouchMusic 0.5.0 development snapshot (unreleased)

This is **0.5.0.dev1**, the first stability increment toward the ten-feature v0.5.0 goal. It is not the complete v0.5.0 release. Stable public downloads remain v0.4.0.

- External VST3 effect processing moved to an owned child process with bounded JSON/PCM communication, watchdog, explicit restart and time-aligned dry fallback. The populated rack adds 2048 frames, approximately 42.7 ms at 48 kHz, excluding other latency.
- Plugin Center adds metadata-only discovery, custom search folders, explicit isolated scans, binary hash/version reports, quarantine and reviewed official publisher links. Pinned archive downloads include TDR Nova 2.2.3, SnapTune 2.4.0 and LyraTune 0.6.7; installation remains manual.
- Stereo external FX reach stereo device output and new performance/stem WAVs. The mono processing API and old loop assets remain compatible.
- Native editor broker opens the actual loaded plugin interface off the desktop process. Audio must be stopped. Actual vendor-window testing remains pending; exposed parameter persistence exists, opaque saved state does not.
- Gesture Learn binds a deliberate movement axis to a selected parameter with timeout, cancellation and performance disarming.
- Motion Score adds beat-based movement/pose recording, event editing/deletion, explicit replay, JSON import/export and optional saved-performance persistence. Current replay uses the 100 ms UI timer.
- Latest parameter targets are retained while a worker is busy; unchanged parameters are no longer redundantly applied every audio block.
- The authoritative roadmap consolidates all prior requirements and separates implementation from automated, listening, hardware and DAW verification. Architecture, technical debt, compatibility matrix and benchmark records are included.
- Development versions cannot automatically publish a stable GitHub/PyPI release.

Full DAW AI audio return, dedicated VST3 instrument hosting, opaque state, full stereo assets, sample-accurate Motion Score and broad plugin certification remain unfinished. Existing control bridge behavior is preserved. No microphone/camera/FL Studio validation is claimed in this snapshot.

113 Python regression tests and 47 native SDK validator checks passed. Actual native control hosting, wheel/sdist metadata, separate-target package startup, plugin child startup and setup ZIP contents were checked. Verification results and measured limitations are recorded in docs/PLUGIN_COMPATIBILITY.md and docs/BENCHMARKS.md. The v0.4.0 regression suite is retained and expanded with worker, framing, stereo, discovery, download-integrity, learning and score tests.

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
