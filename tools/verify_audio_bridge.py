"""Real native host -> standalone DSP -> native stereo return, without audio hardware."""
import gc
import json
from pathlib import Path
import sys
import time
import numpy as np
from pedalboard import load_plugin

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from touchmusic.audio import AudioEngine
from touchmusic.audio_bridge import AudioBridge


def main():
    engine = AudioEngine()
    engine.params.update(robot=.6, reverb=0, delay=0)
    rendered = []
    original = engine.process
    def capture(audio, stereo=False):
        result = original(audio, stereo=stereo)
        rendered.append(result.copy())
        return result
    engine.process = capture
    server = AudioBridge(engine)
    server.start()
    plugin = None
    try:
        path = Path(sys.argv[1])
        binary = path/'Contents/x86_64-win'/path.name
        plugin = load_plugin(str(binary if binary.is_file() else path))
        outputs = []
        for index in range(90):
            t = (np.arange(512)+index*512)/48000
            source = np.stack((.1*np.sin(t*2*np.pi*220), .1*np.sin(t*2*np.pi*330))).astype(np.float32)
            outputs.append(plugin.process(source, 48000, reset=False))
            time.sleep(.011)
        actual = np.concatenate(outputs, axis=1).T
        expected = np.concatenate((np.zeros((4096, 2)), np.concatenate(rendered)))[:len(actual)]
        matched = bool(np.allclose(actual[8192:], expected[8192:], atol=1e-6))
        report = {'native_audio_bridge': '0.5.0', 'rate': 48000, 'blocks_sent': 90,
                  'returned_blocks': server.packets, 'gaps': server.gaps, 'rejected': server.rejected,
                  'server_error': server.error, 'declared_transport_frames': 4096,
                  'matches_standalone_processed_audio': matched, 'hardware_tested': False,
                  'daw_tested': False, 'real_ai_model_tested': False}
        print(json.dumps(report, indent=2))
        assert matched and not server.error and server.packets > 70
        if len(sys.argv) > 2:
            Path(sys.argv[2]).write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    finally:
        plugin = None
        gc.collect()
        server.close()
        engine.rack.close()
        engine.instrument.close()


if __name__ == '__main__':
    main()
