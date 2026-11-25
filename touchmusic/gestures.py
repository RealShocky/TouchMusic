"""Smoothed hand movement and deliberate, one-shot pose events."""
import time
import numpy as np

POSE_HOLD_SECONDS = .25


def finger_count(points):
    """Count extended fingers in hand-relative coordinates."""
    bases = np.array([5, 9, 13, 17])
    palm = points[bases + 1] - points[bases]
    fingers = points[bases + 3] - points[bases + 1]
    alignment = np.sum(palm * fingers, axis=1)
    lengths = np.linalg.norm(palm, axis=1) * np.linalg.norm(fingers, axis=1)
    extended = (lengths > 1e-6) & (alignment > .62 * lengths)
    count = int(np.count_nonzero(extended))
    scale = np.linalg.norm(points[9] - points[0])
    thumb = (np.linalg.norm(points[4] - points[5]) > .85 * scale
             and np.linalg.norm(points[4] - points[0]) > scale)
    if count == 4 and thumb:
        return 5
    if count == 0 and thumb:
        first = points[3] - points[2]
        last = points[4] - points[3]
        length = np.linalg.norm(first) * np.linalg.norm(last)
        if length > 1e-6 and np.dot(first, last) > .75 * length:
            return None
    return count


class GestureMapper:
    def __init__(self):
        self.states = {}

    def lost(self):
        self.states.clear()

    def update(self, hand, points, now=None):
        now = time.monotonic() if now is None else now
        points = np.asarray(points)
        scale = max(float(np.linalg.norm(points[0, :2] - points[9, :2])), .03)
        distance = float(np.linalg.norm(points[4, :2] - points[8, :2])) / scale
        old = self.states.get(hand)
        pinched = distance < (.38 if old and old['held'] else .25)
        x, y = float(np.clip(1 - points[9, 0], 0, 1)), float(np.clip(1 - points[9, 1], 0, 1))
        span = float(np.clip((distance - .25) / .9, 0, 1))
        if old:
            elapsed = max(0, now - old['time'])
            alpha = 1 - np.exp(-elapsed / .09)
            x = old['x'] + alpha * (x - old['x'])
            y = old['y'] + alpha * (y - old['y'])
            span = old['span'] + alpha * (span - old['span'])
        edge = pinched and (not old or not old['held'])
        count = finger_count(points)
        if pinched and count != 0:
            count = None
        same = old is not None and count == old['count']
        since = old['since'] if same else now
        fired = old['fired'] if same else False
        pose = None
        if count is not None and not fired and now - since >= POSE_HOLD_SECONDS:
            pose = count
            fired = True
        self.states[hand] = {'held': pinched, 'x': x, 'y': y, 'time': now,
                             'span': span, 'count': count, 'since': since, 'fired': fired}
        return {'hand': hand, 'x': x, 'y': y, 'pinch': edge, 'held': pinched,
                'fingers': count, 'pose': pose, 'span': span}
