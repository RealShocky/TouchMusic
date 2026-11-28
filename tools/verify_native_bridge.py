"""Exercise the compiled plugin, audio passthrough and native-to-Python control."""
import gc
from pathlib import Path
import sys
import time
import numpy as np
from pedalboard import load_plugin

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from touchmusic.bridge import LocalBridge


def main():
    server = LocalBridge()
    server.start()
    plugin = None
    try:
        path = Path(sys.argv[1]).resolve()
        binary = path/'Contents'/'x86_64-win'/path.name
        plugin = load_plugin(str(binary if binary.is_file() else path))
        plugin.parameters['reverb'].raw_value = .61
        plugin.parameters['pitch'].raw_value = .5
        source = np.stack((np.linspace(-.2, .2, 48000, dtype=np.float32),)*2)
        output = plugin.process(source, 48000, reset=False)
        np.testing.assert_allclose(output, source, atol=1e-7)
        deadline = time.monotonic()+4
        received = None
        while time.monotonic() < deadline:
            packet = server.consume()
            if packet and abs(packet['parameters'][0]-.61) < .001:
                received = packet
                break
            time.sleep(.02)
        assert received, 'Native automation did not reach the Python receiver.'
        assert not server.error
        print('Native VST3 load, 10 parameters, unchanged audio and UDP automation passed.')
    finally:
        plugin = None
        gc.collect()
        server.close()


if __name__ == '__main__':
    main()
