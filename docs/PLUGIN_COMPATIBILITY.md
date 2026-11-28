# VST3 plugin compatibility matrix

Updated 2026-11-28. A catalog listing means a publisher was identified, not that its binary was loaded. Windows x64 is the tested host platform. Results describe exact binaries and scenarios only.

## Measured results

| Plugin | Exact version | Host / test | Result | Timing / automation | Editor / hardware / DAW |
| --- | --- | --- | --- | --- | --- |
| TDR Nova | 2.2.3, Windows x64 | Pedalboard 0.9.26 in owned child; 48 kHz; 100 x 512-frame stereo blocks | Passed loading, finite stereo output and normalized parameter readback; 76 parameters | RPC p50 0.666 ms / p95 0.933 ms in scan; default impulse onset 184 samples; automated parameter `band_1_selected` | Native editor not tested; no mic/speaker round trip; FL Studio not tested |
| TDR Nova | 2.2.3, same binary | Isolated scheduled rack; 104 blocks; nominal 11 ms pacing | Passed finite stereo output, zero worker errors and zero fallback segments after dirty-parameter optimization | 2048-frame worker schedule; brief synthetic pacing, not a hardware dropout test | No hardware or DAW validation |
| SnapTune | 2.4.0, Windows x64 | Pedalboard 0.9.26 in owned child; 48 kHz; 100 x 512-frame stereo blocks | Passed load, finite stereo and normalized readback; 30 parameters | RPC p50 0.595 ms / p95 0.840 ms; default impulse onset 2985 samples; parameter `key` | Editor, hardware and DAW not tested |
| LyraTune | 0.6.7, Windows x64 | Pedalboard 0.9.26 in owned child; 48 kHz; 100 x 512-frame stereo blocks | Passed load, finite stereo and normalized readback; 28 parameters | RPC p50 0.599 ms / p95 0.787 ms; default impulse onset 357 samples; parameter `bypass` | Editor, hardware and DAW not tested |
| TouchMusic Control Bridge | 0.4.0, Windows x64 | Steinberg SDK validator and actual Pedalboard host during v0.4.0 release | 47 validator tests passed; unchanged native audio passthrough and UDP automation verified | Ten controls and soft host timing; not an AI audio bridge | FL Studio and hardware routing pending |

TDR Nova binary SHA-256:

`a9bd0fbfb93137576ddd192e683285d9e410169eb6890cf07e6440e1e2211325`

Developer-hosted 2.2.3 portable ZIP observed SHA-256:

`9bb52d042bd95dd85456da66316347a00d865d9d3f6652333e1a2bc195cb8907`

The archive hash is an integrity pin observed during development, not an independent publisher signature. The impulse onset includes the default effect's response and is not declared plugin latency, total TouchMusic latency, AI latency or a measured hardware round trip. RPC timing is from this development host and is not a general latency promise.

## Catalog sources and remaining compatibility work

| Candidate | Official source | Publisher license label | Tested version / result |
| --- | --- | --- | --- |
| SnapTune | https://github.com/NicoFerni/snaptune | AGPL-3.0 | 2.4.0 smoke test above; publisher's 2.7 ms live-mode claim is not a TouchMusic measurement |
| Graillon 3 | https://www.auburnsounds.com/products/Graillon.html | Proprietary free edition | None; edition/features/license need asset-specific review |
| MAutoPitch | https://www.meldaproduction.com/MAutoPitch | Proprietary freeware | None |
| LyraTune | https://github.com/333stack/LyraTune | AGPL-3.0 | 0.6.7 smoke test above |
| OpenVoxTuner | https://github.com/EiffelBS/OpenVoxTuner | AGPL-3.0 | None; upstream ARA/standalone features do not establish TouchMusic support |
| NoteForge | https://github.com/bighandfoot/NoteForge | AGPL-3.0 | None; correct repository is the audio editor, not similarly named note-taking apps |
| TDR Kotelnikov | https://www.tokyodawn.net/tdr-kotelnikov/ | Proprietary freeware | None |
| Valhalla Supermassive | https://valhalladsp.com/shop/reverb/valhalla-supermassive/ | Proprietary freeware | None |
| Dragonfly Reverb | https://github.com/michaelwillis/dragonfly-reverb | GPL-3.0 | None; confirm the chosen release actually supplies the required VST3 format |
| ChowMatrix | https://github.com/Chowdhury-DSP/ChowMatrix | BSD-3-Clause | None; binary dependencies may have additional terms |
| BYOD | https://github.com/Chowdhury-DSP/BYOD | GPL-3.0 | None |
| MFreeFXBundle | https://www.meldaproduction.com/MFreeFXBundle | Proprietary free edition | None; verify individual effects |
| Surge XT | https://github.com/surge-synthesizer/surge | GPL-3.0 | See dev2 results below; instrument hosting exists and vendor compatibility remains specific to each tested binary |
| Cardinal | https://github.com/DISTRHO/Cardinal | GPL-3.0 / bundled component terms | See dev2 results below; instrument hosting exists and vendor compatibility remains specific to each tested binary |

