# TouchMusic authoritative roadmap

Updated 2026-11-28. This is the single requirements and delivery tracker. It supersedes the earlier overlapping roadmap sections and external AI recommendations. Supporting documents contain evidence and design, not independent feature promises.

## Status and evidence rules

- **Planned**: accepted, with no completed implementation yet.
- **In Progress**: development started; the complete acceptance gate has not passed.
- **Implemented**: code exists; verification is incomplete.
- **Verified**: the explicitly named automated or manual check passed. This never implies unperformed hardware or DAW validation.
- **Blocked**: an identified dependency prevents the next required check. Record the dependency and unblock condition.

Priority P0 is stability and compatibility, P1 is production functionality, P2 is expansion. Windows x64 is the supported platform. Python portability does not establish macOS/Linux support.

Current automated checkpoint: **121 Python tests**, **94 native SDK checks across two bridges**, actual native host/control transport, package metadata and installed GUI/worker startup passed. [Evidence](docs/verification/development-checks.json). These are software checks, not microphone/camera/DAW validation.

The published baseline is **v0.4.0**. **v0.5.0 is in development, not released or production certified.** The ten requested v0.5.0 capabilities below are the release scope. A partial implementation does not satisfy that release gate.

## v0.5.0 delivery scope

| ID | Priority | Requirement | Status | Dependencies and acceptance gate |
| --- | --- | --- | --- | --- |
| V50-01 | P0 | Isolated VST3 effect hosting | In Progress | Owned child process, bounded IPC/queues, watchdog, delayed dry fallback, explicit restart and transactional load implemented. Automated termination/timeout tests pass. Finish lifecycle/long-session stress checks and recovery UX. A process boundary is not a malware sandbox. |
| V50-02 | P0 | Plugin Center discovery and management | In Progress | Metadata-only discovery of standard/user folders, manual scan/load, binary-identity cache and failed-scan quarantine implemented. Complete asynchronous rack load and scan invalidation/lifecycle tests. |
| V50-03 | P1 | Curated catalog and official downloads | In Progress | Fifteen publisher entries, license labels, official links and checksum-pinned TDR Nova 2.2.3, SnapTune 2.4.0 and LyraTune 0.6.7 archive staging implemented. Review/version-pin further downloads individually. Never equate freeware with redistribution rights. |
| V50-04 | P0 | Compatibility scanner | In Progress | Separate-process load, 100-block stereo/finite-output probe, default impulse onset, parameter readback, binary SHA-256 and JSON reports implemented. Add multiple rates/block sizes, pluginval integration and sustained automation stress. Impulse onset is not declared plugin latency or hardware round trip. |
| V50-05 | P1 | Native plugin editor interfaces | Implemented | Actual Pedalboard show_editor runs on the plugin worker main thread. Audio must be stopped, UI remains responsive, exposed parameters synchronize on close. Broker routing tested; actual vendor editor opening/closing remains unverified. Opaque state persistence is a separate dependency. |
| V50-06 | P0 | Stereo audio engine | In Progress | External stereo FX survive through hardware callback and new stereo performance/stem WAVs; mono processing API and legacy loops remain compatible. Stereo regression test passes. Stereo backing/reference/loop assets and full project migration remain planned. |
| V50-07 | P1 | Gesture Learn | Implemented | Select effect parameter/knob and move a hand axis. Deliberate dominant motion binds height, horizontal position or spread, with timeout/cancel and disarmed performance. Pure and UI regression tests pass; physical webcam validation remains pending. |
| V50-08 | P1 | Full DAW AI audio bridge | In Progress | Native Audio Bridge plus opt-in 48 kHz stereo receiver implemented. Actual host returned 90 blocks matching standalone DSP; 47 SDK checks passed. The existing control bridge is preserved. Transport delay is 4096 frames; full AI/FX compensation, offline rendering, additional rates and actual FL/real-model checks remain pending. |
| V50-09 | P1 | Isolated VST3 instruments | In Progress | Separate stereo synth worker, timestamped MIDI, bounded notes, retrigger-safe release, panic, gesture notes/chords/knobs, explicit restore and recording stem implemented. Automated MIDI/backend tests pass. Surge XT 1.3.4 generated finite stereo over 70 paced blocks with zero worker errors/fallback. The normalized adapter is pinned to Pedalboard 0.9.26; vendor/editor/physical/DAW checks remain distinct. |
| V50-10 | P1 | Motion Score | In Progress | Beat-based movement/action recording, event editing/deletion, JSON import/export, explicit replay and optional saved-performance data implemented. Automated event/tempo/persistence tests pass. Current playback uses the 100 ms UI timer; sample-accurate scheduling, visual envelope editing and DAW automation capture remain planned. |

