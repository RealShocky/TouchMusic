# Technical debt and stability limits

This document explains implementation risks. [roadmap.md](../roadmap.md) owns feature status and priority.

| ID | Area | Current limitation | Remediation / evidence required |
| --- | --- | --- | --- |
| TD01 | External FX pipeline | 2048-frame worker scheduling delay; wet/dry fallback can change sound abruptly | Measure smaller safe windows under load, add transition handling and plugin/parallel-path latency compensation without blocking callback |
| TD02 | Native state | Exposed parameters persist, opaque programs/state do not survive reloads | Bounded content-addressed worker state, portable archive migration and tamper/size/round-trip tests |
| TD03 | Callback work | NumPy allocation, queue operations, Python/GIL and built-in DSP remain in callback | Profile under AI/camera/plugin load, preallocate where evidence identifies bottlenecks, preserve deterministic timing tests |
| TD04 | Discovery/identity | Windows x64 bundle lookup; full binary hashing can be expensive | Async identity/read paths and clear unsupported-architecture reports, bounded scan cache invalidation and platform-specific bundle lookup |
| TD05 | Rack loading UI | Configuration is process-isolated but synchronous load can pause GUI until timeout | Background transactional load with cancellation and explicit busy-state controls |
| TD06 | Native editors | Actual publisher windows have not been manually exercised in this increment | Open/close/change preset/start-stop/quit checks on exact named versions; test modal dialogs and malformed state in child only |
| TD07 | Stereo assets | Live external FX/master/WAV are stereo; existing loop/backing/reference storage stays mono | Checked schema migration, stereo asset/loop/overdub/export tests and channel-layout UX |
| TD08 | Motion timing | 100 ms UI replay granularity; abrupt tempo/host seeks lack a defined loop/restart policy | Deterministic scheduling, seek/tempo tests and sample-accurate continuous automation before DAW claims |
| TD09 | Plugin scanner | Default-settings smoke test, one rate/block size, one parameter probe | Matrix of rates/blocks/presets, parameter sweeps, pluginval, sustained worker scheduling and native crash fixtures |
| TD10 | Sustained performance | Brief synthetic/real-plugin runs do not establish stage reliability | Named-hardware 60-minute mic/camera/AI/plugin run, memory trends, device hotplug and measured audio dropouts |
| TD11 | Publishing | Setup ZIP downloads Python packages; no signed installer or offline single executable | Signing/provenance, clean-machine checks, explicit runtime requirements and reproducible dependency/build policy |
| TD12 | Sessions | New optional score is validated; broader schema migration/instance locking is unfinished | Archived v0.4 fixtures, future schema migrations and single-writer recovery ownership |
| TD13 | Platforms | Windows tested; portable Python code and upstream cross-platform support are insufficient | macOS/Linux camera/audio/model/native builds and actual device validation |
| TD14 | GPU baseline | Synthetic FX benchmark never invokes AI; nvidia-smi is system-wide telemetry | Model/reference/quality-specific GPU timing, allocated memory and listening-quality fixtures on named hardware |
| TD15 | Downloads | Three exact official archives currently reviewed and pinned | Review additional publisher assets, terms, platform/version/size/hash provenance and controlled extraction/install UX |

Do not resolve these by suppressing error counters, claiming unperformed hardware checks, or silently removing creative features. Preserve the baseline, surface degradation, and tie each fix to a measurable regression check.
