# Technical debt and stability limits

This document explains implementation risks. [roadmap.md](../roadmap.md) owns feature status and priority.

| ID | Area | Current limitation | Remediation / evidence required |
| --- | --- | --- | --- |
| TD01 | External FX pipeline | 2048-frame worker scheduling delay; wet/dry fallback can change sound abruptly | Measure smaller safe windows under load, add transition handling and plugin/parallel-path latency compensation without blocking callback |
| TD02 | Native state | Bounded native state now persists; cache has no global quota/garbage collection and vendor preset coverage is narrow | Add cache reachability/retention UX, more vendor preset/program changes and interrupted-write checks; current blob/project limits and tamper/round-trip tests pass |
| TD03 | Callback work | NumPy allocation, queue operations, Python/GIL and built-in DSP remain in callback | Profile under AI/camera/plugin load, preallocate where evidence identifies bottlenecks, preserve deterministic timing tests |
| TD04 | Discovery/identity | Windows x64 bundle lookup; full binary hashing can be expensive | Async identity/read paths and clear unsupported-architecture reports, bounded scan cache invalidation and platform-specific bundle lookup |
| TD05 | Rack loading UI | Async configuration and shutdown cancellation are tested; progress/cancel UX and long vendor dialogs need broader usability checks | Keep transactional load/epoch cancellation and busy-state guards; measure user-visible progress for slow installs |
| TD06 | Native editors | Actual publisher windows have not been manually exercised in this increment | Open/close/change preset/start-stop/quit checks on exact named versions; test modal dialogs and malformed state in child only |
| TD07 | Stereo assets | Live external FX/master/WAV are stereo; existing loop/backing/reference storage stays mono | Checked schema migration, stereo asset/loop/overdub/export tests and channel-layout UX |
| TD08 | Motion timing | Local sample-clock replay exists; GUI actions use 10 ms relay, native knobs remain quantized; host seek/restart policy is undefined | Deterministic scheduling, seek/tempo tests and sample-accurate continuous automation before DAW claims |
| TD09 | Plugin scanner | Nine-case matrix and four-parameter sweeps exist; no pluginval or broad preset stress. SnapTune 2.4.0 fails 96 kHz full-block contract | Matrix of rates/blocks/presets, parameter sweeps, pluginval, sustained worker scheduling and native crash fixtures |
| TD10 | Sustained performance | Brief synthetic/real-plugin runs do not establish stage reliability | Named-hardware 60-minute mic/camera/AI/plugin run, memory trends, device hotplug and measured audio dropouts |
| TD11 | Publishing | Setup ZIP downloads Python packages; no signed installer or offline single executable | Signing/provenance, clean-machine checks, explicit runtime requirements and reproducible dependency/build policy |
| TD12 | Sessions | New optional score is validated; ownership locking passes; broader schema migration remains unfinished | Archived v0.4 fixtures, future schema migrations and cross-version handoff checks |
| TD13 | Platforms | Windows tested; portable Python code and upstream cross-platform support are insufficient | macOS/Linux camera/audio/model/native builds and actual device validation |
| TD14 | GPU baseline | Paired actual GPU inference uses the same backend/source fixtures; short streaming native return recorded 122 converter underruns | Separate cold/warm model costs, expand quality/load fixtures, improve converter scheduling and perform listening and named-hardware streaming tests |
| TD15 | Downloads | Four exact official archives currently reviewed and pinned | Review additional publisher assets, terms, platform/version/size/hash provenance and controlled extraction/install UX |

Do not resolve these by suppressing error counters, claiming unperformed hardware checks, or silently removing creative features. Preserve the baseline, surface degradation, and tie each fix to a measurable regression check.

## dev2 additions

- Complete compensation for converter/effect delay in the Audio Bridge, support offline/rate negotiation, and perform actual DAW/real-model checks before production use.
- Expand instrument preset/voice-release soak tests. Surge XT 1.3.4 has a real stereo render check; this does not certify every preset or other instruments. The normalized instrument adapter uses Pedalboard native parameter internals, so Pedalboard is pinned to 0.9.26 and adapter regression checks are required before upgrades.
- Instrument/effect loading is now asynchronous and cancellation-safe. Actual Surge XT 1.3.4 state restore is included in CI; native editor visual interactions remain untested.
