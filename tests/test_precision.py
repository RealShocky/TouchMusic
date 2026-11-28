import numpy as np
from touchmusic.precision import GesturePrecision
from touchmusic.gestures import GestureMapper
from test_finger_poses import hand


def test_calibration_and_deadband_preserve_deliberate_motion():
    precision = GesturePrecision(deadband=.03)
    assert precision.calibrate({'Right': np.linspace(.2, .8, 100), 'Left': [.5]*20}) == 1
    assert precision.map('Right', .2) == 0
    assert precision.map('Right', .8) == 1
    middle = precision.map('Right', .5)
    assert .49 < middle < .51
    assert precision.map('Right', .505) is None
    assert precision.map('Right', .6) > middle
    precision.ranges['Left'] = [1, 1]
    assert precision.map('Left', .5) == .5
    assert precision.map('Right', float('nan')) is None


def test_configurable_pose_hold_and_smoothing():
    mapper = GestureMapper(hold_seconds=.6, smoothing_seconds=.2)
    assert mapper.update('Right', hand(1), 0)['pose'] is None
    assert mapper.update('Right', hand(1), .3)['pose'] is None
    assert mapper.update('Right', hand(1), .61)['pose'] == 1
    assert mapper.update('Right', hand(1), 1.)['pose'] is None
