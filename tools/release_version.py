"""Allow stable publishing only for a complete three-part release number."""
import os
from pathlib import Path
import re
import tomllib


def stable_release(version):
    return bool(re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version))


def main():
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8-sig'))['project']['version']
    value = 'publishable='+str(stable_release(version)).lower()+'\n'
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
            output.write(value)
    print(version+': '+value.strip())


if __name__ == '__main__':
    main()
