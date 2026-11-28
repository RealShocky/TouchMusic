> Historical initial standalone design. Superseded by [the authoritative roadmap](../roadmap.md) and [current architecture](ARCHITECTURE.md). Initial FL exclusions and unchecked task lists below are historical, not current constraints or delivery status.

# TouchMusic Implementation Plan

Goal: deliver and launch a standalone desktop singing instrument.

Architecture: native UI, independent audio callback, camera worker, bounded neural worker, local reference library. Tech stack: Python 3.11, PySide6, sounddevice, Pedalboard, MediaPipe, Seed-VC.

Spec: design.md. Execution is authorized by the user's request to do all and build standalone first.

## Global constraints
- No changes to the BygHeart source project.
- No FL Studio integration in this version.
- Show measured model timing and actual readiness.
- Never perform model inference or disk writes in the audio callback.

## Review focus
- Device start failure leaves no open streams.
- Voice switches discard stale audio.
- Missing or corrupt references report errors without crashing.
- Queue saturation is bounded and reported.
- Camera loss does not repeatedly trigger preset changes.

## Tasks
- [ ] Library and presets: atomic JSON persistence, WAV/MP3 import and metadata. Test bad files and duplicate import.
- [ ] Audio: effects, backing track, looper and recording. Test block continuity, output limits, looping and recording overflow.
- [ ] Conversion: pitch-conditioned Seed-VC backend, bounded asynchronous streaming, voice changes. Test sample conversion, switching and queue limits.
- [ ] Camera: two-hand landmarks, smoothing, pinch edges, tracking loss. Test landmark mappings.
- [ ] Desktop: device controls, effects, voice import/preview, transport, camera and statuses. Exercise controls offscreen and launch normally.
- [ ] Package, verify and document actual limitations. Run full tests and independent review.
