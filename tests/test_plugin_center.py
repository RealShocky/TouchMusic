from io import BytesIO
import hashlib
import numpy as np
import pytest
from touchmusic.plugin_scan import discover, scan_plugin
from touchmusic.plugin_catalog import download_plugin, DOWNLOADS
from touchmusic.gesture_learn import GestureLearner


def test_discovery_deduplicates_bundles_without_loading_native_code(tmp_path):
    root = tmp_path/'Effects'
    bundle = root/'Wide.vst3'
    binary = bundle/'Contents/x86_64-win/Wide.vst3'
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b'not executable')
    (root/'Flat.vst3').write_bytes(b'not executable')
    assert discover([root, root]) == sorted([str(bundle.resolve()), str((root/'Flat.vst3').resolve())])
    assert discover([bundle]) == [str(bundle.resolve())]


def test_failed_binary_is_quarantined_with_identity_and_no_hardware_claim(tmp_path):
    path = tmp_path/'broken.vst3'
    path.write_bytes(b'not a VST3')
    result = scan_plugin(path, '1.2.3')
    assert result['status'] == 'Failed' and result['quarantined']
    assert result['version'] == '1.2.3'
    assert len(result['binary_sha256']) == 64
    assert not result['hardware_tested'] and not result['daw_tested']


def test_download_rejects_modified_official_archive_without_leaving_partial_files(tmp_path):
    class Response(BytesIO):
        def geturl(self):
            return DOWNLOADS['TDR Nova']['url']
    with pytest.raises(ValueError, match='checksum'):
        download_plugin('TDR Nova', tmp_path, lambda *a, **k: Response(b'modified'))
    assert not list(tmp_path.iterdir())


def test_download_rejects_cross_origin_redirect(tmp_path):
    class Response(BytesIO):
        def geturl(self):
            return 'https://unreviewed.example/test.zip'
    with pytest.raises(ValueError, match='redirect'):
        download_plugin('TDR Nova', tmp_path, lambda *a, **k: Response(b'data'))
    assert not list(tmp_path.iterdir())


def test_reviewed_github_release_redirect_stages_only_hash_matched_bytes(tmp_path, monkeypatch):
    data = b'reviewed archive fixture'
    asset = {**DOWNLOADS['SnapTune'], 'sha256': hashlib.sha256(data).hexdigest()}
    monkeypatch.setitem(DOWNLOADS, 'SnapTune', asset)
    class Response(BytesIO):
        def geturl(self):
            return 'https://release-assets.githubusercontent.com/official-asset'
    path = download_plugin('SnapTune', tmp_path, lambda *a, **k: Response(data))
    assert path.read_bytes() == data
    assert list(tmp_path.iterdir()) == [path]


def test_learn_requires_deliberate_unambiguous_movement_and_times_out():
    now = [0.]
    learner = GestureLearner(lambda: now[0])
    control = {'hand': 'Right', 'x': .5, 'y': .5, 'span': .5}
    assert learner.feed([control]) is None
    assert learner.feed([{**control, 'y': .51}]) is None
    assert learner.feed([{**control, 'y': .8, 'x': .2}]) is None
    assert learner.feed([{**control, 'y': .8}]) == 'Right'
    now[0] = 11
    assert learner.feed([control]) == 'timeout'
