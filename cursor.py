import config

class CursorController:
    def __init__(self):
        # Current smoothed coordinates mapped to screen
        self.x = 0.0
        self.y = 0.0
        
        # Previous raw coordinates for adaptive velocity calculation
        self.prev_raw_x = None
        self.prev_raw_y = None
        
        # Active tracking window inside camera space (crops outer margins for comfort)
        self.x_min = 0.25
        self.x_max = 0.75
        self.y_min = 0.25
        self.y_max = 0.75
        
        # Scaling multiplier
        self.sensitivity = config.BASE_SENSITIVITY

    def update(self, landmarks, window_w, window_h):
        """Processes finger tip landmark, updates cursor position, and returns (x, y)."""
        if not landmarks or len(landmarks) < 21:
            return int(self.x), int(self.y)

        # Index finger tip is landmark 8
        raw_x = landmarks[8][0]
        raw_y = landmarks[8][1]

        # 1. Normalize raw coordinate inside our active interaction zone
        norm_x = (raw_x - self.x_min) / (self.x_max - self.x_min)
        norm_y = (raw_y - self.y_min) / (self.y_max - self.y_min)

        # Clamp between 0.0 and 1.0 to prevent cursor from flying off-screen
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        # Map to window pixels
        target_x = norm_x * window_w
        target_y = norm_y * window_h

        # 2. Adaptive Sensitivity (Optional but highly recommended for accuracy)
        # Compute finger velocity. If moving quickly, increase speed. If moving slowly, decrease for precision.
        alpha = config.CURSOR_SMOOTH_FACTOR
        if self.prev_raw_x is not None:
            # Distance moved in normalized coordinates
            dist_moved = ((raw_x - self.prev_raw_x) ** 2 + (raw_y - self.prev_raw_y) ** 2) ** 0.5
            
            if config.ADAPTIVE_SENSITIVITY:
                # If velocity is high, increase smoothing factor (less filter, faster response)
                # If velocity is low, decrease smoothing factor (high filter, stable cursor)
                scale_adjustment = dist_moved * 8.0 # Tuned multiplier
                alpha = max(0.08, min(0.6, config.CURSOR_SMOOTH_FACTOR + scale_adjustment))
                
        self.prev_raw_x = raw_x
        self.prev_raw_y = raw_y

        # 3. Apply Exponential Moving Average (EMA) Smoothing
        self.x = alpha * target_x + (1.0 - alpha) * self.x
        self.y = alpha * target_y + (1.0 - alpha) * self.y

        return int(self.x), int(self.y)