### Dependency order

1. Preserve v0.4.0 behavior and saved content; establish repeatable tests and benchmarks.
2. Complete isolated effect lifecycle, stereo rendering, scanner and diagnostic evidence.
3. Complete Plugin Center workflows, native editor state and Gesture Learn usability.
4. Add the isolated instrument bus and robust MIDI/note scheduling.
5. Add the bidirectional DAW audio bridge using the stabilized stereo/sample provenance model.
6. Move Motion Score playback onto a deterministic scheduler, then extend editing and DAW recording.
7. Run compatibility, soak, package and hardware/DAW gates before publishing v0.5.0.

## Preserved baseline and regression contract

| ID | Capability | Status | Evidence / limits |
| --- | --- | --- | --- |
| B01 | Standalone vocal effects, pitch correction, key/scale/chord targets, Natural/Tight/Hard presets, formant/vibrato controls | Verified | Existing automated suite retained. Live sound quality is a listening test. |
| B02 | Local Seed-VC character conversion and voice switching | Implemented | Existing conversion/provenance tests retained; references are user-owned assets. GPU throughput and voice similarity need model/hardware-specific measurements. |
| B03 | Import player with waveform, zoom, draggable 1-8 second reference selection, audition and quality suggestions | Verified | Existing picker/quality tests. Suggestions use level/silence heuristics, not vocal separation. |
| B04 | Four 120-second loop tracks, level/mute/restart, overdub, four undo states/redo, feedback, edge fades | Verified | Existing audio/looper behavior tests. Legacy captured loops stay mono. |
| B05 | Beat/bar scheduling, count-in, fixed-bar capture, tap tempo, 4/4 metronome | Verified | Sample-clock tests. Existing loops retain recorded speed after tempo changes. |
| B06 | Reverse, half/double speed and eighth-note stutter | Verified | Automated loop tests; varispeed changes pitch. Current exports preserve the original clip, not playback tricks. |
| B07 | Finger counts/fists/pinch, continuous axes, calibration, smoothing, dead zones, hold timing, rehearsal, freeze | Verified | Mapper/precision tests. Physical camera usability is a separate check. |
| B08 | Five voice slots, eight macro slots, scenes, stage view, emergency mute | Verified | Existing macro/stage/UI tests. Macro recursion is rejected. |
| B09 | Portable skits, WAV stems, aligned export, recovery/history and ordered setlists | Verified | Existing project/recovery/alignment tests. Recovery preserves completed assets, not an active take or undo history. |
| B10 | MIDI CC/notes/chords, channel/velocity, timed note release and panic | Verified | Mock-port behavior tests. Physical MIDI routing remains unverified. |
| B11 | Studio workspaces/menu bar, guided standalone setup, profiles, diagnostics, output test | Verified | Qt/diagnostic tests. A test tone is not a measured loopback calibration. |
| B12 | Voice comparison lab with shared phrase, A/B references/quality, preview, metrics and WAV export | Verified | Automated audition tests. GPU listening comparison remains pending. |
| B13 | Native Windows VST3 control bridge, ten automation controls, tempo/PPQ and backing transport chase | Verified | v0.4.0: 47 SDK validator tests plus real Pedalboard hosting, passthrough and UDP automation. Live FL testing pending; DAW audio is unchanged in this bridge. |
| B14 | Saved plugin order, bypass, normalized parameters and eight gesture knob bindings | Verified | Existing rack tests, pending-review restore, plus new isolated facade tests. Native opaque state is not yet persisted. |

## Remaining integration and production work

