import time
import config

class SwipeDetector:
    SWIPE_UP = "Swipe Up"
    SWIPE_DOWN = "Swipe Down"
    SWIPE_LEFT = "Swipe Left"
    SWIPE_RIGHT = "Swipe Right"
    SWIPE_NONE = "None"

    def __init__(self):
        # List of (timestamp, (x, y)) points of palm center (landmark 9)
        self.history = []
        self.last_swipe_time = 0
        self.cooldown = 0.8 # Cooldown duration in seconds to prevent multiple triggerings

    def update(self, landmarks):
        """Track palm center and detect swipes. Returns swipe direction string."""
        now = time.time()
        
        # Cooldown guard
        if now - self.last_swipe_time < self.cooldown:
            return self.SWIPE_NONE

        if not landmarks or len(landmarks) < 21:
            self.history.clear()
            return self.SWIPE_NONE

        # Use middle finger MCP (landmark 9) as palm center
        palm_center = landmarks[9][:2] # (x, y)
        self.history.append((now, palm_center))

        # Filter out points older than SWIPE_MAX_TIME
        self.history = [(t, p) for t, p in self.history if now - t <= config.SWIPE_MAX_TIME]

        if len(self.history) < 5:
            return self.SWIPE_NONE

        # Calculate displacement relative to the oldest point in the window
        start_time, start_pos = self.history[0]
        end_time, end_pos = self.history[-1]
        
        duration = end_time - start_time
        if duration < 0.1: # Must have at least 100ms of data
            return self.SWIPE_NONE

        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        
        # Check if either axis exceeds threshold
        if abs_dx > config.SWIPE_THRESHOLD_DIST or abs_dy > config.SWIPE_THRESHOLD_DIST:
            # Calculate velocity (normalized units per second)
            velocity_x = abs_dx / duration
            velocity_y = abs_dy / duration
            
            # Check if swipe is horizontal or vertical
            if abs_dx > abs_dy and velocity_x > config.SWIPE_MIN_VELOCITY:
                self.history.clear()
                self.last_swipe_time = now
                if dx > 0:
                    return self.SWIPE_RIGHT
                else:
                    return self.SWIPE_LEFT
            elif abs_dy > abs_dx and velocity_y > config.SWIPE_MIN_VELOCITY:
                self.history.clear()
                self.last_swipe_time = now
                if dy > 0:
                    return self.SWIPE_DOWN
                else:
                    return self.SWIPE_UP

        return self.SWIPE_NONE
