# Release benchmarks and validation evidence

Recorded 2026-11-28 on Windows 10.0.26300, Python 3.11.9, NumPy 1.26.4. These are software measurements from this development host, not audio-hardware validation.

## Reproducible comparison

`tools/benchmark_audio.py` renders 2000 x 512-frame, 48 kHz blocks after 64 warmup blocks. Input is a fixed 220 Hz sine at amplitude 0.15. Default built-in effects are active; external plugins, AI, webcam and real audio devices are absent. Runs execute sequentially in fresh processes. The baseline source is the published v0.4.0 GitHub archive; the candidate is this development checkout.

| Measurement | v0.4.0 | v0.5.0 development | Interpretation |
| --- | --- | --- | --- |
| Audio represented | 21.333 s | 21.333 s | Computed faster than real time |
| Wall time | 0.39845 s | 0.46962 s | Includes Python scheduling and measurement overhead |
| Process CPU time | 0.375 s | 0.46875 s | Whole measured loop; not system CPU utilization |
| Median block compute | 0.18990 ms | 0.21830 ms | Candidate includes stereo mix handling |
| P95 block compute | 0.23960 ms | 0.33814 ms | Candidate regression of about 0.099 ms in this run |
| Maximum block compute | 0.64610 ms | 1.00120 ms | Short-run observation, not worst-case guarantee |
| Peak process working set | 66,945,024 bytes | 66,801,664 bytes | No native worker or AI memory included |
| Synthetic blocks exceeding 10.667 ms | 0 | 0 | Software deadline proxy only |
| Physical audio dropouts | Not measured | Not measured | Requires a running audio stream |
| Hardware input/output round trip | Not measured | Not measured | Requires loopback calibration |
| GPU AI compute / allocated peak memory | Not measured | Not measured | No model inference in this scenario |

The raw `cpu_percent_of_one_core` field describes a busy, unpaced render process. It must not be presented as live audio CPU usage. System-wide NVIDIA telemetry happened to report an RTX 5060 with about 2122 MiB in use; that includes unrelated applications and does not measure TouchMusic AI memory or performance.

Raw records: [baseline](verification/benchmark-0.4.0.json), [candidate](verification/benchmark-0.5.0-development.json). Individual runs are noisy. Broader AI/camera/plugin workloads and repeated longer tests remain required before production claims.

## Isolated effect probe

TDR Nova 2.2.3, Pedalboard 0.9.26, 48 kHz, 512 frames:

- The isolated 100-block scan passed load, finite stereo output and one normalized parameter readback.
- Scan RPC p50 was 0.666 ms and p95 0.933 ms; default impulse onset was 184 samples. This onset is not a declared/plugin/hardware round-trip latency measurement.
- A later 104-block scheduled run at nominal 11 ms pacing had zero worker errors and zero fallback segments after removing redundant unchanged parameter writes. It lasted about 1.21 seconds, so it is not a soak test.
- The scheduled external rack intentionally adds 2048 frames, 42.667 ms at 48 kHz. A v0.4 in-process rack had no equivalent scheduling buffer. Plugin DSP, built-in DSP, AI and driver delay are additional.

Raw scan: [exact binary report](verification/tdr-nova-2.2.3-scan.json). See [compatibility matrix](PLUGIN_COMPATIBILITY.md) for hash/version and unperformed checks.

## Release gate checklist

Automated: preserve all original 85 tests and run the expanded worker/protocol/queue/stereo/learning/score/UI suite. Build wheel and sdist, check metadata, install in a separate location, check the entry point and inspect the setup ZIP allowlist. Retain v0.4.0's 47 native SDK checks and actual host/control transport probe; rerun when the native bridge changes.

Still required for v0.5.0: sustained native worker/editor restarts, a 60-minute named-hardware run, webcam gestures, live mic/headphones and listening quality, model-specific CPU/GPU/memory measurements, actual audio dropouts/round-trip calibration, instrument note lifecycle and a real wet-AI DAW return. FL Studio testing is blocked until reinstallation. Never replace these with synthetic results or a passing unit-test count.

This development checkpoint passed 113 Python tests and reran 47 SDK checks against the unchanged compiled control bridge. Wheel/sdist metadata, a separate-target installed GUI/worker startup and setup archive allowlists also passed. [Verification record](verification/development-checks.json).

SnapTune 2.4.0 and LyraTune 0.6.7 also passed isolated 100-block scans. A paced SnapTune/Nova chain had zero pre-fault fallback segments, survived deliberate worker termination with finite stereo fallback, and explicitly restarted. See the compatibility matrix and raw fault report.