| ID | Priority | Requirement | Status | Completion gate |
| --- | --- | --- | --- | --- |
| P01 | P0 | Backward compatibility and explicit session migrations | In Progress | Old v1 skits/presets/mappings load without native auto-load or score auto-play. Add checked migrations and real archived fixtures before changing loop/assets schemas. |
| P02 | P0 | Plugin opaque state/presets | Planned | Capture bounded native state only in isolated workers, store content-addressed blobs, round-trip portable projects and verify checksums. Preserve normalized settings fallback. |
| P03 | P0 | Single-instance session ownership | Planned | Prevent concurrent recovery/settings writers and provide deliberate handoff. |
| P04 | P0 | Device hotplug and unavailable-device recovery | Planned | Explain missing devices; avoid silently opening an unintended mic/output; recover after disconnect/reconnect. |
| P05 | P0 | Soak tests and fault injection | In Progress | Worker termination/watchdog tests exist. Add worker restart/editor/AI stress, queue pressure, 60-minute performance and resource leak checks. |
| P06 | P1 | Plugin latency compensation | Planned | Separate declared plugin delay, worker buffering, converter delay and driver delay. Compensate parallel/stem paths and react safely to latency changes. V50-04 onset probe is not full PDC. |
| P07 | P1 | Recording/round-trip calibration | Planned | Measure routing and AI delay with a reference; save offsets and verify transient alignment tolerance. |
| P08 | P1 | DAW connection wizard | In Progress | Standalone profiles/meters/test tone exist. Add MIDI receive verification, route round trip and active DAW status. |
| P09 | P1 | FL Studio controller profile | Planned | Controller script for transport, recording, track/mixer selection, parameters and feedback. |
| P10 | P1 | Physical FL Studio connection checks | Blocked | User uninstalled FL Studio after failure. Resume after reinstall; follow the sequence below. |
| P11 | P1 | loopMIDI and VB-CABLE guided options | Planned | Document optional routes with official links and explain when interface loopback/existing ports suffice. Never promise audio transfer over MIDI. |
| P12 | P1 | Pitch-preserving loop tempo follow | Planned | Prepare stretching outside callback; maintain beat alignment across tempo/transport changes without changing vocal pitch. |
| P13 | P1 | Separate vocal/loop/backing outputs | Planned | Driver channel mapping, explicit monitor/record buses, saved routing and verified multi-output behavior. |
| P14 | P1 | Compact/scalable performance layouts | Planned | Test supported resolutions/Windows scaling, accessible labels, keyboard navigation and essential control visibility. Current sidebar/workspaces retained. |
| P15 | P1 | Character ensemble and dialogue/duet scenes | Planned | Offline dual conversion first; independent levels/stems; measure GPU/memory before promising live two-character AI. |
| P16 | P1 | Signed installers and downloadable package release | In Progress | Existing setup ZIP, wheel, sdist, hashes, GitHub release and PyPI trusted publishing retained. Add signing/provenance and clean-install verification. No v0.5.0 release before its gates. |
| P17 | P1 | macOS/Linux | Planned | Camera/audio backends, singing runtime, native host, packaging and platform CI/hardware evidence. Catalog portability is not app support. |
| P18 | P2 | Parallel effects chains and send/return buses | Planned | Depend on stereo buses and PDC; bounded mixing, headroom and state persistence. |
| P19 | P2 | Plugin marketplace / guided installations | Planned | Extend curated catalog, official/version-pinned assets, license review, integrity/provenance, manual confirmation of external installers. Community catalogs are references, not trusted executable sources. |
| P20 | P2 | AI-assisted vocal FX selection / stage crew assistant | Planned | Local constrained suggestions for clipping, routes and recipes; user explicitly applies changes. No unreviewed downloads or opaque automation. |
| P21 | P2 | Gesture-controlled modular synthesizer | Planned | Build on V50-09 and validated Cardinal/Surge support; presets, modulation and panic behavior. |
| P22 | P2 | Chord voicings, progressions and held-note performance | Planned | Explicit note lifetimes, voice leading and host/motion scheduling. |
| P23 | P2 | Vocal separation for mixed-song references | Planned | Optional model, quality preview, resource/license checks and fallback to user selection. |
| P24 | P2 | Gapless song transitions | Planned | Explicit backing/loop carryover and safe reference/plugin preloading. |
| P25 | P2 | Character stage directions | Planned | Hand zones, dialogue/duet scenes and separate character stems; consolidate with P15 rather than duplicate an ensemble engine. |
| P26 | P2 | Shadow rehearsal | Planned | Replay tracking signals with intended/triggered action comparison while suppressing audio/MIDI side effects. Distinct from Motion Score performing output. |
| P27 | P2 | Latency-aware scene preparation | Planned | Prewarm next character/effects off callback and expose a measurable readiness budget. |
| P28 | P2 | Shareable performance recipes | Planned | Package mappings, macros and required effect identities without licensed binaries or private voice references. |
| P29 | P2 | Gesture grammar | Planned | Shape + movement + held sequences, explicit conflict resolution and rehearsal preview. |
| P30 | P2 | Expanded tuning/harmony plugin recipes | Planned | Benchmark SnapTune/LyraTune against built-in tuning using the same source/key/quality metrics and listening tests. Publisher latency claims are not TouchMusic measurements. |

