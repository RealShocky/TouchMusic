# TouchMusic architecture

Development snapshot: 0.5.0.dev2. Requirements and delivery status live only in [roadmap.md](../roadmap.md).

## Runtime boundaries

```mermaid
flowchart TD
    UI["Qt UI and gesture mapping"] --> Cache["Rack descriptors and parameter cache"]
    Audio["Audio callback and stereo mix"] --> Queue["Bounded 512-frame jobs"]
    Cache --> Broker["Plugin broker thread"]
    Queue --> Broker
    Broker --> Worker["Owned Python native-plugin process"]
    Worker --> Results["Results keyed to source blocks"]
    Results --> Audio
```

The GUI process hosts the built-in Pedalboard effects, looper, recorder and camera UI. External VST3 DLLs are loaded only by `plugin_worker.py` in an owned child. One child contains the complete four-slot effect rack. A crash bypasses the complete external rack; it does not isolate each effect from the other effects. Python exception handling alone cannot contain a native access violation, hence the process boundary.

`PluginRack` remains the worker-side backend and supports injected fake loaders in regression tests. `IsolatedPluginRack` is the desktop facade. It exposes the existing settings/order/bypass/bindings API without holding native plugin objects.

This is fault containment, not a security sandbox for hostile binaries. A plugin runs with the current user's OS permissions.

## Audio and timing

- Device input and the local AI converter remain mono at 48 kHz. The device block size remains 512 frames.
- The external effect chain can produce two independent channels. These survive the stereo master, device callback and new stereo performance/stem recordings.
- Existing `AudioEngine.process(audio)` callers receive the compatible mono mix. `stereo=True` returns samples by channels. Worker PCM uses channels by samples.
- Existing loop captures and backing/reference assets remain mono. Wet loop capture explicitly downmixes the two channels to preserve the old loop/archive representation. Stereo assets require the planned migration.
- The callback accumulates variable-sized render segments into 512-frame plugin jobs. It never waits on pipe IO or native processing.
- The worker pipeline adds exactly 2048 scheduled frames, 42.667 ms at 48 kHz, when the external rack is populated. Empty racks add no worker delay. This excludes plugin DSP, built-in DSP, AI and device latency.
- Every wet result belongs to its original input block. An unavailable result uses the corresponding delayed dry block. Late results cannot slide into a later block. Six queued jobs and about five timeline blocks bound callback-side storage.
- A slow or dead worker can cause audible fallback changes. Crossfading wet/fallback, measured plugin latency compensation and reducing worker delay are open work, not hidden guarantees.
- Recording provenance receives the same worker delay as the vocal stream, preserving converter/source-frame mapping. It does not compensate an unknown third-party plugin's internal latency.

The broker sends only parameter changes. It retains the latest normalized target in a bounded descriptor map instead of dropping a final gesture when a plugin is busy. Broker/native processing still runs under general-purpose Python/OS scheduling; this is not a hard real-time guarantee.

## Worker protocol and lifecycle

RPC is bounded UTF-8 JSON lines, at most 2 MiB per message. PCM is finite float32, base64 encoded, with explicit dimensions; each accepted audio message has one/two channels and at most 8192 frames. No Python pickle or arbitrary command evaluation is used. Native stdout is redirected away from the protocol pipe before loading DLLs.

Configuration is transactional: a candidate process must load the complete requested rack before replacing the current one. A failed load retains the previous process and cached descriptors. Native calls have an owned-process kill watchdog. Native editor calls intentionally remain open until the user closes the window or the application kills its child on shutdown.

Structural operations occur with audio stopped. Stream reset drains the previous broker generation, resets native audio buffers, then starts a fresh bounded pipeline without discarding the native editor's current runtime state. Explicit Restart reloads the normalized saved configuration. No automatic crash/restart loop repeatedly loads a faulty binary.

