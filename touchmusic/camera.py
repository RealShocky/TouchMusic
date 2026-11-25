"""Webcam acquisition and hand landmarks outside the UI thread."""
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from .gestures import GestureMapper


class CameraWorker(QThread):
    frame = Signal(object)
    controls = Signal(object)
    status = Signal(str)

    def __init__(self, index=0):
        super().__init__()
        self.index = index
        self.running = True

    def run(self):
        capture = None
        try:
            import mediapipe as mp
            for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF):
                capture = cv2.VideoCapture(self.index, backend)
                if capture.isOpened():
                    break
                capture.release()
            if not capture.isOpened():
                raise RuntimeError('Camera unavailable. Close other camera apps or choose another camera index.')
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            mapper = GestureMapper()
            with mp.solutions.hands.Hands(max_num_hands=2, model_complexity=0,
                                         min_detection_confidence=.6, min_tracking_confidence=.6) as hands:
                while self.running:
                    success, frame = capture.read()
                    if not success:
                        raise RuntimeError('Camera stopped delivering frames.')
                    frame = cv2.flip(frame, 1)
                    result = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    controls = []
                    seen = set()
                    for landmarks, handedness in zip(result.multi_hand_landmarks or [], result.multi_handedness or []):
                        hand = handedness.classification[0].label
                        seen.add(hand)
                        points = np.array([[p.x, p.y, p.z] for p in landmarks.landmark])
                        controls.append(mapper.update(hand, points))
                        mp.solutions.drawing_utils.draw_landmarks(frame, landmarks, mp.solutions.hands.HAND_CONNECTIONS)
                    for hand in set(mapper.states) - seen:
                        mapper.states.pop(hand, None)
                    self.controls.emit(controls)
                    self.frame.emit(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    self.msleep(20)
        except Exception as exc:
            self.status.emit(str(exc))
        finally:
            if capture:
                capture.release()

    def stop(self):
        self.running = False
