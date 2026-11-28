"""Worker-only native instrument loader and MIDI renderer."""
from pathlib import Path
import math
import re
import numpy as np
from .plugin_rack import PluginRack


def load_instrument(path, plugin_name=None):
    from pedalboard import VST3Plugin
    def normalized_parameters(plugin):
        return {f'{index:04d}_'+re.sub(r'\W+', '_', parameter.name).strip('_'): parameter
                for index, parameter in enumerate(plugin._parameters)}
    # Only the dedicated instrument worker imports this adapter. Avoid speculative
    # text/range inference and expose stable, version-specific normalized indices.
    VST3Plugin.parameters = property(normalized_parameters)
    return VST3Plugin(path, plugin_name=plugin_name)


class InstrumentBackend(PluginRack):
    def __init__(self, loader=None):
        super().__init__(loader or load_instrument)

    @staticmethod
    def validate(settings):
        PluginRack.validate(settings, maximum_parameters=8192)

    def restore(self, settings):
        self.validate(settings)
        if len(settings.get('effects', [])) != 1:
            raise ValueError('Choose exactly one VST3 instrument.')
        item = settings['effects'][0]
        path = Path(item['path']).resolve()
        binary = path/'Contents'/'x86_64-win'/path.name
        plugin = self.loader(str(binary if binary.is_file() else path), plugin_name=item.get('plugin_name') or None)
        if not plugin.is_instrument:
            raise ValueError('Choose an instrument, not an audio effect.')
        values = {name: float(p.raw_value) for name, p in plugin.parameters.items()}
        for name, value in item.get('parameters', {}).items():
            if name in values and values[name] != value:
                plugin.parameters[name].raw_value = value
                values[name] = value
        self.slots = [{**item, 'path': str(path), 'plugin_name': item.get('plugin_name', ''),
                       'parameters': values, 'bypass': bool(item.get('bypass')), 'plugin': plugin}]
        self.bindings = settings.get('bindings', {}).copy()

    def process(self, frames, rate, midi):
        if not isinstance(midi, list) or len(midi) > 512 or rate != 48000:
            raise ValueError('Invalid instrument MIDI block or sample rate.')
        for message, stamp in midi:
            if (not isinstance(message, list) or len(message) != 3
                    or type(message[0]) is not int or message[0] not in (0x80, 0x90, 0xB0)
                    or any(type(n) is not int or not 0 <= n <= 127 for n in message[1:])
                    or type(stamp) not in (float, int) or not math.isfinite(stamp) or not 0 <= stamp < frames/rate):
                raise ValueError('Invalid instrument MIDI event.')
        if self.slots[0]['bypass']:
            midi = [([0xB0, 120, 0], 0.)]
        result = np.asarray(self.slots[0]['plugin'].process(midi, sample_rate=rate,
                           duration=frames/rate, num_channels=2, reset=False), np.float32)
        if result.shape != (2, frames) or not np.isfinite(result).all():
            raise ValueError('Invalid instrument audio output.')
        return np.zeros_like(result) if self.slots[0]['bypass'] else result
