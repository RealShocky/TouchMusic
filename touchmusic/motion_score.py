"""Versioned, bounded gesture automation on a beat timeline."""
from copy import deepcopy
import math


class MotionScore:
    MAX_EVENTS = 4096

    def __init__(self):
        self.events = []
        self.mode = 'Stopped'
        self.beat = 0.
        self.last_frame = 0
        self.cursor = 0

    @staticmethod
    def validate(value):
        if not isinstance(value, dict) or value.get('version') != 1:
            raise ValueError('Unsupported Motion Score version.')
        events = value.get('events')
        if not isinstance(events, list) or len(events) > MotionScore.MAX_EVENTS:
            raise ValueError('Motion Score exceeds the event limit.')
        previous = -1.
        for event in events:
            if (not isinstance(event, dict) or type(event.get('beat')) not in (float, int)
                    or not math.isfinite(event['beat']) or not 0 <= event['beat'] <= 14400
                    or event['beat'] < previous or event.get('kind') not in ('level', 'action')
                    or not isinstance(event.get('target'), str) or not 1 <= len(event['target']) <= 128):
                raise ValueError('Invalid Motion Score event.')
            if event['kind'] == 'level' and (type(event.get('value')) not in (float, int)
                    or not math.isfinite(event['value']) or not 0 <= event['value'] <= 1):
                raise ValueError('Invalid Motion Score value.')
            previous = event['beat']

    def settings(self):
        return {'version': 1, 'events': deepcopy(self.events)}

    def load(self, value):
        self.validate(value)
        self.stop()
        self.events = deepcopy(value['events'])

    def start(self, mode, frame):
        if mode not in ('Recording', 'Playing'):
            raise ValueError('Invalid score mode.')
        self.mode, self.beat, self.cursor, self.last_frame = mode, 0., 0, frame
        if mode == 'Recording':
            self.events = []

    def stop(self):
        self.mode = 'Stopped'

    def advance(self, frame, period):
        if self.mode == 'Stopped':
            return []
        self.beat += max(0, frame-self.last_frame)/max(1, period)
        self.last_frame = frame
        if self.beat > 14400:
            self.stop()
            return []
        due = []
        if self.mode == 'Playing':
            while self.cursor < len(self.events) and self.events[self.cursor]['beat'] <= self.beat:
                due.append(deepcopy(self.events[self.cursor]))
                self.cursor += 1
            if self.cursor >= len(self.events):
                self.stop()
        return due

    def capture(self, kind, target, value=None):
        if self.mode != 'Recording':
            return
        event = {'beat': self.beat, 'kind': kind, 'target': target}
        if kind == 'level':
            event['value'] = value
        # Validate before mutation; coalesce repeated values while preserving final moves.
        self.validate({'version': 1, 'events': [event]})
        if self.events and kind == 'level' and self.events[-1]['kind'] == kind:
            previous = self.events[-1]
            if previous['target'] == target and abs(previous['value']-value) < .002:
                return
        if len(self.events) >= self.MAX_EVENTS:
            self.stop()
            return
        self.events.append(event)
