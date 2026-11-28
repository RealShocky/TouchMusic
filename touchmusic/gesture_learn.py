"""Deliberate movement learning without invoking performance actions."""
import math
import time


class GestureLearner:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.baseline = {}
        self.deadline = self.clock()+10

    def feed(self, controls):
        if self.clock() >= self.deadline:
            return 'timeout'
        changes = []
        for control in controls:
            hand = control.get('hand')
            if hand not in ('Left', 'Right'):
                continue
            for key, value in ((hand, control.get('y')), (hand+'_x', 1-control.get('x', .5)),
                               (hand+'_span', control.get('span'))):
                if type(value) not in (float, int) or not math.isfinite(value):
                    continue
                initial = self.baseline.setdefault(key, value)
                changes.append((abs(value-initial), key))
        changes.sort(reverse=True)
        if changes and changes[0][0] >= .18 and (len(changes) == 1 or changes[0][0] > changes[1][0]*1.4):
            return changes[0][1]
        return None
