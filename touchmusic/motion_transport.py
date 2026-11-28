"""Sample-clock score dispatch. Qt/MIDI/voice operations are relayed to the GUI."""
from copy import deepcopy
import queue
from .motion_score import MotionScore
from .music import DEGREES, chord_notes


class MotionTransport:
    def __init__(self):
        self.pending = None
        self.running = False
        self.token = 0
        self.active_token = 0
        self.events = []
        self.cursor = 0
        self.beat = 0.
        self.routes = {}
        self.messages = queue.Queue(maxsize=1024)
        self.error = ''
        self.budget = 128

    def start(self, settings, routes):
        MotionScore.validate(settings)
        self.token += 1
        self.pending = (self.token, deepcopy(settings['events']), deepcopy(routes))
        self.error = ''

    def stop(self):
        self.token += 1
        self.pending = None
        self.running = False

    def begin(self):
        pending, self.pending = self.pending, None
        if pending:
            token, self.events, self.routes = pending
            self.cursor, self.beat = 0, 0.
            self.running = bool(self.events)
            self.active_token = token
        self.budget = 128

    def next_frame(self, frame, period):
        if not self.running or self.cursor >= len(self.events):
            return None
        return frame+max(0, round((self.events[self.cursor]['beat']-self.beat)*period))

    def advance(self, frames, period):
        if self.running:
            self.beat += frames/period

    def dispatch(self, engine):
        event = self.events[self.cursor]
        self.cursor += 1
        self.budget -= 1
        handled = self.apply(engine, event)
        try:
            self.messages.put_nowait((self.active_token, event, handled, engine.clock.frame))
        except queue.Full:
            self.error = 'Motion Score relay is full; playback stopped.'
            self.running = False
        if self.cursor == len(self.events):
            self.running = False
        if self.budget <= 0 and self.running:
            self.error = 'Too many Motion Score events in one audio block; playback stopped.'
            self.running = False

    def drain(self):
        result = []
        for _ in range(256):
            try:
                token, event, handled, frame = self.messages.get_nowait()
            except queue.Empty:
                break
            if token == self.token:
                result.append((event, handled, frame))
        return result

    def apply(self, engine, event):
        target = event['target']
        if event['kind'] == 'level':
            value = event['value']
            if target.startswith('Plugin knob '):
                engine.rack.control(int(target.split()[-1]), value)
                return True
            if target.startswith('Instrument knob '):
                engine.instrument.control(int(target.split()[-1]), value)
                return True
            if target == 'Instrument level':
                engine.instrument.gain = round(value*100)/100
                return True
            if target == 'Track level':
                engine.track.gain = round(value*100)/100
                return True
            if target.startswith('Loop ') and target.endswith(' level'):
                index = int(target.split()[1])-1
                if 0 <= index < len(engine.loops):
                    engine.loops[index].gain = round(value*100)/100
                    return True
            route = self.routes.get(target)
            if route:
                if 'choices' in route:
                    choices = route['choices']
                    number = choices[min(len(choices)-1, int(value*len(choices)))]
                else:
                    number = round(route['minimum']+value*(route['maximum']-route['minimum']))/route['divisor']
                if route['key'] == 'chord':
                    engine.commands.put(('chord', number))
                    engine._read_commands(engine.params['quantize'])
                else:
                    engine.params[route['key']] = number
                return True
            return False
        if target.startswith('Chord ') and target[6:] in DEGREES:
            engine.commands.put(('chord', DEGREES.index(target[6:])))
            engine._read_commands(engine.params['quantize'])
            return True
        if target == 'Toggle chords':
            engine.params['chord_enabled'] = not engine.params['chord_enabled']
            return True
        if target == 'Instrument panic':
            engine.instrument.panic()
            return True
        if target in self.routes.get('_notes', {}):
            engine.instrument.play([self.routes['_notes'][target]], self.routes['_velocity'], self.routes['_length'])
            return True
        if target.startswith('Instrument chord ') and target[17:] in DEGREES:
            notes = [int(n+48) for n in chord_notes(engine.params['key'], engine.params['scale'], DEGREES.index(target[17:]))]
            engine.instrument.play(notes, self.routes['_velocity'], self.routes['_length'])
            return True
        return False