No third-party plugin binaries are distributed in TouchMusic. Source license labels are not blanket permission to redistribute every release binary, artwork or dependency. Catalog downloads use official sources; unsupported/unreviewed assets open publisher pages.

## Recording a result

Use Plugin Center -> Discover -> select binary -> enter its exact publisher version -> Scan selected. Reports include a binary hash, UTC test time, platform, rate/block/count, finite stereo probe, parameter readback, impulse onset and RPC timing. An unknown version stays Unknown and must not be converted into a guessed compatibility version.

Record separate editor open/close checks, sustained automation, pluginval logs, listening, hardware and DAW/version checks as they are actually performed. A failed scan quarantines the Plugin Center entry; replacing the binary requires a fresh successful scan. Do not treat the 100-block smoke test as a soak test or a complete preset certification.

Additional exact binary records: [SnapTune 2.4.0](verification/snaptune-2.4.0-scan.json), [LyraTune 0.6.7](verification/lyratune-0.6.7-scan.json). The catalog's pinned SnapTune/LyraTune archive hashes match GitHub release asset digest metadata from their publisher repositories. Native binaries are not redistributed.

A two-effect SnapTune 2.4.0 -> TDR Nova 2.2.3 scheduled chain completed 72 paced blocks with zero fallback segments before the owned worker was deliberately terminated. TouchMusic detected the exit, returned finite stereo delayed-dry fallback and successfully restarted the rack. This is software fault injection, not an audio-device or listening test. [Raw result](verification/plugin-chain-fault.json).

## dev2 Audio Bridge and instrument results

TouchMusic Audio Bridge 0.5.0: 47 SDK validator checks passed. Actual Pedalboard hosting at 48 kHz sent/returned 90 stereo blocks with zero gaps/rejections; returned audio matched standalone DSP after the 4096-frame transport schedule. No real AI model, physical audio device or DAW was used. [Raw report](verification/native-audio-return.json).

Surge XT 1.3.4 Windows x64: finite stereo chord rendering passed across 70 paced 512-frame blocks at 48 kHz, with zero worker errors/fallback. 2855 raw normalized parameters were exposed. Publisher-supported portable user data was used; a dedicated normalized adapter avoids expensive speculative text/range inference. No factory-content/preset library certification, listening, editor or DAW check is claimed. [Exact binary report](verification/surge-xt-1.3.4.json).

## dev3 expanded verification

| Plugin / version | Rates and blocks | Parameter automation | Native state / editor |
| --- | --- | --- | --- |
| TDR Nova 2.2.3 | 44.1/48/96 kHz x 128/512/1024 frames: 9/9 pass | Up to four exposed parameters swept across normalized range in each case | 4968-byte opaque state portable round trip passed; editor not tested |
| SnapTune 2.4.0 | Same matrix: 6/9 pass; every 96 kHz case fails this host's valid full-block audio contract | Sweeps pass at tested 44.1/48 kHz | Actual editor API opened and event-closed in 0.844 s; no manual visual interaction claimed |
| LyraTune 0.6.7 | Same matrix: 9/9 pass | Up to four exposed parameters swept in each case | Opaque restore/editor not independently certified |
| Surge XT 1.3.4 | 48 kHz, 512 frames, 70 paced stereo chord blocks | 3047 normalized controls after preset initialization (2855 in the earlier dev2 pre-initialization snapshot) | See reviewed-archive probe below; factory content and editor usability remain unverified |

Each matrix case uses a fresh owned process and 20 blocks after the primary 100-block scan. SnapTune's failure is a result of the current host/block contract, not a universal vendor incompatibility claim. All exact binaries, per-case timing and swept parameter names are in [matrix JSON](verification/effects-matrix-dev3.json). Normalized sweeps are compatibility probes, not tuning-quality listening tests.

Native [Nova state report](verification/native-state-roundtrip.json) and [SnapTune editor API report](verification/native-editor-close.json) distinguish automated API checks from visual/manual/hardware/DAW checks. No physical audio or FL Studio test was performed. FL Studio checks are delegated to external testers.

CI downloads checksum-pinned official SnapTune 2.4.0, LyraTune 0.6.7 and Surge XT 1.3.4 archives into temporary staging and saves JSON reports only. SnapTune/Lyra release pins match publisher GitHub asset digests. The Surge official archive hash is an observed integrity pin, not a publisher signature: `564e162c560af07ad4ed47fe1bfcd827cf97a575de30d06c48249aad2e7c35e6`. Third-party binaries are not published in TouchMusic artifacts.

Reviewed-archive [Surge XT state/reset/render report](verification/curated-dev3/Surge-XT.json), [SnapTune scan](verification/curated-dev3/SnapTune.json) and [LyraTune scan](verification/curated-dev3/LyraTune.json). Instrument state preparation renders a bounded 32 silent blocks with audio stopped so deferred preset loads complete before notes are accepted.
