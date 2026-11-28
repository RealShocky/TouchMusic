from zipfile import ZipFile
import pytest
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('verify_curated', Path(__file__).parents[1]/'tools/verify_plugins.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
extract_plugins = module.extract_plugins


def test_curated_extraction_rejects_escape_and_excludes_other_payloads(tmp_path):
    archive = tmp_path/'official.zip'
    with ZipFile(archive, 'w') as zipped:
        zipped.writestr('Example.vst3/Contents/plugin.dll', b'plugin')
        zipped.writestr('installer.exe', b'not a plugin')
    extract_plugins(archive, tmp_path/'safe')
    assert (tmp_path/'safe/Example.vst3/Contents/plugin.dll').read_bytes() == b'plugin'
    assert not (tmp_path/'safe/installer.exe').exists()
    with ZipFile(archive, 'w') as zipped:
        zipped.writestr('../escaped.vst3', b'escape')
    with pytest.raises(ValueError, match='Invalid'):
        extract_plugins(archive, tmp_path/'safe')
    assert not (tmp_path/'escaped.vst3').exists()
