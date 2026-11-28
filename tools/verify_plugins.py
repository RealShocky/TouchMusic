"""Download reviewed official archives and verify actual effects/instrument hosting.

Only JSON reports are CI artifacts. Third-party binaries stay in temporary staging.
"""
import argparse
import json
from pathlib import Path
import sys
import time
from zipfile import ZipFile
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from touchmusic.plugin_catalog import download_plugin, DOWNLOADS
from touchmusic.plugin_scan import scan_plugin, fingerprint
from touchmusic.instrument import InstrumentBus
from touchmusic.plugin_state import StateStore


def extract_plugins(archive, root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    total = 0
    with ZipFile(archive) as zipped:
        for item in zipped.infolist():
            if '.vst3' not in item.filename.lower():
                continue
            target = (root/item.filename).resolve()
            total += item.file_size
            if not target.is_relative_to(root) or total > 256*1024*1024:
                raise ValueError('Invalid or oversized plugin archive.')
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zipped.read(item))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--staging', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--plugins', nargs='+', default=['SnapTune', 'LyraTune', 'Surge XT'])
    args = parser.parse_args()
    staging = Path(args.staging)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    for name, bundle_name in [('SnapTune', 'SnapTune.vst3'), ('LyraTune', 'Lyra Tune.vst3'), ('Surge XT', 'Surge XT.vst3')]:
        if name not in args.plugins:
            continue
        archive = download_plugin(name, staging)
        folder = staging/name
        extract_plugins(archive, folder)
        bundle = next(path for path in folder.rglob(bundle_name) if path.is_dir())
        if name != 'Surge XT':
            record = scan_plugin(bundle, DOWNLOADS[name]['version'])
            record['path'] = bundle_name
            assert record['status'] == 'Passed smoke test', record
            assert all(case['passed'] for case in record['compatibility_cases'] if case['rate'] == 48000), record
        else:
            (folder/'SurgeXTUserData').mkdir(exist_ok=True)
            instrument = InstrumentBus()
            instrument.state_store = StateStore(folder/'states')
            try:
                instrument.add(str(bundle.resolve()))
                instrument.capture_states()
                settings = instrument.settings()
                instrument.restore(settings)
                instrument.reset_stream()
                assert instrument.play([60, 64, 67], duration=.2)
                blocks = []
                for _ in range(70):
                    blocks.append(instrument.read(512))
                    time.sleep(.011)
                peak = float(np.max(np.abs(blocks)))
                assert peak > .001 and np.isfinite(blocks).all() and not instrument.error, {
                    'peak': peak, 'error': instrument.error, 'fallback': instrument.bypassed_blocks}
                record = {'plugin': name, 'version': DOWNLOADS[name]['version'], 'binary_sha256': fingerprint(bundle),
                          'parameters': len(instrument.slots[0]['parameters']), 'rate': 48000,
                          'stereo_peak': peak, 'blocks': 70, 'state_restore': 'Passed',
                          'stream_reset': 'Passed', 'hardware_audio_tested': False}
            finally:
                instrument.close()
        (output/(name.replace(' ', '-')+'.json')).write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
        print(name+': actual native hosting verified', flush=True)


if __name__ == '__main__':
    main()
