"""Offline alignment from exact streaming sample provenance.

The recorder writes one little-endian signed int64 source frame for every
wet-vocal sample. Unavailable converter output is represented by -1. These
functions run on a worker after recording closes, never on the audio callback.
"""
from contextlib import ExitStack
import os
from pathlib import Path
import tempfile
import numpy as np
import soundfile as sf


def _temporary_output(output_path, input_paths):
    output_path = Path(output_path)
    if output_path.resolve() in {Path(path).resolve() for path in input_paths}:
        raise ValueError('Choose a separate output file to preserve the original recording.')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=output_path.stem + '-', suffix='.wav', dir=output_path.parent)
    os.close(descriptor)
    return Path(name)


def align_recording(wet_path, provenance_path, output_path, recording_start_frame=0, block_frames=65536):
    """Place delayed vocal samples at their original capture time in a new WAV.

    The output has the same duration as the wet recording. Negative origins,
    pre-recording audio and origins beyond its end are omitted. Missing audio
    remains silent. If an origin occurs twice, the later received sample wins.
    The provenance sidecar must contain exactly one '<i8' value per wet frame.
    Returns counts for reporting. Original inputs and existing output survive
    validation/processing errors. Memory use is bounded by block_frames.
    """
    if block_frames < 1:
        raise ValueError('block_frames must be positive.')
    provenance_path = Path(provenance_path)
    with sf.SoundFile(str(wet_path)) as source:
        if provenance_path.stat().st_size != source.frames * 8:
            raise ValueError('Provenance length must match the wet recording frame count.')
        temporary = _temporary_output(output_path, [wet_path, provenance_path])
        aligned = 0
        try:
            with provenance_path.open('rb') as mapping, sf.SoundFile(
                str(temporary), 'w+', source.samplerate, source.channels, subtype='PCM_24'
            ) as output:
                zeros = np.zeros((min(block_frames, source.frames), source.channels), np.float32)
                remaining = source.frames
                while remaining:
                    count = min(len(zeros), remaining)
                    output.write(zeros[:count])
                    remaining -= count
                for block in source.blocks(blocksize=block_frames, dtype='float32', always_2d=True):
                    origins = np.frombuffer(mapping.read(len(block) * 8), dtype='<i8')
                    targets = origins - int(recording_start_frame)
                    valid = (origins >= 0) & (targets >= 0) & (targets < source.frames)
                    indices = np.flatnonzero(valid)
                    if not len(indices):
                        continue
                    # Seek once for each contiguous source/destination run.
                    boundaries = np.flatnonzero((np.diff(indices) != 1) | (np.diff(targets[indices]) != 1)) + 1
                    for run in np.split(indices, boundaries):
                        output.seek(int(targets[run[0]]))
                        output.write(block[run[0]:run[-1] + 1])
                    aligned += len(indices)
            os.replace(temporary, output_path)
        finally:
            temporary.unlink(missing_ok=True)
        return {'frames': source.frames, 'aligned_frames': aligned,
                'omitted_frames': source.frames - aligned, 'sample_rate': source.samplerate}


def mix_stems(stem_paths, output_path, master_gain=1., block_frames=65536):
    """Sum aligned mono/stereo stems from frame zero and soft-limit a new mix.

    Files must share a rate and channel count. Shorter files are zero-padded.
    Pass the aligned wet vocal plus accompaniment stems, excluding dry mic
    and the original unaligned wet vocal. This reconstructs a mix from stems;
    it does not reproduce historic master automation.
    """
    stem_paths = list(stem_paths)
    if not stem_paths or block_frames < 1 or not np.isfinite(master_gain):
        raise ValueError('Provide stems, a positive block size and a finite master gain.')
    with ExitStack() as stack:
        sources = [stack.enter_context(sf.SoundFile(str(path))) for path in stem_paths]
        rate, channels = sources[0].samplerate, sources[0].channels
        if any(source.samplerate != rate or source.channels != channels for source in sources):
            raise ValueError('Stem sample rates and channel counts must match.')
        length = max(source.frames for source in sources)
        temporary = _temporary_output(output_path, stem_paths)
        try:
            with sf.SoundFile(str(temporary), 'w', rate, channels, subtype='PCM_24') as output:
                for start in range(0, length, block_frames):
                    count = min(block_frames, length - start)
                    mixed = np.zeros((count, channels), np.float32)
                    for source in sources:
                        block = source.read(count, dtype='float32', always_2d=True)
                        mixed[:len(block)] += block
                    output.write(np.tanh(mixed * master_gain))
            os.replace(temporary, output_path)
        finally:
            temporary.unlink(missing_ok=True)
        return {'frames': length, 'sample_rate': rate, 'stems': len(sources)}
