"""Nonblocking plugin pipeline with a fixed delay and time-aligned dry fallback."""
from copy import deepcopy
import math
import queue
import threading
import base64
import numpy as np
from .plugin_process import PluginProcess
from .plugin_rack import PluginRack
from .plugin_worker import encode_audio, decode_audio
from .plugin_state import StateStore, CHUNK
from .plugin_scan import fingerprint


class IsolatedPluginRack:
    validate = staticmethod(PluginRack.validate)
    quantum = 512
    latency_frames = 2048

    def __init__(self, factory=PluginProcess, state_store=None):
        self._commit_lock = threading.Lock()
        self._restore_lock = threading.Lock()
        self._lifecycle_epoch = 0
        self.preparing = None
        self.loading = False
        self.ui_busy = False
        self.factory = factory
        self.state_store = state_store or StateStore()
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
        if self.editor_open or self.editor_pending:
            raise RuntimeError('Close the native editor first.')
        if not self._restore_lock.acquire(blocking=False):
            raise RuntimeError('A plugin configuration is already in progress.')
        self.loading = True
        epoch = self._lifecycle_epoch
        prepared = None
        committed = False
        try:
            prepared = self.factory() if settings.get('effects') else None
            with self._commit_lock:
                if epoch != self._lifecycle_epoch:
                    raise RuntimeError('Native loading cancelled during shutdown.')
                self.preparing = prepared
            has_state = any(item.get('state_id') for item in settings.get('effects', []))
            initial_settings = deepcopy(settings)
            if has_state:
                initial_settings['bindings'] = {}
            values = prepared.request('configure', settings=initial_settings) if prepared else settings
            for index, item in enumerate(settings.get('effects', [])):
                if item.get('state_id'):
                    if item.get('state_binary') != fingerprint(item['path']):
                        raise ValueError('Plugin binary changed since native state capture. Review before restoring.')
                    raw = self.state_store.get(item['state_id'])
                    if not raw:
                        continue
                    prepared.request('state_begin', index=index, size=len(raw), sha256=item['state_id'])
                    for offset in range(0, len(raw), CHUNK):
                        prepared.request('state_write', offset=offset,
                            data=base64.b64encode(raw[offset:offset+CHUNK]).decode('ascii'))
                    prepared.request('state_commit')
            if prepared and has_state:
                prepared.request('set_values', parameters=[s.get('parameters', {}) for s in settings['effects']])
                values = prepared.request('inspect')
                values['bindings'] = deepcopy(settings.get('bindings', {}))
                for slot, original in zip(values['effects'], settings['effects']):
                    for key in ('state_id', 'state_binary'):
                        if key in original:
                            slot[key] = original[key]
                self.validate(values)
            with self._commit_lock:
                if epoch != self._lifecycle_epoch:
                    raise RuntimeError('Native loading cancelled during shutdown.')
                old_client, old_thread = self.client, self.thread
                self.client, self.preparing = prepared, None
                self.slots = deepcopy(values.get('effects', []))
                self.bindings = deepcopy(values.get('bindings', {}))
                self.error = ''
                self.reset_pipeline()
                self.thread = None
                if prepared:
                    initial = [dict(slot['parameters']) for slot in values['effects']]
                    self.thread = threading.Thread(target=self._broker,
                        args=(prepared, self.jobs, self.generation, initial), daemon=True)
                    self.thread.start()
                committed = True
            if old_client:
                old_client.close()
            if old_thread:
                old_thread.join(timeout=1)
        finally:
            if not committed and prepared:
                prepared.close()
            with self._commit_lock:
                if self.preparing is prepared:
                    self.preparing = None
            self.loading = False
            self._restore_lock.release()

    def add(self, path, plugin_name=None, parameters=None, bypass=False):
        self.capture_states()
        values = self.settings()
        values['effects'].append({'path': str(path), 'plugin_name': plugin_name or '',
                                  'parameters': parameters or {}, 'bypass': bool(bypass)})
        self.restore(values)

    def remove(self, index):
        self.capture_states()
        values = self.settings()
        values['effects'].pop(index)
        values['bindings'] = {key: {**item, 'slot': item['slot']-(item['slot'] > index)}
                              for key, item in values['bindings'].items() if item['slot'] != index}
        self.restore(values)

    def move(self, source, destination):
        self.capture_states()
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
        prior = self.settings()['effects']
        try:
            values = self.client.request('editor', timeout=None, index=index)
            self.slots = values['effects']
            for slot, saved in zip(self.slots, prior):
                for key in ('state_id', 'state_binary'):
                    if key in saved:
                        slot[key] = saved[key]
        finally:
            self.editor_open = False
        self.capture_states()

    def capture_states(self):
        """Call only with audio stopped. Opaque state stays outside JSON manifests."""
        if not self.client or not self.slots:
            return
        if self.editor_open:
            raise RuntimeError('Close the native editor before capturing state.')
        if self.loading:
            raise RuntimeError('Wait for native loading before capturing state.')
        self.client.request('set_values', parameters=[dict(s['parameters']) for s in self.slots])
        current = self.client.request('inspect')
        for slot, observed in zip(self.slots, current['effects']):
            slot['parameters'] = dict(observed['parameters'])
        captured = []
        for index, slot in enumerate(self.slots):
            info = self.client.request('state_info', index=index)
            from .plugin_state import MAX_STATE, valid_id
            if (type(info.get('size')) is not int or not 0 <= info['size'] <= MAX_STATE
                    or not valid_id(info.get('sha256'))):
                raise ValueError('Invalid worker state descriptor.')
            raw = bytearray()
            for offset in range(0, info['size'], CHUNK):
                block = base64.b64decode(self.client.request('state_read', index=index, offset=offset), validate=True)
                if len(block) != min(CHUNK, info['size']-offset):
                    raise ValueError('Invalid worker native state chunk length.')
                raw.extend(block)
            identity = self.state_store.put(bytes(raw), expected=info['sha256'])
            captured.append((identity, fingerprint(slot['path'])))
        for slot, (identity, binary) in zip(self.slots, captured):
            slot['state_id'], slot['state_binary'] = identity, binary

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
        with self._commit_lock:
            self._lifecycle_epoch += 1
            client, candidate, thread = self.client, self.preparing, self.thread
            self.client, self.thread = None, None
        if candidate and candidate is not client:
            candidate.kill()
        if client:
            client.close()
        if thread and thread is not threading.current_thread():
            thread.join(timeout=1)
