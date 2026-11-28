"""A bounded VST3 effect rack with normalized gesture parameters."""
from copy import deepcopy
from pathlib import Path
import math
import threading
import numpy as np


class PluginRack:
    def __init__(self, loader=None):
        from pedalboard import load_plugin
        self.loader = loader or load_plugin
        self.slots = []
        self.bindings = {}
        self.lock = threading.Lock()
        self.error = ''
        self.bypassed_blocks = 0

    def add(self, path, plugin_name=None, parameters=None, bypass=False):
        path = Path(path).resolve()
        if path.suffix.lower() != '.vst3' or not path.exists():
            raise ValueError('Choose an installed VST3 effect file or bundle.')
        if len(self.slots) >= 4:
            raise ValueError('This rack supports four VST3 effects.')
        binary = path/'Contents'/'x86_64-win'/path.name
        plugin = self.loader(str(binary if binary.is_file() else path), plugin_name=plugin_name or None)
        if getattr(plugin, 'is_instrument', False):
            raise ValueError('Choose an audio effect. Instrument hosting is not supported in this vocal rack.')
        values = {name: float(parameter.raw_value) for name, parameter in plugin.parameters.items()}
        for name, value in (parameters or {}).items():
            if name in values and isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= 1:
                plugin.parameters[name].raw_value = value
                values[name] = float(value)
        slot = {'path': str(path), 'plugin_name': plugin_name or '', 'parameters': values,
                'bypass': bool(bypass), 'plugin': plugin}
        with self.lock:
            self.slots.append(slot)

    def settings(self):
        with self.lock:
            return {'effects': [{key: deepcopy(value) for key, value in slot.items() if key != 'plugin'}
                                for slot in self.slots], 'bindings': deepcopy(self.bindings)}

    def process(self, audio, rate):
        if not self.slots:
            return audio
        if not self.lock.acquire(blocking=False):
            self.bypassed_blocks += 1
            return audio
        try:
            for slot in self.slots:
                if slot['bypass']:
                    continue
                try:
                    plugin = slot['plugin']
                    channels = getattr(plugin, 'num_input_channels', 2)
                    source = audio if channels == 1 else np.stack((audio, audio))
                    processed = np.asarray(plugin.process(source, rate, reset=False), np.float32)
                    if processed.ndim == 2:
                        processed = processed.mean(axis=0)
                    if processed.shape != audio.shape or not np.isfinite(processed).all():
                        raise ValueError('Plugin returned an invalid audio block.')
                    audio = processed
                except Exception as exc:
                    slot['bypass'] = True
                    self.error = Path(slot['path']).name + ': ' + str(exc)
            return audio
        finally:
            self.lock.release()

    def set_parameter(self, index, name, value):
        if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 1:
            return False
        if not self.lock.acquire(blocking=False):
            return False
        try:
            if not 0 <= index < len(self.slots) or name not in self.slots[index]['parameters']:
                return False
            slot = self.slots[index]
            slot['plugin'].parameters[name].raw_value = value
            slot['parameters'][name] = float(value)
            return True
        except Exception as exc:
            self.error = str(exc)
            return False
        finally:
            self.lock.release()

    def control(self, knob, value):
        binding = self.bindings.get(str(knob))
        return bool(binding and self.set_parameter(binding['slot'], binding['parameter'], value))

    def remove(self, index):
        with self.lock:
            self.slots.pop(index)
            self.bindings = {key: {**value, 'slot': value['slot']-(value['slot'] > index)}
                             for key, value in self.bindings.items() if value['slot'] != index}

    def move(self, source, destination):
        with self.lock:
            self.slots[source], self.slots[destination] = self.slots[destination], self.slots[source]
            for value in self.bindings.values():
                if value['slot'] == source:
                    value['slot'] = destination
                elif value['slot'] == destination:
                    value['slot'] = source

    def apply_values(self, settings):
        self.validate(settings)
        effects = settings.get('effects', [])
        current = self.settings()['effects']
        if [(item.get('path'), item.get('plugin_name', '')) for item in effects] != [
                (item['path'], item['plugin_name']) for item in current]:
            return False
        for index, item in enumerate(effects):
            for name, value in item.get('parameters', {}).items():
                self.set_parameter(index, name, value)
            self.slots[index]['bypass'] = bool(item.get('bypass'))
        self.bindings = deepcopy(settings.get('bindings', {}))
        return True

    def restore(self, settings):
        self.validate(settings)
        effects = settings.get('effects', [])
        if not isinstance(effects, list) or len(effects) > 4:
            raise ValueError('A rack supports up to four effects.')
        prepared = PluginRack(self.loader)
        for item in effects:
            prepared.add(item['path'], item.get('plugin_name'), item.get('parameters'), item.get('bypass', False))
        for key, binding in settings.get('bindings', {}).items():
            if (key not in [str(i) for i in range(1, 9)] or not isinstance(binding, dict)
                    or type(binding.get('slot')) is not int or not 0 <= binding['slot'] < len(prepared.slots)
                    or binding.get('parameter') not in prepared.slots[binding['slot']]['parameters']):
                raise ValueError('Invalid plugin gesture binding.')
        with self.lock:
            self.slots = prepared.slots
            self.bindings = deepcopy(settings.get('bindings', {}))
            self.error = ''

    @staticmethod
    def validate(settings):
        if not isinstance(settings, dict) or not isinstance(settings.get('effects', []), list):
            raise ValueError('Invalid plugin rack settings.')
        effects = settings.get('effects', [])
        if len(effects) > 4:
            raise ValueError('A rack supports four effects.')
        for item in effects:
            if (not isinstance(item, dict) or not isinstance(item.get('path'), str)
                    or Path(item['path']).suffix.lower() != '.vst3'
                    or not isinstance(item.get('plugin_name', ''), str)
                    or not isinstance(item.get('parameters', {}), dict)):
                raise ValueError('Invalid saved effect.')
            values = item.get('parameters', {})
            if len(values) > 2048 or any(not isinstance(name, str) or type(value) not in (int, float)
                    or not math.isfinite(value) or not 0 <= value <= 1 for name, value in values.items()):
                raise ValueError('Invalid saved plugin parameters.')
        bindings = settings.get('bindings', {})
        if not isinstance(bindings, dict) or len(bindings) > 8:
            raise ValueError('Invalid plugin bindings.')
        for key, binding in bindings.items():
            if (key not in [str(i) for i in range(1, 9)] or not isinstance(binding, dict)
                    or type(binding.get('slot')) is not int or not 0 <= binding['slot'] < len(effects)
                    or binding.get('parameter') not in effects[binding['slot']].get('parameters', {})):
                raise ValueError('Invalid plugin binding.')
