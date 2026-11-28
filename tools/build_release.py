"""Build a clean setup archive from an explicit public-file allowlist."""
import hashlib
from pathlib import Path
import tomllib
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT / 'pyproject.toml').read_text('utf-8-sig'))['project']['version']
OUTPUT = ROOT / 'dist'


def main():
    OUTPUT.mkdir(exist_ok=True)
    source_files = [ROOT / name for name in ('README.md', 'Setup.cmd', 'Launch.cmd',
                    'prepare_seed.py', 'pyproject.toml', 'MANIFEST.in', 'requirements.txt', 'THIRD_PARTY_NOTICES.md')]
    source_files.extend((ROOT / 'touchmusic').glob('*.py'))
    source_files.extend((ROOT / 'touchmusic').glob('*.txt'))
    archive = OUTPUT / f'TouchMusic-{VERSION}-Windows-Setup.zip'
    with ZipFile(archive, 'w', ZIP_DEFLATED) as zipped:
        for file in sorted(source_files):
            zipped.write(file, f'TouchMusic-{VERSION}/' + file.relative_to(ROOT).as_posix())
        zipped.writestr(f'TouchMusic-{VERSION}/START-HERE.txt',
            'TouchMusic for Windows\n\nInstall Python 3.11 (64-bit) and Git for Windows.\n'
            'Extract this ZIP, run Setup.cmd once, then open Launch.cmd.\n'
            'Setup needs internet and downloads the optional singing runtime.\n'
            'Import your own voice references. Read README.md for MIDI and FL Studio setup.\n')
    checksums = []
    for file in sorted(OUTPUT.iterdir()):
        if file.name.endswith(('.whl', '.tar.gz', '.zip')):
            with file.open('rb') as source:
                checksums.append(hashlib.file_digest(source, 'sha256').hexdigest() + '  ' + file.name)
    (OUTPUT / 'SHA256SUMS.txt').write_text('\n'.join(checksums) + '\n', encoding='utf-8')
    print(archive)


if __name__ == '__main__':
    main()
