# TouchMusic Control Bridge 0.4.0

Experimental Windows x64 VST3 control bridge. Run the TouchMusic standalone app alongside your DAW.

1. Extract the complete `.vst3` bundle into a folder your DAW scans. Keep its Contents directory intact. Add the extracted folder to your DAW plugin search paths if needed.
2. Load TouchMusic Control Bridge on a DAW mixer insert. It passes the insert audio through unchanged.
3. Open TouchMusic > VST3 bridge and enable the localhost receiver.
4. Choose whether to follow DAW tempo/musical position, accept effect automation, or follow transport for backing playback. Start standalone audio yourself when ready.
5. Automate the plugin parameters using the DAW's generic plugin controls. One receiver follows one plugin instance; Forget current plugin instance allows selecting another sender.

## Automation

Ten normalized controls: Reverb, Delay, Robot, Pitch, Tune strength, Master, Formant, Voice slot, Chord, and Bridge bypass. Pitch maps 0..1 to -12..+12 semitones, Formant to -5..+5, Voice slot to slots 1..5, and Chord to I..VII. Others use the corresponding 0..100% range. Bypass prevents incoming controls from being applied and does not change dry DAW audio.

The receiver binds only to 127.0.0.1:26789 and validates bounded JSON packets. There is no remote command execution, file access, audio transport, or network listener in the native audio callback. A worker sends the latest scalar controls at 20 Hz.

## Timing limits

Tempo following supports 40..240 BPM. Host PPQ is used to reanchor the standalone scheduling clock with elapsed-time compensation. Control application runs on the UI timer and audio callback, so sample-accurate cross-application sync is not claimed. First lock, a seek over one beat, or host stop finishes active capture and cancels pending scheduled actions. Existing loops remain at their original playback speed and continue free-running; automatic pitch-preserving time stretch and loop transport chase are future work. Optional backing-track chase uses host sample position and requires a host that provides valid timing.

This plugin does not send processed AI vocals into the DAW. Use an audio interface loopback or virtual audio route for that. The AI engine remains in the standalone process.

## Build

Requires CMake 3.25+, C++17, and a native compiler. On Windows use Visual Studio 2022 Build Tools with the C++ workload and Windows SDK:

    cmake -S native/control_bridge -B native-build -A x64
    cmake --build native-build --config Release --target TouchMusicControlBridge

CMake fetches pinned Steinberg VST3 SDK 3.8.1 sources. Set TOUCHMUSIC_VST3_SDK to a complete local SDK checkout to build without fetching. The SDK validator runs after compilation. Source uses portable socket branches, but this release is built and verified on Windows only.

The SDK's MIT notice is included in STEINBERG-LICENSE.txt. VST is a trademark of Steinberg Media Technologies GmbH.
