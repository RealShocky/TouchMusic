"""Calibrated movement ranges and output hysteresis, independent of camera IO."""
import math


class GesturePrecision:
    def __init__(self, ranges=None, deadband=.02, sensitivity=1.):
        self.ranges = dict(ranges or {})
        self.deadband = deadband
        self.sensitivity = sensitivity
        self.last = {}

    def reset(self):
        self.last.clear()

    def map(self, axis, value, state_key=None):
        if not math.isfinite(value):
            return None
        bounds = self.ranges.get(axis, (0., 1.))
        if (not isinstance(bounds, (list, tuple)) or len(bounds) != 2
                or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in bounds)
                or bounds[1] - bounds[0] < .15):
            bounds = (0., 1.)
        normalized = (value - bounds[0]) / (bounds[1] - bounds[0])
        normalized = max(0., min(1., .5 + (normalized - .5) * self.sensitivity))
        state_key = state_key or axis
        previous = self.last.get(state_key)
        if previous is not None and abs(normalized - previous) < self.deadband and normalized not in (0., 1.):
            return None
        if normalized == previous:
            return None
        self.last[state_key] = normalized
        return normalized

    def calibrate(self, samples):
        """Use deliberate movement extremes. Ignore axes with insufficient travel."""
        accepted = {}
        for axis, values in samples.items():
            valid = sorted(float(value) for value in values if math.isfinite(value))
            if len(valid) < 10:
                continue
            low, high = valid[int((len(valid)-1)*.02)], valid[int((len(valid)-1)*.98)]
            if high - low >= .15:
                accepted[axis] = [low, high]
        self.ranges.update(accepted)
        self.reset()
        return len(accepted)
