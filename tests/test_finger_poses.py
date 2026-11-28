import numpy as np
from touchmusic.gestures import GestureMapper, finger_count


def hand(count):
    points = np.zeros((21, 3))
    points[0] = (.5, .8, 0)
    for position, (base, x) in enumerate(zip((5, 9, 13, 17), (.4, .47, .54, .61))):
        extended = position < count
        for joint, y in enumerate((.62, .51, .42, .34) if extended else (.62, .51, .55, .62)):
            points[base + joint] = (x, y, 0)
    points[3] = (.34, .68, 0)
    points[4] = (.22 if count == 5 else .51, .70, 0)
    return points


def test_counts_fingers_when_the_hand_is_rotated():
    for count in range(6):
        assert finger_count(hand(count)) == count
        rotated = hand(count)[:, [1, 0, 2]].copy()
        rotated[:, 0] *= -1
        assert finger_count(rotated) == count


def test_pose_requires_a_hold_and_fires_only_once():
    mapper = GestureMapper()
    assert mapper.update('Right', hand(1), 0)['pose'] is None
    assert mapper.update('Right', hand(1), .12)['pose'] is None
    assert mapper.update('Right', hand(2), .2)['pose'] is None
    assert mapper.update('Right', hand(2), .5)['pose'] == 2
    assert mapper.update('Right', hand(2), 1)['pose'] is None
    assert mapper.update('Left', hand(2), 1)['pose'] is None
    assert mapper.update('Left', hand(2), 1.3)['pose'] == 2
    mapper.lost()
    assert mapper.update('Right', hand(2), 2)['pose'] is None


def test_pinch_suppresses_finger_pose():
    mapper = GestureMapper()
    points = hand(1)
    points[4] = points[8]
    assert mapper.update('Right', points, 0)['pinch']
    assert mapper.update('Right', points, .5)['pose'] is None


def test_fist_is_detected_even_if_thumb_touches_folded_index():
    mapper = GestureMapper()
    points = hand(0)
    points[4] = points[8]
    assert mapper.update('Left', points, 0)['pinch']
    held = mapper.update('Left', points, .3)
    assert held['held'] and held['pose'] == 0
    assert mapper.update('Left', points, .5)['pose'] is None
