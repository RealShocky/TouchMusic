> Historical initial standalone design. Superseded by [the authoritative roadmap](../roadmap.md) and [current architecture](ARCHITECTURE.md). Initial FL exclusions and unchecked task lists below are historical, not current constraints or delivery status.

# TouchMusic standalone

Approved scope from the conversation: one Windows app for live singing, webcam gestures, vocal effects, reference voice selection, local singing conversion, backing tracks, looping and recording. FL Studio is deferred by the owner.

Use PySide6 for the native desktop, PortAudio via sounddevice for audio, Pedalboard for stateful effects, MediaPipe for two-hand landmarks, and the upstream Seed-VC pitch-conditioned model for reference-based singing conversion. Keep inference off the audio callback. Model weights are downloaded locally. This is integration of a pretrained model with a custom streaming engine, not training a foundation model.

Audio runs at 48 kHz. The live effects path and buffered neural path expose their different latency. Microphone monitoring starts only on the user's Start button. Voice switching clears stale converted audio. A bounded queue prevents unbounded latency. Recording writes on a background thread and reports overflow. Gesture mapping uses continuous smoothing and an armed pinch for deliberate changes. Tracking loss holds settings and releases gesture state.

The interface uses a graphite studio panel, warm white text, cyan meters and amber recording controls, with large performance controls and a central camera preview. Device selection, voice library and track transport remain visible. User settings and imported references live in the app data directory.

Existing BygHeart recordings are imported as reference candidates. Their use with singing is evaluated independently. No cloud voice account is needed. Conversion must show loading/error/ready states accurately. Neural hardware performance and hand tracking are measured on this host where available.

Alternatives considered: browser-only audio offers convenient delivery but weaker native device access. A DAW plugin adds a host dependency. Native standalone meets the requested workflow.
