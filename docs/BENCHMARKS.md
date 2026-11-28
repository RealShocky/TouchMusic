# Release benchmarks and validation evidence

Recorded 2026-11-28 on Windows 10.0.26300, Python 3.11.9 and NumPy 1.26.4. Automated/software measurements below do not establish live microphone, speaker, camera, listening or DAW quality. FL Studio testing is delegated to external testers.

## Synthetic audio comparison

`tools/benchmark_audio.py` renders 2000 x 512-frame blocks at 48 kHz after 64 warmup blocks: fixed 220 Hz input, default built-in effects, no AI/external effects/webcam/device stream. Published v0.4.0 and current development source run in sequential fresh processes. The desktop is not otherwise controlled; short timings are noisy.

| Measurement | v0.4.0 | 0.5.0.dev3 |
| --- | --- | --- |
| Wall seconds | 0.398451 | 0.556497 |
| Process CPU seconds | 0.375 | 0.5625 |
| Median block ms | 0.1899 | 0.24575 |
| P95 block ms | 0.239605 | 0.443345 |
| Maximum block ms | 0.6461 | 1.4269 |
| Peak process memory bytes | 6.6945e+07 | 6.7158e+07 |
| Synthetic deadline misses | 0 | 0 |

Both represent 21.333 seconds of audio, rendered faster than real time. Candidate P95 is higher in this run; these are measured compute costs, not driver latency or live CPU utilization. Neither run measures physical dropouts or input/output round trip. System-wide NVIDIA snapshots include unrelated applications and cannot attribute GPU usage to TouchMusic.

Raw [baseline](verification/benchmark-0.4.0.json) and [dev3](verification/benchmark-0.5.0.dev3.json). Historical dev1/dev2 records remain available without replacing them.

## Actual GPU conversion comparison

`tools/benchmark_ai.py` runs the actual local Seed-VC backend on the same two private references, two-second source and default four inference steps. The reports export metrics only. RTX 5060, PyTorch 2.11.0+cu128, sequential fresh processes, offline cached model assets. Both source revisions have the same neural backend SHA-256, so this is a preservation/measurement check, not evidence of a faster new model.

| Measurement | v0.4.0 | 0.5.0.dev3 |
| --- | --- | --- |
| Model load seconds | 38.0343 | 15.512 |
| Conversion CPU seconds | 2.15625 | 2.10938 |
| Peak process memory bytes | 3.59527e+09 | 3.59848e+09 |
| CUDA allocated peak bytes | 2.05771e+09 | 2.05771e+09 |
| CUDA reserved peak bytes | 2.29638e+09 | 2.29638e+09 |
| First two-second conversion | 1.007924 s | 0.604661 s |
| Second two-second conversion | 0.378978 s | 0.374531 s |

Load/first-call variation includes cache and initialization effects. Two calls are insufficient for throughput or similarity guarantees. Source/reference names and audio stay private. Raw [baseline GPU](verification/ai-benchmark-0.4.0.json) and [dev3 GPU/native return](verification/ai-benchmark-0.5.0.dev3.json).

The dev3 native host probe also passed real streaming CUDA conversion through TouchMusic Audio Bridge: 750 packets, no input packet gaps, zero dropped conversion chunks, 619 matched real-converted output blocks and finite nonzero stereo. It recorded **122 converter underruns** and last inference time about 409.3 ms. Underruns are converter availability counters, not measured device dropouts. They remain a production performance limitation. This probe used actual native hosting, no physical audio or DAW.

## Endurance and worker lifecycle

`tools/verify_performance.py` rendered 337500 blocks, representing 3600 seconds, in 120.324 wall seconds. Every output was finite and bounded; zero compute blocks exceeded 10.667 ms, maximum 9.4593 ms, CPU 117.734 s, peak process memory 69,279,744 bytes. Ten real plugin restart/state cycles completed with zero owned workers left alive. [Raw report](verification/software-endurance-dev3.json).

This accelerated test is not a one-hour real-time hardware soak. It excludes webcam/AI/physical devices from the DSP loop; the optional worker cycle is separate. A named-hardware 60-minute combined-load run, trend-based memory leak check and physical dropout/round-trip measurements remain required.

## Plugin and bridge timing

The external rack intentionally adds 2048 frames, 42.667 ms at 48 kHz. Audio Bridge reports 4096 transport frames, 85.333 ms. AI, vendor plugin DSP and driver latency are additional; full compensation remains unfinished. Scanner impulse onset is the default effect response, not declared plugin or total hardware latency.

See the [exact compatibility matrix](PLUGIN_COMPATIBILITY.md) for per-plugin rates/blocks, parameter sweeps, state/editor results and failed cases. Both compiled bridges passed 47 SDK validator checks each. Actual control hosting and 90-block standalone DSP audio return pass. Automated Qt/worker/protocol/MIDI/state/transport/device-failure checks retain v0.4.0 behavior. Package metadata, installed startup and allowlists are recorded in [development checks](verification/development-checks.json).

## Remaining release verification

Actual microphone/headphones, webcam gestures, listening quality, hardware disconnect/reconnect, combined-load soak, full delay compensation, signed/clean-machine distribution and DAW-version-specific wet-AI routing remain unverified. Pluginval is planned. Never substitute a unit-test count, SDK result, GPU run or synthetic endurance result for these checks.
