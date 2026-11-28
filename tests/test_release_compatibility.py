import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import tomllib
import numpy as np
import pytest
from touchmusic.project import load_project, save_project, validate_settings
from touchmusic.plugin_rack import PluginRack
from touchmusic.runtime import VERSION
from touchmusic.audio import AudioEngine

ROOT = Path(__file__).resolve().parents[1]


def test_archived_v04_performance_roundtrips_without_new_optional_data(tmp_path):
    fixture = json.loads((Path(__file__).parent/'fixtures/v0.4.0-performance.json').read_text())
    raw = base64.b64decode(fixture['archive_base64'], validate=True)
    assert hashlib.sha256(raw).hexdigest() == fixture['archive_sha256']
    old = tmp_path/'old.touchmusic'
    old.write_bytes(raw)
    settings, assets, voices = load_project(old)
    assert settings['music']['bpm'] == 112 and settings['mapping']['Right'] == 'Reverb'
    PluginRack.validate(settings['plugins'])
    np.testing.assert_array_equal(assets['loop-1'], .125)
    assert 'motion_score' not in settings
    new = tmp_path/'roundtrip.touchmusic'
    save_project(new, settings, assets)
    restored, copied, _ = load_project(new)
    assert restored == settings
    np.testing.assert_array_equal(copied['loop-1'], assets['loop-1'])


def test_bad_optional_score_is_rejected_during_project_validation():
    with pytest.raises(ValueError):
        validate_settings({'motion_score': {'version': 1, 'events': [
            {'beat': 0, 'kind': 'level', 'target': 'Reverb', 'value': 99}]}})
    validate_settings({'music': {'bpm': 120}})


def test_editor_reservation_blocks_audio_before_any_hardware_query():
    engine = AudioEngine()
    engine.rack.editor_pending = True
    with pytest.raises(ValueError, match='native plugin editor'):
        engine.start(None, None)


def test_development_build_cannot_pass_stable_publishing_gate():
    spec = importlib.util.spec_from_file_location('release_version', ROOT/'tools/release_version.py')
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    assert release.stable_release('0.5.0')
    for value in ('0.5.0.dev1', '0.5.0rc1', '0.5.0+local', 'v0.5.0', '0.5'):
        assert not release.stable_release(value)
    assert VERSION == tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8-sig'))['project']['version']
