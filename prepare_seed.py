"""Keep the optional training codec out of the pitch-conditioned runtime."""
from pathlib import Path


if __name__ == '__main__':
    path = Path(__file__).resolve().parent / 'vendor/seed-vc/modules/length_regulator.py'
    source = path.read_text(encoding='utf-8')
    eager_import = 'from dac.nn.quantize import VectorQuantize\n'
    branch = '            if vector_quantize:\n'
    lazy_import = '                ' + eager_import
    if branch + lazy_import not in source:
        if source.count(eager_import) != 1 or source.count(branch) != 1:
            raise RuntimeError('Seed-VC source does not match the pinned version.')
        source = source.replace(eager_import, '').replace(branch, branch + lazy_import)
        path.write_text(source, encoding='utf-8')
