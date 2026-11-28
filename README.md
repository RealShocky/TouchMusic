# TouchMusic

> Development checkout: **0.5.0.dev2**, not a finished v0.5.0 release. Published stable downloads remain v0.4.0. The [authoritative roadmap](roadmap.md) tracks every requested feature, dependency and verification gate.


![Windows](https://img.shields.io/badge/platform-Windows_10%2F11-0078D4)
![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Standalone](https://img.shields.io/badge/app-standalone-559C80)
![Local AI](https://img.shields.io/badge/voice_conversion-local-7958A6)
![Status](https://img.shields.io/badge/status-experimental-D59C37)
[![Latest release](https://img.shields.io/github/v/release/RealShocky/TouchMusic)](https://github.com/RealShocky/TouchMusic/releases/latest)
[![PyPI](https://img.shields.io/pypi/v/touchmusic)](https://pypi.org/project/touchmusic/)

**Perform live with your voice, switch characters with hand gestures, and build layered loops.**

TouchMusic combines microphone effects, pitch correction, webcam hand tracking, reference-based AI voice conversion, a chord pad, a four-track looper, and WAV recording in a standalone Windows desktop app.

See [roadmap.md](roadmap.md) for planned upgrades, standalone feature ideas, and the FL Studio test sequence.

[Quick start](#quick-start) · [Auto-Tune](#pitch-correction) · [Looper](#four-track-looper) · [Gestures](#gesture-control) · [Troubleshooting](#troubleshooting)

## Features

| Area | Controls |
| --- | --- |
| Voice performance | Live microphone monitoring, backing tracks, vocal effects, master mute |
| Pitch correction | Auto-Tune switch, Natural / Tight / Hard presets, key and scale, chromatic or chord targets, pitch meter |
| Character voices | Import, preview, and rename your own references; five gesture voice slots |
| AI conversion | Local pitch-conditioned Seed-VC; Live and Studio modes; compute and dropped-chunk status |
| Gestures | Finger counts, fists, thumb-index pinch, hand height, horizontal movement, thumb-index spread |
| Looper | Four tracks, 120 seconds per track, level, mute, restart, overdub, undo/redo, edge fades, progress, WAV export |
| Musical timing | Tap tempo, 40–240 BPM, 4/4 metronome, immediate / next beat / next bar changes, count-in and fixed-bar capture |
| Vocal character | Chord-following harmonies, vocal-range selection, vibrato preservation, formant shifting |
| Sessions | Portable skits with completed loops, backing, voice references, settings, scenes, mappings, crash recovery, ordered setlists |
| Recording | Performance WAV, separate stems, optional automatic vocal and mix alignment |
| MIDI output | Gesture CC, notes, chords, velocity, channel, timed note release, all-notes-off |

## Download or install

Download the Windows setup ZIP from [Releases](https://github.com/RealShocky/TouchMusic/releases/latest), extract it, run Setup.cmd once, then Launch.cmd. Python 3.11 and Git are required. Setup downloads the runtime.

The release also includes an installable wheel. With Python 3.11, install it directly:

    py -3.11 -m pip install https://github.com/RealShocky/TouchMusic/releases/download/v0.4.0/touchmusic-0.4.0-py3-none-any.whl
    touchmusic

For character conversion, run the optional engine setup once:

    touchmusic --setup-ai

Use **touchmusic --setup-ai --cpu** for CPU wheels. The standard setup selects NVIDIA CUDA wheels.

Install from [PyPI](https://pypi.org/project/touchmusic/) with Python 3.11:

    py -3.11 -m pip install touchmusic

The base package contains desktop effects, camera gestures, pitch correction, loops, and MIDI. The singing engine and model downloads are installed separately. **touchmusic --help** lists launch and setup options.

## Requirements

- Windows 10 or 11, 64-bit.
- [Python 3.11, 64-bit](https://www.python.org/downloads/) with the Windows Python launcher.
- [Git for Windows](https://git-scm.com/download/win).
- A microphone and headphones. A webcam enables gesture control.
- Internet for setup and the first AI model downloads.
- Several GB of free disk space for the Python environment and downloaded models.
- An NVIDIA GPU and compatible driver are recommended for AI conversion. Setup installs CUDA 12.8 PyTorch wheels. The model loader supports CPU, but real-time CPU performance has not been validated.

Effects, pitch correction, playback, and looping work before loading the AI model. A fresh clone starts with an empty voice library. Import your own reference audio to use character conversion.

## Quick start

1. Clone the repository into a writable folder.

       git clone https://github.com/RealShocky/TouchMusic.git
       cd TouchMusic

2. Double-click **Setup.cmd** and let it finish. It creates the Python environment, installs dependencies, downloads Seed-VC at the pinned revision, and applies the inference compatibility patch.
3. Double-click **Launch.cmd**.
4. Select your microphone and headphone output, then click **Start audio**.
5. Choose **Natural**, **Tight**, or **Hard** to try pitch correction. Turn off **Dialogue mode** so vocal effects apply.
6. For gestures, click **Start camera**, check the preview, open **Gesture mapping**, and enable **Arm gestures**.

Launch.cmd changes to its own folder before starting the app, so it works from a desktop shortcut. Run **Launch.cmd --load-engine** to load the AI engine at launch. Later runs only need Launch.cmd. Setup is for creating or repairing the environment.

## Desktop shortcut

Right-click **Launch.cmd** in your installation folder and choose **Show more options → Send to → Desktop (create shortcut)**. The shortcut should point to Launch.cmd, with **Start in** set to the installation folder.

You can also choose **New → Shortcut** on the desktop, browse to Launch.cmd, and name it **TouchMusic**.

## Pitch correction

1. Click **Auto-Tune Off** on the main screen to enable pitch correction.
2. Choose a preset, or adjust **Tune strength** and **Retune speed** on the **Pitch correction** tab.
3. Set the song key, scale, and target. **Chromatic** uses the nearest semitone. **Key / scale** restricts correction to your scale. **Current chord** targets the active triad.
4. Choose **Wet vocal** in Music tools to hear the processed result. Hold a sung note and watch the detected note, target, and cents meter.

Higher retune speed pulls notes into tune faster. Dialogue mode bypasses pitch correction and vocal effects. The UI label “Auto-Tune” refers to TouchMusic's built-in pitch correction.

Music tools also contains vocal range, vibrato preservation, harmony mode, and formant controls. Formant shifting changes voice color independently of pitch and adds about 43 ms of processing delay while active.

## Character voices

1. Click **Import audio** and choose WAV, MP3, FLAC, or OGG. The reference picker opens with a player and waveform.
2. Listen with **Play song**, seek with the full-track slider, and click **Use playhead as start** when you find a section. Drag the green selection or either edge to choose 1–8 seconds. Zoom and the waveform scrollbar let you work through longer songs. **Play selection** auditions the highlighted section, and **Loop selection** repeats it.
3. Enter a voice name and click **Use this section**. TouchMusic saves the selected audio and selects the new reference in the voice list.
4. Click **Load singing engine** and wait until it reports ready.
5. Enable **Use AI character conversion**, start audio, and speak or sing.

The engine uses up to eight seconds. The picker saves exactly the chosen section as the reference, so it can come from anywhere in a whole song. Earlier imports still use their first eight seconds. Use clear solo vocals with minimal instruments. The picker extracts the selected section as supplied. WAV preserves the source best, and MP3 is supported.

Preview output and volume can be chosen inside the picker. It plays through its own player and works while the main audio engine is stopped. Use headphones while auditioning if the main microphone is active.

Preview plays the reference. AI mix blends time-aligned dry and converted samples. Results depend on the reference, performance, and model. Importing a short reference does not train a dedicated model.

### Live and Studio modes

| Mode | Model steps | Input block |
| --- | --- | --- |
| Live | 4 | 800 ms |
| Studio | 8 | 1.2 seconds |

Input blocks are only part of the audible delay. Inference, buffering, audio devices, and effects add latency. Status reports compute time and dropped chunks.

For singing in time, use **Dry mic** headphone monitoring while recording the processed vocal. Leave a few seconds after the final phrase so buffered audio can finish.

## Four-track looper

Set BPM or use Tap tempo, then choose Immediate, Next beat, or Next bar. Enable Metronome for a headphone click.

- Click a pad to capture. Click it again to finish and play.
- Quantized pads display the remaining beats until capture or finish. Press the same pad again before the boundary to cancel.
- Starting capture on another track finishes the current capture.
- Each track has level and mute. Select a track for restart, export, clear, or undo.
- In Replace mode, capturing over a filled track replaces its take. Overdub adds a layer. Undo and Redo move through up to four prior committed takes. Clear loop clears the clip and history.
- Four tracks hold up to 120 seconds each and play together.
- Processed vocal captures effects and AI output, including conversion delay. Mic before AI captures after enabled pitch correction and before downstream AI and vocal effects.

The clock uses 4/4 and starts when audio starts. Chords and loop restart follow the timing setting. Keep BPM fixed while building loops. Existing clips keep their speed when BPM changes. Backing tracks use their own playhead.

## Chords and harmony

Open Music tools, choose a chord, and enable Play chord pad. Key and scale determine seven diatonic triads.

**Map left fingers 1–5 to chords I–V** replaces those poses' previous mappings. You can assign all seven chords, next / previous chord, and the chord-pad switch individually.

For vocal harmony, choose Chord above or Chord below and raise Harmony on the Vocal effects tab.

## Gesture control

| Input | Controls |
| --- | --- |
| Finger counts and fists | Voice slots, next / previous voice, loop capture, mute, restart, undo, chords, transport, recording, saved scenes |
| Thumb-index pinch | A discrete action when the fingertips touch |
| Hand height or side-to-side movement | Effects, pitch, levels, tuning strength, retune speed |
| Thumb-index spread | A continuous effect or level |
| Rehearse gestures | Shows a detected pose and mapped action before arming |

Hold a pose for about a quarter second. It fires once until the pose changes. Pinch means touching thumb tip to index fingertip. Leave pinch unassigned if you want that hand's closed fist to take priority.

Assign voice slots in Gesture mapping. Default right-hand counts 1–4 select populated slots 1–4. Voice 5 is available to map. Rehearse assignments, then exit rehearsal and enable Arm gestures.

## Vocal effects and scenes

Vocal effects include pitch, reverb, delay, harmony, robot modulation, chorus, drive, radio, low octave, tremolo, warmth, brightness, noise gate, delay feedback and time, AI mix, and levels.

Presets include Clean, Space, Choir, Machine, Intercom, Villain, and Ghost. Save a preset to recall effects, voices, mappings, and musical settings together. Saved presets appear as gesture scene actions.

## Save a skit

Save skit creates a .touchmusic archive with completed loops, backing, active and slotted voice references, scenes, levels, loop mutes, gesture mappings, and musical settings.

Finish capture before saving. Open skit restores the arrangement, stops audio, and disarms gestures so you can check it before performing.

## Recording and aligned export

Record performance writes the processed mix to WAV. Its gesture action starts and stops a recording in data/recordings without a file picker.

Record separate WAV stems creates a folder beside the mix with dry mic, wet vocal, four loop tracks, backing, and chords. Mute output silences monitoring while recording continues.

Export aligned vocal and mix generates wet-vocal-aligned.wav and performance-aligned.wav after stopping. Converted samples return to their originating microphone times. The original mix and stems remain available.

Alignment accounts for neural transport and the active formant buffer. Missing converted audio remains silent. It cannot recover samples arriving after recording stops. Other effect delays and tails can remain. The aligned mix uses the master level at stop instead of replaying master automation.

## Using TouchMusic with FL Studio

### Live audio route

TouchMusic already offers a selectable output device. A virtual audio cable can carry that output into an FL Studio Mixer input.

1. Install a virtual cable such as [VB-CABLE](https://vb-audio.com/Cable/) using its vendor instructions.
2. In TouchMusic, keep your microphone selected and choose **CABLE Input** as the output using the same Windows audio backend as the microphone. Choose **Wet vocal** monitoring to send the converted/effected sound.
3. In FL Studio's Audio settings, select **FL Studio ASIO** and open its panel. Choose **CABLE Output** as input and your headphones as output.
4. Select the available external input on an FL Mixer insert. Monitor it and arm it for recording. FL Studio Producer Edition or higher supports external audio recording.

This sends TouchMusic's monitored mix, including loops and backing if playing. Disable TouchMusic's metronome if you want the click excluded from this route. The AI engine's processing delay also reaches FL Studio. This routing requires configuring the virtual driver and has not been verified on every device.

For an existing performance, import the WAV mix or separate stems into FL Studio. The aligned export can help place the converted vocal against the backing track.

### Gesture control and plugin support

Open **MIDI / FL** in TouchMusic. Create a virtual port with [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html), click Refresh ports, select that port and channel, then Connect MIDI. Enable the same input in FL Studio's MIDI settings. **Test C4** checks the connection.

In Gesture mapping, map continuous hand movements to **MIDI CC 0–119** and poses to **MIDI note C4–B4**, **MIDI chord**, or **MIDI chord I–VII**. The chord actions use the selected song key and scale. Set note velocity and length in MIDI / FL. **Map hand heights to CC 1 / 74** provides a quick starting point.

Arm gestures to send. Rehearsal previews actions. Disarming sends all-notes-off. MIDI output disconnects when the app closes. Timed note release prevents a pose from leaving its notes held indefinitely. The all-notes-off button is also available manually. Connections are selected explicitly after launching the app.

To link a plugin knob in FL Studio, right-click it, choose Link to controller, and move the mapped hand. MIDI transports control messages. Use the audio route above for vocals. The existing native control bridge sends controls/timing; the full processed-audio bridge is still planned.

Official references are [FL Studio audio settings](https://www.image-line.com/fl-studio-learning-content/fl-studio-online-manual/html/envsettings_audio.htm), [audio recording](https://www.image-line.com/fl-studio-learning-content/fl-studio-online-manual/html/recording_audio.htm), and [external controller linking](https://www.image-line.com/fl-studio-learning-content/fl-studio-online-manual/html/automation_linking.htm).

## Files and local data

| Path | Purpose |
| --- | --- |
| touchmusic/ | Desktop app, audio, camera, gestures, transport, session, and conversion source |
| Launch.cmd | Windows launcher |
| Setup.cmd | Environment and pinned upstream setup |
| requirements.txt | Runtime dependencies |
| prepare_seed.py | Upstream inference compatibility patch |
| .venv/ | Local Python environment |
| vendor/seed-vc/ | Downloaded inference source and upstream license |
| data/voices/ | Imported reference copies and manifest |
| data/models/ | Downloaded models |
| data/settings.json | Devices, effects, scenes, and mappings |
| data/recordings/ | Default recording folder |
| data/touchmusic.log | Startup and runtime diagnostics |

Source-folder launches keep data beside the source. A wheel installation uses **%LOCALAPPDATA%/TouchMusic** on Windows. **TOUCHMUSIC_DATA_DIR** can override the data directory. Imported voices and models are excluded from the package.

## Publishing a release

Bump the version in pyproject.toml and touchmusic/runtime.py, update release-notes.md, then push to main. The release workflow builds a wheel, source distribution, Windows setup ZIP, and SHA-256 checksums and publishes a GitHub release. The same version is kept immutable on reruns.

For the first PyPI publication, add a pending trusted publisher in your PyPI account:

| PyPI field | Value |
| --- | --- |
| Project name | touchmusic |
| Owner | RealShocky |
| Repository | TouchMusic |
| Workflow | release.yml |
| Environment | pypi |

After configuring it, version builds on main publish automatically. You can also open Actions, select Build and release TouchMusic, choose Run workflow, and enable **publish_pypi**. Reruns reuse the exact Python distributions attached to the existing GitHub release. The publisher uses short-lived GitHub OIDC authentication.

This repository contains source and setup files. User audio, model weights, recordings, settings, upstream checkout, and the Python environment are generated locally and ignored by Git. Screenshots can be added under docs/screenshots/ and embedded here.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Setup cannot find Python | Install 64-bit Python 3.11 with the Windows launcher, then retry |
| Git unavailable | Install Git for Windows and reopen Setup.cmd |
| Audio fails to open | Select input and output from the same Windows audio backend, then refresh |
| Camera fails | Close other webcam apps, check Windows camera access, and try another camera index |
| Tuning has no effect | Enable it, turn off Dialogue mode, choose Wet vocal, and sing a held note |
| Voice sounds unchanged | Select the imported reference, load the engine, enable AI conversion, and check AI mix |
| Loop seems to wait | Check Next beat / Next bar and the queued pad state |
| AI breaks up or is delayed | Try Live and Dry mic monitoring, close other GPU workloads, and check dropped chunks |
| Final AI phrase missing | Leave a few seconds after the last phrase before stopping |
| Startup exits | Read data/touchmusic.log and rerun Setup.cmd if dependencies are missing |

## Status and acknowledgments

TouchMusic is an experimental Windows application. Automated DSP, transport, conversion-queue, recording, session, and UI tests were run during development. Live performance depends on your devices, reference audio, and GPU.

The singing engine uses [Seed-VC](https://github.com/Plachtaa/seed-vc), pinned by Setup.cmd. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for source, model, and dependency information. The repository owner has not yet selected a license for TouchMusic's application source.

## New in 0.2.0

- **Import audio:** choose Suggest section or Next suggestion, audition it, then Use this section. The level, silence, and possible-clipping report updates when you drag the selection. Suggestions rank audio levels; they do not identify singers or isolate vocals from music.
- **Loop capture:** select Replace or Overdub. Choose 0-2 count-in bars and Free length or 1/2/4/8 bars. Click a loop pad or use its gesture action. A second click cancels a queued start or finishes capture. Count-in clicks go to monitoring, not performance recordings.
- **Overdub:** add layers to an existing loop, with up to four prior committed takes available through Undo/Redo. Feedback controls how much existing audio survives each pass. With a fixed length selected, overdubs finish after one existing-loop cycle. Recorded loops retain their original playback speed when BPM changes.
- **Edge fade:** choose 0-20 ms to soften loop boundaries without changing duration. Loop pads display countdowns, recording state, and playback progress.
- **Recovery:** completed loops, backing, references, scenes, and settings save in the background after changes settle. An unexpected exit offers Recover session before any new session can overwrite that backup. Session > Recover last session is also available after a normal exit. An unfinished recording and undo history are not recovered. Save important performances as skits as well.
- **Setlists:** use Session > Save skit for each song, then Session > Setlist to add and arrange skits. Save the list as `.tmsetlist`. Next song and Previous song can be assigned to gestures. Song recall stops audio and disarms gestures; check the setup and restart audio. Keep the skit files alongside the setlist when moving it.

Live FL Studio routing and hardware timing remain under test. These additions work independently of DAW routing.

## Stage view and gesture precision (0.3.0)

- **Session > Stage view**, or **F11** from the main window, opens large voice, key, chord, tempo, and loop controls. In stage view, F11 toggles fullscreen. Space toggles output mute. Back to controls returns to the main window.
- **F12** performs an emergency mute from anywhere inside TouchMusic: output muted, gestures disarmed, MIDI notes released. It leaves recording and the arrangement running. Unmute explicitly when ready; re-arm gestures separately.
- **Gesture mapping > Precision and calibration** adjusts pose hold, movement smoothing, deadband, sensitivity, and pinch cooldown. Defaults retain the earlier 250 ms pose hold and 90 ms smoothing, with a 2% movement deadband.
- Start the camera, click **Calibrate movement for 5 seconds**, and move both hands through a comfortable up/down and side-to-side range. Open and close thumb-index spread too. Calibration disarms gestures and retains prior ranges for axes without enough movement. It never arms gestures automatically. Reset calibration restores full movement ranges.
- **Freeze movements** holds continuous controls while finger and pinch actions remain available. Calibration and precision settings save with presets, skits, recovery, and app settings. The temporary freeze switch is not saved.
- New movement targets: **Tempo, Overdub feedback, Loop edge fade, Count-in bars, Capture length, Song key, Chord selection**. New pose actions: **Toggle overdub mode, Next capture length, Next count-in, Freeze movements, Emergency mute, Toggle stage view**. Tempo changes schedule future events; existing loops keep their recorded playback speed.
- **Session > Test output** plays a quiet 440 Hz tone for 0.8 seconds through the selected output after audio is started. The tone obeys output mute and master level and is excluded from recorded mixes, stems, and loop capture. This verifies playback by listening, not an automatic device loopback measurement.

Gesture precision and stage controls are covered by automated tests. Camera comfort, tracking consistency, audible hardware output, and DAW routing still need live validation.

## Studio workspaces (0.4.0)

The v0.4.0 baseline has a menu bar and ten sidebar workspaces: Perform, Voice lab, FX rack, Songs, Gestures, Macros, Music & chords, Audio setup, MIDI / DAW, and VST3 bridge. The stage window remains available separately. Existing Session menu actions still work.

### Guided audio setup and diagnostics

Open **Audio setup**, choose compatible microphone/output devices, Apply and start audio, speak to check Input, then play the output test. Confirm hearing the tone yourself. Named routing profiles save device names; unavailable devices are reported instead of silently substituting a saved profile. The readable health summary shows clipping, audio status events, plugin failures, and AI backlog. The optional technical report can be copied or exported locally. Driver latency is reported, not measured by a hardware loopback test.

### Gesture macros

Use **Macros** to save up to eight actions in each of eight slots, then map a pose to Macro 1..8. Actions execute in order immediately. Loop, chord, and playback commands retain their own beat/bar scheduling. Model reference preparation can add delay. Nested macros are rejected, and Emergency mute stops the remaining macro actions. Saved scenes can be macro actions. Definitions travel with presets, skits, settings, and recovery.

### Voice comparison lab

Stop main audio, load the singing engine and a reference, then open **Voice lab**. Choose source audio, a start time and 1..8 second length, then choose A/B voice references and Live/Studio quality. Render comparison uses the existing model worker serially, with bounded context chunks rather than loading another GPU model. Preview dry/A/B on the explicitly selected preview output, or export floating-point WAVs. Main audio cannot start during rendering. Cancellation waits for the current model chunk. The same source phrase makes comparison easier; displayed render time, RMS and overload fractions do not constitute an objective voice-similarity score. Model quality still needs listening tests.

### VST3 effects in the development checkout

Open **Plugin Center** to discover installed VST3 paths without loading them. Add a custom folder if needed, enter the exact publisher version and choose **Scan selected**. A successful scan permits **Load into FX rack**. Failed scans are quarantined in Plugin Center until a successful rescan. **FX rack** also retains the explicit file/bundle picker and four-slot controls.

Third-party effects load/process in an owned worker process. A native crash or timeout stops that worker while TouchMusic continues with time-aligned delayed dry audio. Stop audio, then use **Restart isolated rack** to retry. Populated racks add 2048 scheduled frames, approximately 42.7 ms at 48 kHz, before unknown plugin, AI and device delays. This trades latency for fault containment; it is not a hardware round-trip measurement or full plugin latency compensation.

Stereo effect output is preserved through the master, device output and new stereo performance/stem WAVs. Existing loop capture and backing/reference storage remain mono for archive compatibility. Dialogue mode bypasses vocal effects and the external rack. Instruments use the separate Instruments workspace; sidechain routing remains planned.

Select a parameter and bind **Plugin knob 1..8**, then choose that knob in Gesture mapping. Or start the camera, choose **Gesture Learn**, and deliberately move a hand vertically/horizontally or change thumb-index spread. Learning disarms performance gestures and times out after ten seconds. Arm again when ready to perform.

With audio stopped, **Open native editor** opens the actual plugin interface in its worker process. Close it before starting audio or changing the rack. Exposed parameter changes synchronize on close. The current runtime native state survives normal audio start/stop, but opaque programs/state are not yet saved across rack reloads or projects. Snapshots preserve normalized exposed parameters.

Saved skits never automatically load native effects. Review the paths and choose **Restore saved rack**. Plugins must remain installed at their saved paths. This process boundary contains crashes, not malicious binaries running with your OS permissions.

Plugin Center lists fifteen official publisher candidates and stages checksum-pinned TDR Nova 2.2.3, SnapTune 2.4.0 and LyraTune 0.6.7 archives. Downloaded files are never executed or automatically installed. Other candidates open their official publisher pages until an exact asset is reviewed. No third-party effects or personal references are redistributed. See the [versioned compatibility matrix](docs/PLUGIN_COMPATIBILITY.md), which distinguishes scan evidence from actual editor, listening, hardware and DAW checks.

### Motion Score in the development checkout

Open **Motion Score**, start audio and choose **Record**. Perform movement controls and deliberate finger/pinch actions, then **Stop**. Recording replaces the existing score. The event table lets you edit beat positions, targets and normalized values, apply edits, delete rows, and import/export JSON. **Play** explicitly replays automation and disarms camera gestures. Playback can change voices, loops, effects and MIDI. F12 stops playback, releases MIDI notes and mutes output.

Scores are optional saved-performance data and never auto-play on load. The current beat timeline is serviced by the 100 ms UI timer, so it is not sample-accurate automation. Visual envelopes and deterministic scheduling remain on the roadmap.

### Loop performance tricks

Tools > Loop playback provides reverse, half-speed, double-speed, normal playback, and toggle eighth-note stutter for the selected loop. These are also gesture actions and follow beat/bar scheduling. Half/double speed changes pitch; pitch-preserving tempo matching is still future work. Return to Normal before overdubbing. Speed and reverse settings save with the performance; temporary stutter state does not. Export loop writes the original captured clip, without live playback tricks.

### Recovery history

File > Recovery history lets you choose the latest completed snapshot or up to five prior snapshots, with a 256 MiB budget for prior backups. The latest backup remains separate. Restore stops audio and disarms gestures. Active recording and undo stacks are not recovered. Save important performances as skits too.

### VST3 control bridge

Download the separate Windows Control Bridge ZIP from the release and load the `.vst3` bundle in your DAW. Enable the opt-in receiver in **VST3 bridge**. Host automation, tempo/musical position and optional backing transport chase are available. The native plugin passes DAW audio through unchanged; processed vocals require their own audio route. See [native/control_bridge/README.md](native/control_bridge/README.md) for controls and timing limits. Live FL Studio validation is pending.

### Platform support

The supported release is **Windows 10/11 x64 with Python 3.11**. Python modules and native bridge source contain portable components, but macOS/Linux camera, device routing, engine installation, packaging and host validation are not certified. This is a Windows studio build, not a completed cross-platform release.

## Engineering and verification

- [roadmap.md](roadmap.md): authoritative requirements, priorities, status and release gates.
- [Architecture](docs/ARCHITECTURE.md): process boundaries, stereo/audio timing and compatibility contract.
- [Technical debt](docs/TECHNICAL_DEBT.md): known risks and remediation.
- [Plugin compatibility](docs/PLUGIN_COMPATIBILITY.md): exact binary/version evidence.
- [Benchmarks](docs/BENCHMARKS.md): repeatable CPU/memory/timing comparison and explicitly unmeasured hardware/GPU checks.

Run `python -m pytest tests -q` for automated regressions. The synthetic benchmark is `python tools/benchmark_audio.py --label development --output benchmark.json`; it does not open audio hardware or invoke AI. Development versions are built/tested but are excluded from automatic stable GitHub/PyPI publishing.

## Development increment 0.5.0.dev2

Two new workspaces are available:

- **Instruments**: explicitly load one VST3 synthesizer, start audio, and test C4 or a chord. Map Instrument C4..C5, Instrument chord I..VII and Instrument panic to poses. Eight Instrument knobs and Instrument level accept movement mappings. Notes have timed release, retrigger protection and panic on disarm. Instruments run in their own child process and contribute a stereo recording stem. Saved instruments require explicit reviewed restore. Third-party synth compatibility remains per binary, not guaranteed.
- **DAW audio**: stop standalone audio, enable the receiver, and load **TouchMusic Audio Bridge.vst3** on a 48 kHz DAW insert. It sends DAW input through the standalone effects/AI path and returns stereo audio without a virtual cable. The model must be ready and AI enabled to convert a voice. The separate Control Bridge remains unchanged for automation/timing.

The experimental Audio Bridge reports 4096 transport frames, about 85.3 ms at 48 kHz. AI buffering, external FX worker delay and instrument delay are additional and are not included in full DAW delay compensation yet. Fast offline rendering and non-48-kHz wet return are unsupported. Missing/late returns use delayed dry audio. Physical FL Studio, editor, microphone/camera and real-model DAW validation remain pending.

Actual native hosting returned 90 processed stereo blocks matching standalone DSP. Both compiled bridges passed 47 SDK checks each. Automated note/queue/rate/PCM/duplicate-packet/AI-routing tests are included. These are software tests, not listening or hardware certification.
