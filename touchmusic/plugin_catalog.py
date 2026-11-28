"""Reviewed publisher links. Listing is separate from compatibility certification."""
from pathlib import Path
import hashlib
import os
import tempfile
from urllib.parse import urlparse
from urllib.request import urlopen

CATALOG = [
    ('SnapTune', 'Pitch correction', 'AGPL-3.0', 'https://github.com/NicoFerni/snaptune'),
    ('Graillon 3', 'Pitch / formants', 'Proprietary free edition', 'https://www.auburnsounds.com/products/Graillon.html'),
    ('MAutoPitch', 'Pitch / formants', 'Proprietary freeware', 'https://www.meldaproduction.com/MAutoPitch'),
    ('LyraTune', 'Pitch correction', 'AGPL-3.0', 'https://github.com/333stack/LyraTune'),
    ('OpenVoxTuner', 'Pitch / harmony', 'AGPL-3.0', 'https://github.com/EiffelBS/OpenVoxTuner'),
    ('NoteForge', 'Pitch editor', 'AGPL-3.0', 'https://github.com/bighandfoot/NoteForge'),
    ('TDR Nova', 'Dynamic EQ / de-essing', 'Proprietary freeware', 'https://www.tokyodawn.net/tdr-nova/'),
    ('TDR Kotelnikov', 'Compressor', 'Proprietary freeware', 'https://www.tokyodawn.net/tdr-kotelnikov/'),
    ('Valhalla Supermassive', 'Reverb / delay', 'Proprietary freeware', 'https://valhalladsp.com/shop/reverb/valhalla-supermassive/'),
    ('Dragonfly Reverb', 'Reverb', 'GPL-3.0', 'https://github.com/michaelwillis/dragonfly-reverb'),
    ('ChowMatrix', 'Multi-tap delay', 'BSD-3-Clause', 'https://github.com/Chowdhury-DSP/ChowMatrix'),
    ('BYOD', 'Modular distortion', 'GPL-3.0', 'https://github.com/Chowdhury-DSP/BYOD'),
    ('MFreeFXBundle', 'Effects bundle', 'Proprietary free edition', 'https://www.meldaproduction.com/MFreeFXBundle'),
    ('Surge XT', 'Instrument (planned)', 'GPL-3.0', 'https://github.com/surge-synthesizer/surge'),
    ('Cardinal', 'Modular instrument (planned)', 'GPL-3.0', 'https://github.com/DISTRHO/Cardinal'),
]

# SHA256 observed from a developer-hosted archive, not an independent publisher signature.
# Assets are staged for manual installation. Never execute an installer or extract arbitrary ZIPs.
DOWNLOADS = {'TDR Nova': {
    'version': '2.2.3', 'filename': 'TDR-Nova-2.2.3.zip',
    'url': 'https://www.tokyodawn.net/labs/Nova/2.2.3/TDR%20Nova%20%28no%20installer%29.zip',
    'sha256': '9bb52d042bd95dd85456da66316347a00d865d9d3f6652333e1a2bc195cb8907'}}


def download_plugin(name, directory, opener=urlopen):
    asset = DOWNLOADS[name]
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='download-', suffix='.part', dir=root)
    digest, count = hashlib.sha256(), 0
    try:
        with os.fdopen(descriptor, 'wb') as output, opener(asset['url'], timeout=30) as source:
            final = urlparse(source.geturl())
            if final.scheme != 'https' or final.hostname != urlparse(asset['url']).hostname:
                raise ValueError('Unexpected download redirect. Use the publisher link.')
            while True:
                block = source.read(65536)
                if not block:
                    break
                count += len(block)
                if count > 256 * 1024 * 1024:
                    raise ValueError('Plugin archive exceeds the download limit.')
                digest.update(block)
                output.write(block)
        if digest.hexdigest() != asset['sha256']:
            raise ValueError('Archive checksum changed. Publisher review is required.')
        target = root / asset['filename']
        os.replace(temporary, target)
        return target
    finally:
        Path(temporary).unlink(missing_ok=True)