At shutdown TouchMusic stops scanning, kills owned native children and closes its audio/conversion resources. Other applications and unrelated processes are never terminated.

## Plugin Center and compatibility

Discovery enumerates paths, treating a `.vst3` directory as one bundle. It does not instantiate plugins. Explicit scans use a separate worker and produce binary-hash/version/rate/block/parameter/impulse/RPC evidence. A failure quarantines that Plugin Center entry until a successful rescan. The direct FX file picker remains an explicit advanced loading path.

The catalog separates official publisher identity, license label, reviewed download asset and measured compatibility. Pinned downloads are TDR Nova 2.2.3, SnapTune 2.4.0 and LyraTune 0.6.7. It is staged as an archive and never automatically executed/extracted. The SHA-256 is an observed integrity pin, not a publisher signature. Community catalogs are reference material only.

Native editors use the actual loaded plugin instance on the worker's main thread. The GUI remains available; audio start and rack changes are blocked until the editor closes. Exposed parameters synchronize afterward. Full opaque state persistence across restarts/projects is not implemented yet.

## Gesture Learn and Motion Score

Gesture Learn temporarily disarms performance output. It establishes axis baselines, accepts a deliberate dominant movement, binds the chosen plugin knob, and times out after ten seconds. Pose actions do not execute during learning.

Motion Score v1 stores at most 4096 finite beat-ordered events. Targets are validated against supported movement/action names. Recording captures filtered movement values and deliberate physical pose actions, so a macro is recorded once rather than duplicated with every expanded action. Playback calls the existing gesture dispatchers and never starts merely because a project was opened. Rehearsal and learning remain separate modes.

Current playback is serviced by the 100 ms UI timer. It follows elapsed audio frames with the current beat period and is not sample-accurate host automation. Editing, row deletion, explicit JSON import/export and saved-performance persistence exist; envelope editing and deterministic scheduling are next-stage work.

## DAW and instrument boundaries

The existing VST3 Control Bridge remains version 0.4.0 and retains its protocol/UID/ten controls. It passes DAW audio unchanged and emits bounded automation/timing packets to an opt-in loopback receiver. It is separate from the isolated external-FX worker. Full processed AI audio return and an isolated instrument/MIDI synthesis bus are still planned. Neither is implied by the new Plugin Center.

## Compatibility contract

Existing v1 performance archives, normalized FX settings and gesture mappings remain readable. New Motion Score data is optional and never auto-plays. A saved external rack still requires explicit review/load. Preserving old mono loop assets avoids an untested schema change. Unknown/malformed automation is rejected before replacing a score. Future stereo assets, plugin blobs and audio bridge state require versioned, tested migrations.

## dev2: separate synth and DAW audio buses

InstrumentBus reuses the owned-process pipeline with a separate InstrumentBackend. Timestamped channel-zero MIDI is rendered in the worker; bounded commands and a bounded event heap track note generations so an earlier note-off cannot terminate a retrigger. Panic invalidates old queued commands. Silent worker input means failure falls back to silence rather than microphone audio. The stereo synth is mixed after the vocal rack and exported as its own stem. Native instruments are never automatically loaded from a session.

The new Audio Bridge uses a distinct VST3 UID. Its audio callback only copies samples and exchanges bounded SPSC queues. A native network thread owns UDP; the Python receiver is loopback-only and processes one source at 48 kHz without a simultaneous PortAudio stream. Packet identity, source frame, shape, rate, kind and finite PCM are checked; duplicate/foreign packets are rejected. The DAW owns the input clock, eliminating a second device clock for this route. Missing returns use the matching delayed dry block.

The native plugin reports 4096 transport frames. This is not total AI/FX latency compensation: converter and effect-worker delays still apply, and parameter automation is not sample-accurate across the process boundary. Offline fast rendering and non-48-kHz wet return are explicitly unsupported. Actual native-host DSP return was checked; FL Studio and real-model conversion inside a DAW remain pending.
