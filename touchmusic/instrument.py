"""Isolated stereo VST3 instrument bus with bounded, timestamped note lifetimes."""
import heapq
import math
import queue
import numpy as np
from .isolated_rack import IsolatedPluginRack
from .plugin_process import PluginProcess
from .plugin_rack import PluginRack
from .plugin_worker import encode_audio


class InstrumentProcess(PluginProcess):
    def request(self, action, **values):
        if action == 'configure':
            values['instrument'] = True
        return super().request(action, **values)


class InstrumentBus(IsolatedPluginRack):
    def __init__(self, factory=InstrumentProcess):
        self.gain = .3
        self.note_commands = queue.Queue(maxsize=128)
        self.panic_requested = True
        self.events = []
        self.active = {}
        self.serial = 0
        self.note_epoch = 0
        super().__init__(factory)

    @staticmethod
    def validate(settings):
        PluginRack.validate(settings, maximum_parameters=8192)
        if len(settings.get('effects', [])) > 1:
            raise ValueError('The instrument bus supports one synthesizer.')

    def reset_pipeline(self):
        super().reset_pipeline()
        self.panic()

    def play(self, notes, velocity=96, duration=.5):
        if (not isinstance(notes, (list, tuple)) or not 1 <= len(notes) <= 16
                or any(type(n) is not int or not 0 <= n <= 127 for n in notes)
                or type(velocity) is not int or not 1 <= velocity <= 127
                or type(duration) not in (int, float) or not math.isfinite(duration) or not .05 <= duration <= 10):
            raise ValueError('Invalid instrument note, velocity or duration.')
        if not self.slots or self.error or self.editor_open:
            return False
        try:
            self.note_commands.put_nowait((self.note_epoch, self.position, list(notes), velocity, duration))
            return True
        except queue.Full:
            self.panic()
            return False

    def panic(self):
        self.note_epoch += 1
        self.panic_requested = True

    def _midi(self, start, frames, rate):
        result = []
        if self.panic_requested:
            self.panic_requested = False
            self.events.clear()
            self.active.clear()
            result = [([0xB0, 123, 0], 0.), ([0xB0, 120, 0], 0.)]
        while True:
            try:
                epoch, frame, notes, velocity, duration = self.note_commands.get_nowait()
            except queue.Empty:
                break
            if epoch != self.note_epoch:
                continue
            for note in notes:
                self.serial += 1
                token = self.serial
                attack = max(start, frame)
                heapq.heappush(self.events, (attack, token, 0, note, velocity))
                heapq.heappush(self.events, (attack+round(duration*rate), token, 1, note, 0))
        if len(self.events) > 4096:
            self.events.clear()
            self.active.clear()
            return [([0xB0, 123, 0], 0.), ([0xB0, 120, 0], 0.)]
        while self.events and self.events[0][0] < start+frames:
            frame, token, off, note, velocity = heapq.heappop(self.events)
            if off and self.active.get(note) != token:
                continue
            if off:
                self.active.pop(note, None)
            else:
                self.active[note] = token
            result.append(([0x80 if off else 0x90, note, velocity], max(0, frame-start)/rate))
        return result

    def _request_audio(self, client, entry, rate, changed):
        return client.request('process', audio=encode_audio(entry['dry']), rate=rate, parameters=changed,
            bypass=[s['bypass'] for s in self.slots], midi=self._midi(entry['start'], self.quantum, rate))

    def read(self, frames, rate=48000):
        return self.process(np.zeros(frames, np.float32), rate, stereo=True).T * self.gain
