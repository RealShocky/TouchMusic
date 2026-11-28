"""Nonblocking plugin pipeline with a fixed delay and time-aligned dry fallback."""
from copy import deepcopy
import math
import queue
import threading
import numpy as np
from .plugin_process import PluginProcess
from .plugin_rack import PluginRack
from .plugin_worker import encode_audio, decode_audio


class IsolatedPluginRack:
    validate = staticmethod(PluginRack.validate)
    quantum = 512
    latency_frames = 2048

    def __init__(self, factory=PluginProcess):
        self.factory = factory
        self.slots, self.bindings = [], {}
        self.error = ''
        self.bypassed_blocks = 0
        self.compute_ms = 0.
        self.client = None
        self.thread = None
        self.editor_open = False
        self.editor_pending = False
        self.reset_pipeline()

    def settings(self):
        return {'effects': deepcopy(self.slots), 'bindings': deepcopy(self.bindings)}

    def reset_pipeline(self):
        self.generation = getattr(self, 'generation', 0) + 1
        self.position = 0
        self.entries = {}
        self.jobs = queue.Queue(maxsize=6)

    def restore(self, settings):
        self.validate(settings)
        if self.editor_open:
            raise RuntimeError('Close the native editor first.')
        prepared = self.factory() if settings.get('effects') else None
        try:
            values = prepared.request('configure', settings=settings) if prepared else settings
        except Exception:
            prepared.close()
            raise
        self.close()
        self.client = prepared
        self.slots = deepcopy(values.get('effects', []))
        self.bindings = deepcopy(values.get('bindings', {}))
        self.error = ''
        self.reset_pipeline()
        if prepared:
            jobs, generation = self.jobs, self.generation
            initial = [dict(s['parameters']) for s in values['effects']]
            self.thread = threading.Thread(target=self._broker, args=(prepared, jobs, generation, initial), daemon=True)
            self.thread.start()

    def add(self, path, plugin_name=None, parameters=None, bypass=False):
        values = self.settings()
        values['effects'].append({'path': str(path), 'plugin_name': plugin_name or '',
                                  'parameters': parameters or {}, 'bypass': bool(bypass)})
        self.restore(values)

    def remove(self, index):
        values = self.settings()
        values['effects'].pop(index)
        values['bindings'] = {key: {**item, 'slot': item['slot']-(item['slot'] > index)}
                              for key, item in values['bindings'].items() if item['slot'] != index}
        self.restore(values)

    def move(self, source, destination):
        values = self.settings()
        slots = values['effects']
        slots[source], slots[destination] = slots[destination], slots[source]
        for item in values['bindings'].values():
            if item['slot'] == source:
                item['slot'] = destination
            elif item['slot'] == destination:
                item['slot'] = source
        self.restore(values)

    def apply_values(self, settings):
        self.validate(settings)
        if [(s['path'], s.get('plugin_name', '')) for s in settings.get('effects', [])] != [
                (s['path'], s.get('plugin_name', '')) for s in self.slots]:
            return False
        for index, item in enumerate(settings.get('effects', [])):
            for name, value in item.get('parameters', {}).items():
                self.set_parameter(index, name, value)
            self.slots[index]['bypass'] = bool(item.get('bypass'))
        self.bindings = deepcopy(settings.get('bindings', {}))
        return True

    def set_parameter(self, index, name, value):
        if (type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 1
                or not 0 <= index < len(self.slots) or name not in self.slots[index]['parameters']):
            return False
        # Coalesce to the latest value. The broker retries it on subsequent blocks.
        self.slots[index]['parameters'][name] = float(value)
        return True

    def control(self, knob, value):
        binding = self.bindings.get(str(knob))
        return bool(binding and self.set_parameter(binding['slot'], binding['parameter'], value))

    def _broker(self, client, jobs, generation, applied):
        while client is self.client and generation == self.generation:
            try:
                entry, rate = jobs.get(timeout=.1)
            except queue.Empty:
                continue
            try:
                desired = [dict(s['parameters']) for s in self.slots]
                changed = [{name: value for name, value in values.items() if applied[i].get(name) != value}
                           for i, values in enumerate(desired)]
                result = self._request_audio(client, entry, rate, changed)
                applied = desired
                wet = decode_audio(result)
                if wet.shape != (2, len(entry['dry'])):
                    raise ValueError('Unexpected plugin output dimensions.')
                if result.get('error'):
                    raise RuntimeError(result['error'])
                entry['wet'] = wet
                self.compute_ms = result['compute_ms']
            except Exception as exc:
                if client is self.client:
                    self.error = str(exc)
                client.kill()
                return

    def process(self, audio, rate, stereo=False):
        if not self.slots:
            return np.stack((audio, audio)) if stereo else audio
        audio = np.asarray(audio, np.float32)
        if audio.ndim != 1:
            raise ValueError('The isolated vocal pipeline expects mono input.')
        output = np.zeros((2, len(audio)), np.float32)
        offset = 0
        while offset < len(audio):
            frame = self.position
            key, within = divmod(frame, self.quantum)
            size = min(len(audio)-offset, self.quantum-within)
            entry = self.entries.setdefault(key, {'dry': np.zeros(self.quantum, np.float32),
                                                 'wet': None, 'start': key*self.quantum})
            entry['dry'][within:within+size] = audio[offset:offset+size]
            if within+size == self.quantum and not self.error and not self.editor_open:
                try:
                    self.jobs.put_nowait((entry, rate))
                except queue.Full:
                    self.bypassed_blocks += 1
            target = frame-self.latency_frames
            if target >= 0:
                old_key, old_offset = divmod(target, self.quantum)
                old = self.entries[old_key]
                wet = old['wet']
                signal = wet if wet is not None else np.broadcast_to(old['dry'], (2, self.quantum))
                output[:, offset:offset+size] = signal[:, old_offset:old_offset+size]
                if wet is None:
                    self.bypassed_blocks += 1
                if old_offset+size == self.quantum:
                    self.entries.pop(old_key)
            offset += size
            self.position += size
        return output if stereo else output.mean(axis=0)

    def _request_audio(self, client, entry, rate, changed):
        return client.request('process', audio=encode_audio(entry['dry']), rate=rate,
            parameters=changed, bypass=[s['bypass'] for s in self.slots])

    def show_editor(self, index):
        if self.editor_open or not self.client or self.error:
            raise RuntimeError('Restart a healthy rack before opening its editor.')
        self.editor_open = True
        try:
            values = self.client.request('editor', timeout=None, index=index)
            self.slots = values['effects']
        finally:
            self.editor_open = False

    def restart(self):
        self.restore(self.settings())

    def reset_stream(self):
        """Clear transport buffers off the audio thread without losing native editor state."""
        if self.editor_open:
            raise RuntimeError('Close the native editor first.')
        if not self.client or self.error:
            if self.slots:
                self.restart()
            return
        self.generation += 1
        if self.thread:
            self.thread.join(timeout=11)
            if self.thread.is_alive():
                self.error = 'Plugin broker did not stop. Restart the rack.'
                self.client.kill()
                raise RuntimeError(self.error)
        self.client.request('reset')
        self.reset_pipeline()
        initial = [dict(s['parameters']) for s in self.client.request('inspect')['effects']]
        self.thread = threading.Thread(target=self._broker,
            args=(self.client, self.jobs, self.generation, initial), daemon=True)
        self.thread.start()

    def close(self):
        client, self.client = self.client, None
        if client:
            client.close()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=1)
        self.thread = None
