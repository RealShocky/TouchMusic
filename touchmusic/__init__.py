"""TouchMusic standalone performance instrument."""
import os
from pathlib import Path

_data = Path(__file__).resolve().parents[1] / 'data'
for _key, _folder in {'HF_HOME': 'models', 'HF_HUB_CACHE': 'models/hub',
                     'TORCH_HOME': 'models/torch', 'NUMBA_CACHE_DIR': 'cache/numba',
                     'MPLCONFIGDIR': 'cache/matplotlib'}.items():
    _path = _data / _folder
    _path.mkdir(parents=True, exist_ok=True)
    os.environ[_key] = str(_path)
os.environ['HF_HUB_DISABLE_XET'] = '1'
os.environ['USE_TF'] = '0'
