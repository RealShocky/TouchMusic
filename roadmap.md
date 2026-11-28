# TouchMusic roadmap

TouchMusic is a standalone vocal performance instrument with gesture control and an emerging FL Studio connection. This roadmap tracks the next work and the live checks needed to validate it.

## Current baseline

Version 0.1.0 is published on GitHub Releases and PyPI.

- Standalone desktop effects, pitch correction, voice references, and local AI conversion.
- Reference-import player with waveform, zoom, and draggable 1-8 second selection.
- Four loop tracks with beat/bar scheduling, tap tempo, metronome, and take replacement undo.
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
| 4 | Gesture calibration and precision | Calibrated movement range, adjustable sensitivity, dead zones, pose timing, and a visible parameter/action overlay | Deliberate gestures work consistently while small incidental movement avoids unwanted changes |
| 5 | Performance UI | Large active voice, key, chord and recording displays, loop progress indicators, compact mode, and clear advanced controls | Essential performance controls stay visible at supported screen sizes and normal Windows scaling |
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

These are proposed additions that can be developed and verified independently of FL Studio.

| Priority | Candidate | Intended result |
| --- | --- | --- |
| 1 | Reference quality assistant | Flag silence and clipping, suggest candidate vocal sections, and let the user audition and choose them |
| 2 | Looper overdubbing | Add another layer to a playing loop with layer undo/redo and controlled feedback |
| 3 | Count-in and fixed-bar capture | One- or two-bar count-in and automatic capture lengths of 1, 2, 4, or 8 bars |
| 4 | Crash recovery | Recover completed loops and the last usable skit after an unexpected exit |
| 5 | Setlists | Recall per-song backing, key, tempo, voices, chords, and gesture assignments in performance order |
| 6 | Clearer vocal controls | Show bypass reasons, provide direct tuning strength/speed access, and audition dry versus processed sound |
| 7 | Loop seam treatment | Optional short crossfades to reduce clicks at loop boundaries while preserving the chosen loop length |

The suggested first standalone increment is reference quality feedback plus count-in and fixed-bar capture. Both extend controls already used during import and looping.

## Later exploration

- A TouchMusic VST3 bridge with host automation and tempo synchronization.
- Separate vocal, loop, and backing outputs where the selected audio driver supports them.
- More expressive chord voicings, chord progressions, and held-note MIDI performance.
- Optional vocal separation before creating a reference from a mixed song.

Each release should update its version, notes, compatibility information, and verification results. Features needing a live DAW or device check stay pending until that check is recorded.

