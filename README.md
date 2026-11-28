# TouchMusic

![Windows](https://img.shields.io/badge/platform-Windows_10%2F11-0078D4)
![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Standalone](https://img.shields.io/badge/app-standalone-559C80)
![Local AI](https://img.shields.io/badge/voice_conversion-local-7958A6)
![Status](https://img.shields.io/badge/status-experimental-D59C37)
[![Latest release](https://img.shields.io/github/v/release/RealShocky/TouchMusic)](https://github.com/RealShocky/TouchMusic/releases/latest)
[![PyPI](https://img.shields.io/pypi/v/touchmusic)](https://pypi.org/project/touchmusic/)

**Perform live with your voice, switch characters with hand gestures, and build layered loops.**

TouchMusic combines microphone effects, pitch correction, webcam hand tracking, reference-based AI voice conversion, a chord pad, a four-track looper, and WAV recording in a standalone Windows desktop app.

[Quick start](#quick-start) � [Auto-Tune](#pitch-correction) � [Looper](#four-track-looper) � [Gestures](#gesture-control) � [Troubleshooting](#troubleshooting)

## Features

| Area | Controls |
| --- | --- |
| Voice performance | Live microphone monitoring, backing tracks, vocal effects, master mute |
| Pitch correction | Auto-Tune switch, Natural / Tight / Hard presets, key and scale, chromatic or chord targets, pitch meter |
| Character voices | Import, preview, and rename your own references; five gesture voice slots |
| AI conversion | Local pitch-conditioned Seed-VC; Live and Studio modes; compute and dropped-chunk status |
| Gestures | Finger counts, fists, thumb-index pinch, hand height, horizontal movement, thumb-index spread |
| Looper | Four tracks, 120 seconds per track, level, mute, restart, replacement undo, WAV export |
| Musical timing | Tap tempo, 40-240 BPM, 4/4 metronome, immediate / next beat / next bar loop and chord changes |
| Vocal character | Chord-following harmonies, vocal-range selection, vibrato preservation, formant shifting |
| Sessions | Portable skits with completed loops, backing, voice references, settings, scenes, and mappings |
| Recording | Performance WAV, separate stems, optional automatic vocal and mix alignment |
| MIDI output | Gesture CC, notes, chords, velocity, channel, timed note release, all-notes-off |

## Download or install

Download the Windows setup ZIP from [Releases](https://github.com/RealShocky/TouchMusic/releases/latest), extract it, run Setup.cmd once, then Launch.cmd. Python 3.11 and Git are required. Setup downloads the runtime.

The release also includes an installable wheel. With Python 3.11, install it directly:

    py -3.11 -m pip install https://github.com/RealShocky/TouchMusic/releases/download/v0.1.0/touchmusic-0.1.0-py3-none-any.whl
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

Right-click **Launch.cmd** in your installation folder and choose **Show more options  Send to  Desktop (create shortcut)**. The shortcut should point to Launch.cmd, with **Start in** set to the installation folder.

You can also choose **New  Shortcut** on the desktop, browse to Launch.cmd, and name it **TouchMusic**.

## Pitch correction

1. Click **Auto-Tune Off** on the main screen to enable pitch correction.
2. Choose a preset, or adjust **Tune strength** and **Retune speed** on the **Pitch correction** tab.
3. Set the song key, scale, and target. **Chromatic** uses the nearest semitone. **Key / scale** restricts correction to your scale. **Current chord** targets the active triad.
4. Choose **Wet vocal** in Music tools to hear the processed result. Hold a sung note and watch the detected note, target, and cents meter.

Higher retune speed pulls notes into tune faster. Dialogue mode bypasses pitch correction and vocal effects. The UI label "Auto-Tune" refers to TouchMusic's built-in pitch correction.

Music tools also contains vocal range, vibrato preservation, harmony mode, and formant controls. Formant shifting changes voice color independently of pitch and adds about 43 ms of processing delay while active.

## Character voices

1. Click **Import audio** and choose WAV, MP3, FLAC, or OGG. The reference picker opens with a player and waveform.
2. Listen with **Play song**, seek with the full-track slider, and click **Use playhead as start** when you find a section. Drag the green selection or either edge to choose 1-8 seconds. Zoom and the waveform scrollbar let you work through longer songs. **Play selection** auditions the highlighted section, and **Loop selection** repeats it.
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
- Quantized pads display Capture queued or Finish queued until the boundary. Press the same pad again before the boundary to cancel.
- Starting capture on another track finishes the current capture.
- Each track has level and mute. Select a track for restart, export, clear, or undo.
- Capturing over a filled track replaces its take. Undo swaps the current and previous take. Clear loop clears both.
- Four tracks hold up to 120 seconds each and play together.
- Processed vocal captures effects and AI output, including conversion delay. Mic before AI captures after enabled pitch correction and before downstream AI and vocal effects.

The clock uses 4/4 and starts when audio starts. Chords and loop restart follow the timing setting. Keep BPM fixed while building loops. Existing clips keep their speed when BPM changes. Backing tracks use their own playhead.

## Chords and harmony

Open Music tools, choose a chord, and enable Play chord pad. Key and scale determine seven diatonic triads.

**Map left fingers 1-5 to chords I-V** replaces those poses' previous mappings. You can assign all seven chords, next / previous chord, and the chord-pad switch individually.

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

Assign voice slots in Gesture mapping. Default right-hand counts 1-4 select populated slots 1-4. Voice 5 is available to map. Rehearse assignments, then exit rehearsal and enable Arm gestures.

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

In Gesture mapping, map continuous hand movements to **MIDI CC 0-119** and poses to **MIDI note C4-B4**, **MIDI chord**, or **MIDI chord I-VII**. The chord actions use the selected song key and scale. Set note velocity and length in MIDI / FL. **Map hand heights to CC 1 / 74** provides a quick starting point.

Arm gestures to send. Rehearsal previews actions. Disarming sends all-notes-off. MIDI output disconnects when the app closes. Timed note release prevents a pose from leaving its notes held indefinitely. The all-notes-off button is also available manually. Connections are selected explicitly after launching the app.

To link a plugin knob in FL Studio, right-click it, choose Link to controller, and move the mapped hand. MIDI transports control messages. Use the audio route above for vocals. Native TouchMusic VST3 hosting would require a separate plugin implementation.

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

