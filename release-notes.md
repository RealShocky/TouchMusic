# TouchMusic 0.2.0

Standalone performance and session upgrades.

- Reference-quality reports and suggested 1-8 second sections, with manual audition and selection.
- Loop overdubbing with adjustable feedback and four levels of committed-take undo/redo.
- One- or two-bar count-in and exact 1/2/4/8-bar capture, including automatic stop.
- Background recovery of completed loops, backing, voice references, and settings.
- Ordered setlists with per-song skit recall and Next/Previous song gesture actions.
- Optional loop-edge fades, progress bars, countdowns, and clearer capture status.
- Preview media loads when auditioning, reducing unnecessary player work during reference analysis.

## Downloads

The Windows Setup ZIP requires 64-bit Python 3.11 and Git. Extract, run Setup.cmd once, then Launch.cmd. Dependencies and the optional singing runtime download during setup. This is a setup archive, not a dependency-free executable.

Alternatively: `py -3.11 -m pip install --upgrade touchmusic`, then run `touchmusic`. Install the optional character engine with `touchmusic --setup-ai`.

Personal voices, recordings, model weights, and caches are excluded. Reference suggestions use level heuristics, not vocal isolation. Recovery excludes active capture and undo history. Setlist song recall stops audio and disarms gestures. Live FL Studio routing validation is pending.

Automated behavior tests, desktop layout checks, and package installation are checked for this release. SHA256SUMS.txt accompanies the release artifacts.
