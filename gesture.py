import math
import numpy as np
import config

class GestureRecognizer:
    # Simplified gesture set
    GESTURE_NONE = "None"
    GESTURE_INDEX_FINGER = "Index Finger"  # 1 finger open: Cursor movement
    GESTURE_PINCH = "Pinch"                # Thumb + Index touch: Mouse Click (Toggle Grab/Drop)
    GESTURE_VICTORY = "Victory"            # 2 fingers open: Scroll Mode

    def __init__(self):
        # Buffer to keep track of recent raw gestures for debouncing
        self.history = []
        self.stable_gesture = self.GESTURE_NONE

    def get_distance(self, pt1, pt2):
        """Calculate Euclidean distance between two 3D points."""
        return math.sqrt((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2 + (pt1[2] - pt2[2])**2)

    def is_finger_open(self, landmarks, tip_idx, pip_idx):
        """Check if a finger is extended based on relative distance from the wrist."""
        wrist = landmarks[0]
        dist_tip_wrist = self.get_distance(landmarks[tip_idx], wrist)
        dist_pip_wrist = self.get_distance(landmarks[pip_idx], wrist)
        return dist_tip_wrist > dist_pip_wrist

    def classify_raw(self, landmarks):
        """Classify a single frame's landmarks into a raw gesture."""
        if not landmarks or len(landmarks) < 21:
            return self.GESTURE_NONE

        # Get open/closed state of fingers
        index_open = self.is_finger_open(landmarks, 8, 6)
        middle_open = self.is_finger_open(landmarks, 12, 10)
        ring_open = self.is_finger_open(landmarks, 16, 14)
        pinky_open = self.is_finger_open(landmarks, 20, 18)

        # Pinch detection (Distance between thumb tip (4) and index tip (8))
        dist_thumb_index = self.get_distance(landmarks[4], landmarks[8])
        is_pinching = dist_thumb_index < config.PINCH_THRESHOLD

        # 1. PINCH (Click action) - Highest priority
        if is_pinching:
            return self.GESTURE_PINCH

        # 2. VICTORY (Scroll action) - Index and Middle open, Ring and Pinky closed
        if index_open and middle_open and not ring_open and not pinky_open:
            return self.GESTURE_VICTORY

        # 3. INDEX FINGER (Cursor movement) - Index open, others closed
        if index_open and not middle_open and not ring_open and not pinky_open:
            return self.GESTURE_INDEX_FINGER

        return self.GESTURE_NONE

    def update(self, landmarks):
        """Update historical queue with raw gesture and return stable gesture."""
        raw_gesture = self.classify_raw(landmarks)
        self.history.append(raw_gesture)

        # Maintain buffer of size config.DEBOUNCE_FRAMES (default 10)
        if len(self.history) > config.DEBOUNCE_FRAMES:
            self.history.pop(0)

        # Check if gesture is stable: all elements in the buffer must be identical
        if len(self.history) == config.DEBOUNCE_FRAMES:
            first = self.history[0]
            if all(g == first for g in self.history) and first != self.GESTURE_NONE:
                self.stable_gesture = first

        return self.stable_gesture, raw_gesture
