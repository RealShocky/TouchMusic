"""Install the optional neural runtime without writing into site-packages."""
from importlib.resources import files
from pathlib import Path
import shutil
import subprocess
import sys
from .runtime import VENDOR, SEED_REVISION


def patch_seed(path):
    path = Path(path) / 'modules/length_regulator.py'
    source = path.read_text(encoding='utf-8')
    eager_import = 'from dac.nn.quantize import VectorQuantize\n'
    branch = '            if vector_quantize:\n'
    lazy_import = '                ' + eager_import
    if branch + lazy_import not in source:
        if source.count(eager_import) != 1 or source.count(branch) != 1:
            raise RuntimeError('Seed-VC source does not match the pinned version.')
        path.write_text(source.replace(eager_import, '').replace(branch, branch + lazy_import), encoding='utf-8')


def setup_ai(cpu=False):
    if not shutil.which('git'):
        raise RuntimeError('Install Git for Windows, then run touchmusic --setup-ai again.')
    index = 'https://download.pytorch.org/whl/' + ('cpu' if cpu else 'cu128')
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'torch==2.11.0', 'torchaudio==2.11.0',
                    'torchvision==0.26.0', '--index-url', index], check=True)
    requirements = str(files('touchmusic').joinpath('ai-requirements.txt'))
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', requirements], check=True)
    VENDOR.parent.mkdir(parents=True, exist_ok=True)
    if not (VENDOR / '.git').is_dir():
        subprocess.run(['git', 'clone', 'https://github.com/Plachtaa/seed-vc.git', str(VENDOR)], check=True)
    subprocess.run(['git', '-C', str(VENDOR), 'checkout', SEED_REVISION], check=True)
    patch_seed(VENDOR)
    print('Singing engine setup complete. Run touchmusic and import a voice reference.')
