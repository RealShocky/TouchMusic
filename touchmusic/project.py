"""Portable skit archives. Members are read without extracting paths."""
import io
import json
import os
import re
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import soundfile as sf

ASSETS = ('backing', 'loop-1', 'loop-2', 'loop-3', 'loop-4')
RATE = 48000


def save_project(path, settings, assets, voices=()):
    path = Path(path)
    voices = tuple(voices)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.tmp', delete=False) as file:
        temporary = Path(file.name)
    try:
        with ZipFile(temporary, 'w', ZIP_DEFLATED, compresslevel=1) as archive:
            archive.writestr('project.json', json.dumps({'version': 1, 'settings': settings,
                             'assets': list(assets), 'voices': [voice for voice, _ in voices]}))
            for key, audio in assets.items():
                buffer = io.BytesIO()
                sf.write(buffer, audio, RATE, format='WAV', subtype='FLOAT')
                archive.writestr(f'audio/{key}.wav', buffer.getvalue())
            for voice, reference_path in voices:
                archive.write(reference_path, f"voices/{voice['id']}.wav")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read(archive, name, maximum):
    info = archive.getinfo(name)
    if info.file_size > maximum:
        raise ValueError(f'Project member is too large: {name}')
    return archive.read(info)


def load_project(path):
    with ZipFile(path) as archive:
        manifest = json.loads(_read(archive, 'project.json', 2 * 1024 * 1024))
        if not isinstance(manifest, dict) or manifest.get('version') != 1:
            raise ValueError('Unsupported TouchMusic project format.')
        assets, voices = {}, []
        for key in manifest['assets']:
            if key not in ASSETS or key in assets:
                raise ValueError('Invalid project audio entry.')
            limit = RATE * (3600 if key == 'backing' else 120)
            with sf.SoundFile(io.BytesIO(_read(archive, f'audio/{key}.wav', 4 * limit + 256))) as stream:
                if stream.samplerate != RATE or stream.channels != 1 or not 0 < stream.frames <= limit:
                    raise ValueError(f'Invalid project audio: {key}')
                audio = stream.read(dtype='float32')
            if not np.isfinite(audio).all():
                raise ValueError(f'Invalid samples in {key}')
            assets[key] = audio
        if len(manifest['voices']) > 100:
            raise ValueError('Project contains too many references.')
        for voice in manifest['voices']:
            identity, name = voice['id'], voice['name']
            if not re.fullmatch(r'[0-9a-f]{20}', identity) or not isinstance(name, str) or not name.strip():
                raise ValueError('Invalid project voice entry.')
            wav = _read(archive, f'voices/{identity}.wav', 24 * 1024 * 1024)
            with sf.SoundFile(io.BytesIO(wav)) as stream:
                if stream.format != 'WAV' or stream.samplerate != 24000 or stream.channels != 1 or stream.frames < 24000:
                    raise ValueError(f'Invalid reference audio: {name}')
                seconds = round(stream.frames / 24000, 2)
            voices.append(({'id': identity, 'name': name, 'file': identity + '.wav', 'seconds': seconds}, wav))
        settings = manifest['settings']
        validate_settings(settings)
    return settings, assets, voices


def validate_settings(settings, include_scenes=True):
    if not isinstance(settings, dict):
        raise ValueError('Invalid project settings.')
    for key, kind in {'effects': dict, 'mapping': dict, 'voice_slots': dict, 'music': dict,
                      'loop_levels': list, 'muted_loops': list, 'loop_selected': int, 'track_name': str}.items():
        if key in settings and not isinstance(settings[key], kind):
            raise ValueError(f'Invalid project setting: {key}')
    if not 0 <= settings.get('loop_selected', 0) < 4:
        raise ValueError('Invalid selected loop.')
    if include_scenes:
        scenes = settings.get('scenes', {})
        if not isinstance(scenes, dict):
            raise ValueError('Invalid scene list.')
        for scene in scenes.values():
            validate_settings(scene, include_scenes=False)
