# VST3 plugin compatibility matrix

Updated 2026-11-28. A catalog listing means a publisher was identified, not that its binary was loaded. Windows x64 is the tested host platform. Results describe exact binaries and scenarios only.

## Measured results

| Plugin | Exact version | Host / test | Result | Timing / automation | Editor / hardware / DAW |
| --- | --- | --- | --- | --- | --- |
| TDR Nova | 2.2.3, Windows x64 | Pedalboard 0.9.26 in owned child; 48 kHz; 100 x 512-frame stereo blocks | Passed loading, finite stereo output and normalized parameter readback; 76 parameters | RPC p50 0.666 ms / p95 0.933 ms in scan; default impulse onset 184 samples; automated parameter `band_1_selected` | Native editor not tested; no mic/speaker round trip; FL Studio not tested |
| TDR Nova | 2.2.3, same binary | Isolated scheduled rack; 104 blocks; nominal 11 ms pacing | Passed finite stereo output, zero worker errors and zero fallback segments after dirty-parameter optimization | 2048-frame worker schedule; brief synthetic pacing, not a hardware dropout test | No hardware or DAW validation |
| TouchMusic Control Bridge | 0.4.0, Windows x64 | Steinberg SDK validator and actual Pedalboard host during v0.4.0 release | 47 validator tests passed; unchanged native audio passthrough and UDP automation verified | Ten controls and soft host timing; not an AI audio bridge | FL Studio and hardware routing pending |

TDR Nova binary SHA-256:

`a9bd0fbfb93137576ddd192e683285d9e410169eb6890cf07e6440e1e2211325`

Developer-hosted 2.2.3 portable ZIP observed SHA-256:

`9bb52d042bd95dd85456da66316347a00d865d9d3f6652333e1a2bc195cb8907`

The archive hash is an integrity pin observed during development, not an independent publisher signature. The impulse onset includes the default effect's response and is not declared plugin latency, total TouchMusic latency, AI latency or a measured hardware round trip. RPC timing is from this development host and is not a general latency promise.

## Reviewed candidates, not yet compatibility tested

| Candidate | Official source | Publisher license label | Tested version / result |
| --- | --- | --- | --- |
| SnapTune | https://github.com/NicoFerni/snaptune | AGPL-3.0 | None; publisher's 2.7 ms live-mode claim is not a TouchMusic measurement |
| Graillon 3 | https://www.auburnsounds.com/products/Graillon.html | Proprietary free edition | None; edition/features/license need asset-specific review |
| MAutoPitch | https://www.meldaproduction.com/MAutoPitch | Proprietary freeware | None |
| LyraTune | https://github.com/333stack/LyraTune | AGPL-3.0 | None |
| OpenVoxTuner | https://github.com/EiffelBS/OpenVoxTuner | AGPL-3.0 | None; upstream ARA/standalone features do not establish TouchMusic support |
| NoteForge | https://github.com/bighandfoot/NoteForge | AGPL-3.0 | None; correct repository is the audio editor, not similarly named note-taking apps |
| TDR Kotelnikov | https://www.tokyodawn.net/tdr-kotelnikov/ | Proprietary freeware | None |
| Valhalla Supermassive | https://valhalladsp.com/shop/reverb/valhalla-supermassive/ | Proprietary freeware | None |
| Dragonfly Reverb | https://github.com/michaelwillis/dragonfly-reverb | GPL-3.0 | None; confirm the chosen release actually supplies the required VST3 format |
| ChowMatrix | https://github.com/Chowdhury-DSP/ChowMatrix | BSD-3-Clause | None; binary dependencies may have additional terms |
| BYOD | https://github.com/Chowdhury-DSP/BYOD | GPL-3.0 | None |
| MFreeFXBundle | https://www.meldaproduction.com/MFreeFXBundle | Proprietary free edition | None; verify individual effects |
| Surge XT | https://github.com/surge-synthesizer/surge | GPL-3.0 | None; dedicated instrument bus planned |
| Cardinal | https://github.com/DISTRHO/Cardinal | GPL-3.0 / bundled component terms | None; dedicated instrument bus planned |

No third-party plugin binaries are distributed in TouchMusic. Source license labels are not blanket permission to redistribute every release binary, artwork or dependency. Catalog downloads use official sources; unsupported/unreviewed assets open publisher pages.

## Recording a result

Use Plugin Center -> Discover -> select binary -> enter its exact publisher version -> Scan selected. Reports include a binary hash, UTC test time, platform, rate/block/count, finite stereo probe, parameter readback, impulse onset and RPC timing. An unknown version stays Unknown and must not be converted into a guessed compatibility version.

Record separate editor open/close checks, sustained automation, pluginval logs, listening, hardware and DAW/version checks as they are actually performed. A failed scan quarantines the Plugin Center entry; replacing the binary requires a fresh successful scan. Do not treat the 100-block smoke test as a soak test or a complete preset certification.
