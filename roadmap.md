# TouchMusic roadmap

TouchMusic is a standalone vocal performance instrument with gesture control and an emerging FL Studio connection. This roadmap tracks the next work and the live checks needed to validate it.

## Current baseline

Version 0.3.0 adds gesture precision, expanded mappings, stage view, and output diagnostics. Version 0.2.0 introduced overdubbing, timed capture, reference suggestions, recovery, and setlists.

- Standalone desktop effects, pitch correction, voice references, and local AI conversion.
- Reference-import player with waveform, zoom, and draggable 1–8 second selection.
- Four loop tracks with beat/bar scheduling, tap tempo, metronome, and overdub, undo/redo, count-in, fixed-bar capture, edge fades, and progress.
- Diatonic chord pad, chord-following harmonies, formant controls, and voice slots.
- Gesture-to-MIDI CC, notes, and chords with timed note release and all-notes-off.
- Portable skits, WAV stems, and optional aligned vocal and mix export.

Automated tests and package installation were verified during development. End-to-end FL Studio and physical MIDI/audio routing tests are pending.

## Planned integration and UI upgrades

| Priority | Work | Intended result | Completion check |
| --- | --- | --- | --- |
| 1 | Connection wizard | A guided MIDI and audio setup with test note, audio meters, saved routing profiles, and explicit connection status | A fresh setup can verify MIDI messages and an audio round trip and report a missing route clearly |
| 2 | Dedicated FL Studio controller profile | Gesture actions for transport, record, track selection, mixer controls, and plugin parameters through an FL controller script | Each action controls the intended FL function and provides feedback for the active target |
| 3 | Shared tempo and transport | Select a clock master and make TouchMusic follow FL tempo, playback, and bar position | Capture and chord changes remain aligned during sustained playback and recover correctly after stop/restart |
| Implemented in 0.3.0; live check pending | Gesture calibration and precision | Calibrated movement range, adjustable sensitivity, dead zones, pose timing, and a visible parameter/action overlay | Deliberate gestures work consistently while small incidental movement avoids unwanted changes |
| Partial in 0.3.0 | Performance UI | Large active voice, key, chord and recording displays, loop progress indicators, compact mode, and clear advanced controls | Essential performance controls stay visible at supported screen sizes and normal Windows scaling |
| 6 | Recording calibration | Measure routing and conversion delay, save a profile, and apply the measured recording offset | Recorded transients align against a reference within a measured tolerance shown to the user |

Clock synchronization must address tempo changes and the playback speed of existing loops. The current looper keeps existing clips at their recorded speed.

## FL Studio test sequence

- [ ] Confirm the current TouchMusic build opens from the existing desktop shortcut.
- [ ] Check standalone microphone, pitch correction, backing playback, loops, and voice conversion.
- [ ] Inventory available MIDI ports and audio input/output devices.
- [ ] Test MIDI C4 reaching an FL instrument through an available route.
- [ ] Link one FL knob to a gesture CC and verify the channel and controller number.
- [ ] Test gesture notes and chord actions, then disarm gestures and confirm notes stop.
- [ ] Route the wet vocal into an FL Mixer insert and record a short phrase.
- [ ] Measure audio timing and check for feedback or duplicate monitoring.
- [ ] Save the working configuration and verify it after restarting both apps.

Testing can start with the available hardware and drivers. An existing MIDI route or audio-interface loopback may provide the connection. loopMIDI and VB-CABLE are documented software options when the corresponding route is missing.

## Suggested standalone work before FL testing

The approved standalone increment is implemented in 0.2.0. Live hardware checks remain part of user testing.

| Priority | Candidate | Intended result |
| --- | --- | --- |
| Complete | Reference quality assistant | Flag silence and clipping, suggest candidate vocal sections, and let the user audition and choose them |
| Complete | Looper overdubbing | Add another layer to a playing loop with layer undo/redo and controlled feedback |
| Complete | Count-in and fixed-bar capture | One- or two-bar count-in and automatic capture lengths of 1, 2, 4, or 8 bars |
| Complete | Crash recovery | Recover completed loops and the last usable skit after an unexpected exit |
| Complete | Setlists | Recall per-song backing, key, tempo, voices, chords, and gesture assignments in performance order |
| Existing | Clearer vocal controls | Show bypass reasons, provide direct tuning strength/speed access, and audition dry versus processed sound |
| Complete | Loop seam treatment | Optional short edge fades to reduce clicks at loop boundaries while preserving the chosen loop length |

Recovery preserves completed assets, not an active take or undo history. Setlist recall stops audio and disarms gestures. Reference suggestions use level and silence heuristics, not vocal detection. Four undo states are retained per loop. Count-in clicks are monitoring-only.

## Later exploration

- A TouchMusic VST3 bridge with host automation and tempo synchronization.
- Separate vocal, loop, and backing outputs where the selected audio driver supports them.
- More expressive chord voicings, chord progressions, and held-note MIDI performance.
- Optional vocal separation before creating a reference from a mixed song.

Each release should update its version, notes, compatibility information, and verification results. Features needing a live DAW or device check stay pending until that check is recorded.

## Additional candidates after this increment

- Gapless song transitions with explicit backing/loop carryover rules.
- Per-loop pitch-preserving time stretch when the master tempo changes.
- Implemented in 0.3.0: gesture control for capture length, overdub feedback, loop-edge treatment, tempo, key, chords, and count-in.
- Recovery retention policy and a selectable backup history.
- Stage view with larger controls implemented in 0.3.0; configurable displays and further compact layouts remain candidates.

## Standalone progress in 0.3.0

- Implemented: movement calibration, deadband, smoothing, sensitivity, pose hold and pinch timing, movement freeze, action/value feedback.
- Implemented: stage view and fullscreen, emergency mute shortcut, expanded musical gesture targets and actions.
- Implemented: manual output-test tone, excluded from loop capture and recordings.
- Fixed: conflicting capture/overdub commands during a queued count-in.
- Verified: 72 automated behavior tests, desktop layout checks, and installed package startup.
- Pending: live webcam usability and speaker checks. The output-test tone is an audible playback aid, not an automated connection wizard or measured audio round trip.
- FL Studio testing is paused because the application was uninstalled after failing. Resume the existing test sequence after reinstallation. No end-to-end FL connection is claimed.
