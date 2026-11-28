"""MIDI output with bounded controller traffic and timed note release."""
import time

NOTE_NAMES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
MIDI_LEVELS = tuple(f'MIDI CC {number}' for number in range(120))
MIDI_NOTES = {f'MIDI note {name}4': 60 + index for index, name in enumerate(NOTE_NAMES)}
MIDI_CHORDS = {f'MIDI chord {name}': degree for degree, name in enumerate(('I', 'II', 'III', 'IV', 'V', 'VI', 'VII'))}
MIDI_ACTIONS = (*MIDI_NOTES, 'MIDI chord', *MIDI_CHORDS, 'MIDI panic')


class MidiOutput:
    def __init__(self, factory=None, clock=time.monotonic):
        self.factory = factory or self._backend
        self.clock = clock
        self.backend = None
        self.port = ''
        self.channel = 1
        self.error = ''
        self.notes = {}
        self.controls = {}

    @staticmethod
    def _backend():
        try:
            import rtmidi
        except ImportError as exc:
            raise RuntimeError('MIDI needs python-rtmidi. Run Setup.cmd or reinstall TouchMusic.') from exc
        return rtmidi.MidiOut()

    def ports(self):
        if self.backend:
            return self.backend.get_ports()
        device = self.factory()
        try:
            return device.get_ports()
        finally:
            device.close_port()

    def connect(self, port, channel=1):
        self.close()
        self.error = ''
        device = self.factory()
        try:
            available = device.get_ports()
            if port not in available:
                raise ValueError('Choose an available MIDI output port.')
            device.open_port(available.index(port), 'TouchMusic')
        except Exception:
            device.close_port()
            raise
        self.backend, self.port, self.channel = device, port, max(1, min(16, int(channel)))

    def send(self, message):
        if self.backend is None:
            return False
        try:
            self.backend.send_message(message)
            return True
        except Exception as exc:
            self.error = str(exc)
            self.close()
            return False

    def control(self, controller, value):
        value = max(0, min(127, round(value * 127)))
        previous, sent = self.controls.get(controller, (None, float('-inf')))
        now = self.clock()
        if value == previous or now - sent < .025:
            return
        if self.send([0xB0 | (self.channel - 1), controller, value]):
            self.controls[controller] = value, now

    def play(self, notes, velocity=100, duration=.5):
        now = self.clock()
        status = self.channel - 1
        for note in sorted(set(notes)):
            if not 0 <= note <= 127:
                continue
            if note in self.notes:
                self.send([0x80 | status, note, 0])
            if self.send([0x90 | status, note, max(1, min(127, int(velocity)))]):
                self.notes[note] = now + max(.05, min(10., duration))

    def tick(self):
        for note, deadline in tuple(self.notes.items()):
            if deadline <= self.clock():
                self.notes.pop(note, None)
                self.send([0x80 | (self.channel - 1), note, 0])

    def panic(self):
        device = self.backend
        status = self.channel - 1
        notes, self.notes = self.notes, {}
        self.controls.clear()
        if device is not None:
            try:
                for note in notes:
                    device.send_message([0x80 | status, note, 0])
                device.send_message([0xB0 | status, 123, 0])
                device.send_message([0xB0 | status, 120, 0])
            except Exception as exc:
                self.error = str(exc)

    def close(self):
        self.panic()
        device, self.backend = self.backend, None
        self.port = ''
        if device is not None:
            try:
                device.close_port()
            except Exception as exc:
                self.error = str(exc)
