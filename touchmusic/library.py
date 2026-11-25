"""Local reference audio and persistent settings."""
import hashlib
import json
import os
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from math import gcd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def read_audio(path, rate=48000):
    audio, original_rate = sf.read(str(path), dtype='float32', always_2d=True)
    audio = audio.mean(axis=1)
    if not len(audio) or not np.isfinite(audio).all():
        raise ValueError('This audio file is empty or contains invalid samples.')
    if original_rate != rate:
        factor = gcd(original_rate, rate)
        audio = resample_poly(audio, rate // factor, original_rate // factor)
    return np.asarray(audio, dtype=np.float32)


class VoiceLibrary:
    def __init__(self, directory=DATA / 'voices'):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.manifest = self.directory / 'library.json'
        self.voices = json.loads(self.manifest.read_text('utf-8')) if self.manifest.exists() else []

    def import_file(self, source, name=None):
        audio = read_audio(source, 24000)
        if len(audio) < 24000:
            raise ValueError('Choose a reference at least one second long.')
        if np.max(np.abs(audio)) < .0001:
            raise ValueError('This reference is silent.')
        identity = hashlib.sha256(audio.tobytes()).hexdigest()[:20]
        existing = next((v for v in self.voices if v['id'] == identity), None)
        if existing:
            return existing
        destination = self.directory / (identity + '.wav')
        sf.write(destination, audio, 24000, subtype='PCM_16')
        voice = {'id': identity, 'name': name or Path(source).stem.replace('_', ' '),
                 'file': destination.name, 'seconds': round(len(audio) / 24000, 2)}
        self.voices.append(voice)
        save_json(self.manifest, self.voices)
        return voice

    def path(self, voice):
        return self.directory / voice['file']

    def restore_references(self, references):
        known = {voice['id'] for voice in self.voices}
        additions = []
        for voice, audio in references:
            target = self.path(voice)
            if voice['id'] in known and target.is_file():
                continue
            temp = target.with_suffix('.tmp')
            temp.write_bytes(audio)
            os.replace(temp, target)
            if voice['id'] not in known:
                additions.append(voice)
                known.add(voice['id'])
        if additions:
            save_json(self.manifest, [*self.voices, *additions])
            self.voices.extend(additions)

    def rename(self, identity, name):
        name = name.strip()
        if not name:
            raise ValueError('Enter a voice name.')
        next(v for v in self.voices if v['id'] == identity)['name'] = name
        save_json(self.manifest, self.voices)
