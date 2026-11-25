# TouchMusic

![Windows](https://img.shields.io/badge/platform-Windows_10%2F11-0078D4)
![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Standalone](https://img.shields.io/badge/app-standalone-559C80)
![Local AI](https://img.shields.io/badge/voice_conversion-local-7958A6)
![Status](https://img.shields.io/badge/status-experimental-D59C37)

**Perform live with your voice, switch characters with hand gestures, and build layered loops.**

TouchMusic combines microphone effects, pitch correction, webcam hand tracking, reference-based AI voice conversion, a chord pad, a four-track looper, and WAV recording in a standalone Windows desktop app.

[Quick start](#quick-start) · [Auto-Tune](#pitch-correction) · [Looper](#four-track-looper) · [Gestures](#gesture-control) · [Troubleshooting](#troubleshooting)

## Features

| Area | Controls |
| --- | --- |
| Voice performance | Live microphone monitoring, backing tracks, vocal effects, master mute |
| Pitch correction | Auto-Tune switch, Natural / Tight / Hard presets, key and scale, chromatic or chord targets, pitch meter |
| Character voices | Import, preview, and rename your own references; five gesture voice slots |
| AI conversion | Local pitch-conditioned Seed-VC; Live and Studio modes; compute and dropped-chunk status |
| Gestures | Finger counts, fists, thumb-index pinch, hand height, horizontal movement, thumb-index spread |
| Looper | Four tracks, 120 seconds per track, level, mute, restart, replacement undo, WAV export |
| Musical timing | Tap tempo, 40–240 BPM, 4/4 metronome, immediate / next beat / next bar loop and chord changes |
| Vocal character | Chord-following harmonies, vocal-range selection, vibrato preservation, formant shifting |
| Sessions | Portable skits with completed loops, backing, voice references, settings, scenes, and mappings |
| Recording | Performance WAV, separate stems, optional automatic vocal and mix alignment |

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

1. Click **Import audio** and choose WAV, MP3, FLAC, or OGG.
2. Select the new voice in the **Character voice** dropdown. Importing preserves your previous selection.
3. Click **Load singing engine** and wait until it reports ready.
4. Enable **Use AI character conversion**, start audio, and speak or sing.

References must contain at least one second of audio. The engine uses the first eight seconds. Use a clean solo voice and trim the lead-in. WAV preserves the source best, and MP3 is supported.

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
