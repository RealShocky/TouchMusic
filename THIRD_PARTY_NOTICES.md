# Third-party components

TouchMusic uses third-party packages installed by `Setup.cmd` and the pinned runtime in `requirements.txt`. Each dependency retains its own license and notices.

## Seed-VC

- Source repository is https://github.com/Plachtaa/seed-vc
- Setup revision is `51383efd921027683c89e5348211d93ff12ac2a8`.
- Setup downloads the source into `vendor/seed-vc`, including its upstream license.
- `prepare_seed.py` moves the optional `dac.nn.quantize.VectorQuantize` import into its conditional branch so the singing inference path can load without installing the training codec.
- TouchMusic loads the pitch-conditioned inference path through `touchmusic/neural.py`.

## Downloaded model assets

The AI engine downloads model assets from Plachta/Seed-VC, lj1995/VoiceConversionWebUI, funasr/campplus, NVIDIA BigVGAN, and the model loaders used by the pinned Seed-VC revision. Consult the corresponding model repositories for their terms and notices. These assets are downloaded into local caches.

## Other runtime packages

The application uses PySide6, NumPy, SciPy, sounddevice, SoundFile, Pedalboard, MediaPipe, OpenCV, PyTorch, torchaudio, torchvision, Transformers, Hugging Face Hub, librosa, and their dependencies. Their distribution metadata contains license and copyright information.

## Voice references

Users import their own audio references. This source repository contains no reference voices, artist recordings, backing tracks, or generated performances.

## TouchMusic licensing

The repository owner has not selected a license for the TouchMusic application source. Repository visibility alone does not grant an open-source license. Third-party components remain governed by their respective licenses.