## Plugin candidates and engineering tools

Authoritative results are in [plugin compatibility matrix](docs/PLUGIN_COMPATIBILITY.md). Exact version, binary hash, host/rate/block size, parameter, stereo, latency, editor, hardware and DAW evidence must accompany a compatibility claim. Unknown versions stay Unknown.

- Vocal candidates: SnapTune, Graillon 3, MAutoPitch, LyraTune, OpenVoxTuner, NoteForge.
- Effects: TDR Nova, TDR Kotelnikov, Valhalla Supermassive, Dragonfly Reverb, ChowMatrix, BYOD, MFreeFXBundle.
- Instruments: Surge XT 1.3.4 has a real stereo render check; Cardinal compatibility remains unverified.
- SDK/host: Steinberg VST3 SDK and Spotify Pedalboard are already used.
- Pluginval headless validation: Planned. Add a pinned validator and archived logs to CI for our bridge and an optional local validation workflow for installed effects.
- EnterOutside/vst-loader: Planned reference review; do not import code without a confirmed applicable license.
- gr8monk3ys/VSTs: Planned catalog-reference review. Independently verify every publisher URL/license/hash; do not copy claimed catalog counts or run its downloader implicitly.
- Proposed four-slot recipe: pitch correction -> dynamic EQ -> compression -> reverb/delay. It is a recipe candidate, not four certified installed effects.

## Consolidation and resolved conflicts

- Standalone plugin hosting and the DAW bridge are independent systems. V50-01 is plugin fault containment; V50-08 is audio transport. The existing control bridge remains automation-only; the separate experimental Audio Bridge implements live audio return, with full latency compensation still pending.
- Automatic discovery means finding paths without loading native code. Explicit isolated scans and reviewed restores remain required.
- A native editor is the third-party UI in its worker process. Its exposed parameter changes can persist now; complete opaque preset state is P02.
- Free download, open-source license, redistribution rights, and measured compatibility are separate properties.
- Instruments get their own MIDI/synthesis bus; they do not silently enter the vocal effect chain.
- Stereo live/output work must preserve old mono loops and archives. A schema migration and stereo asset work remain explicit.
- Motion Score records automation; shadow rehearsal diagnoses tracking without emitting performance actions.
- Gesture macros, finger mappings, precision controls, stage view and beat-synced looping already exist. Extend them without building duplicate subsystems.

## Verification and release gates

- [ ] All ten V50 requirements have implemented acceptance checks, with unperformed live checks explicitly identified.
- [ ] Retained v0.4.0 regression suite plus tests for every new subsystem and archived session fixtures.
- [ ] Worker fault/timeout/restart, state restore, note-off/panic, malformed IPC and sustained queue pressure tests.
- [ ] Versioned compatibility reports and SDK/pluginval logs; no ambiguous plugin-version claims.
- [ ] CPU, GPU, memory, callback/deadline and dropout comparison against v0.4.0 under the same scenario; see [benchmarks](docs/BENCHMARKS.md).
- [ ] Stereo playback/recording and saved-performance migration verified.
- [ ] Wheel/sdist metadata, isolated install, entry point, setup ZIP contents/hashes and native bridge validation verified.
- [ ] Actual microphone, speakers/headphones, webcam and listening quality checked on named hardware.
- [ ] Actual wet AI return, automation, transport and restart tested in named DAW/version with measured latency.
- [ ] README, release notes, architecture and technical debt reflect the exact delivered behavior.

## FL Studio hardware test sequence

Currently Blocked on reinstallation. No end-to-end FL connection is claimed.

1. Verify TouchMusic standalone mic, headphones, camera, tuning, conversion and loops.
2. Inventory audio drivers/devices and MIDI routes. Use interface loopback or existing routes when available; loopMIDI/VB-CABLE are optional missing-route solutions.
3. Send C4 and gesture chords into an FL instrument; verify channel, velocity and panic after disarm.
4. Link one FL parameter to gesture CC and verify target feedback.
5. Check native control bridge tempo, automation and stop/restart behavior.
6. Once V50-08 exists, return wet AI audio on an FL insert, record a phrase and measure input-to-output timing without duplicate monitoring/feedback.
7. Save both configurations, restart both applications, and repeat a sustained performance.

Design: [architecture](docs/ARCHITECTURE.md). Known limitations and remediation: [technical debt](docs/TECHNICAL_DEBT.md). Release history: [release notes](release-notes.md).
