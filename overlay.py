import cv2
import numpy as np
import config

class HUDOverlay:
    def __init__(self):
        # Setup colors (BGR for OpenCV)
        self.color_teal = (254, 242, 0)      # BGR for Neon Teal
        self.color_blue = (254, 172, 79)      # BGR for Neon Blue
        self.color_green = (135, 255, 0)     # BGR for Neon Green
        self.color_red = (108, 65, 255)      # BGR for Neon Red
        self.color_white = (255, 255, 255)
        self.color_gray = (204, 204, 179)

    def draw(self, frame, landmarks, smoothed_landmarks, active_state, gesture_info, conn_status, fps):
        """Annotates OpenCV frame with the hand tracker HUD."""
        h, w, c = frame.shape
        
        # 1. Semi-transparent glass background layout overlays
        # Draw status bars
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 60), (15, 15, 10), -1)      # Top bar
        cv2.rectangle(overlay, (0, h - 35), (w, h), (15, 15, 10), -1) # Bottom bar
        cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

        # 2. Draw Hand Skeleton (MediaPipe style)
        if landmarks:
            # Draw Connections
            connections = [
                # Wrist to Thumb
                (0, 1), (1, 2), (2, 3), (3, 4),
                # Wrist to Index
                (0, 5), (5, 6), (6, 7), (7, 8),
                # Wrist to Middle
                (0, 9), (9, 10), (10, 11), (11, 12),
                # Wrist to Ring
                (0, 13), (13, 14), (14, 15), (15, 16),
                # Wrist to Pinky
                (0, 17), (17, 18), (18, 19), (19, 20),
                # Finger MCP bases
                (5, 9), (9, 13), (13, 17)
            ]
            
            # Use smoothed landmarks for drawing to make the lines smooth too
            points = [(int(lm[0] * w), int(lm[1] * h)) for lm in smoothed_landmarks]
            
            for conn in connections:
                cv2.line(frame, points[conn[0]], points[conn[1]], self.color_blue, 2, cv2.LINE_AA)
                
            # Draw Joints
            for i, pt in enumerate(points):
                # Color code tips differently
                if i in [4, 8, 12, 16, 20]:
                    cv2.circle(frame, pt, 5, self.color_teal, -1, cv2.LINE_AA)
                else:
                    cv2.circle(frame, pt, 4, self.color_green, -1, cv2.LINE_AA)

            # Draw Hand Bounding Box
            xs = [pt[0] for pt in points]
            ys = [pt[1] for pt in points]
            min_x, max_x = max(0, min(xs) - 15), min(w, max(xs) + 15)
            min_y, max_y = max(0, min(ys) - 15), min(h, max(ys) + 15)
            cv2.rectangle(frame, (min_x, min_y), (max_x, max_y), self.color_teal, 1, cv2.LINE_AA)

        # 3. Top Left Status Display: Connection, state, FPS
        status_text = f"NET: {conn_status}  |  FPS: {int(fps)}"
        cv2.putText(frame, status_text, (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_white, 1, cv2.LINE_AA)
        
        state_text = f"MODE: {active_state}"
        cv2.putText(frame, state_text, (15, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.color_teal, 1, cv2.LINE_AA)

        # 4. Top Right Status Display: Current Gesture and stability count
        stable_g = gesture_info.get("stable", "None")
        raw_g = gesture_info.get("raw", "None")
        history_len = gesture_info.get("history_len", 0)
        
        cv2.putText(frame, "GESTURE", (w - 150, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.color_gray, 1, cv2.LINE_AA)
        
        g_color = self.color_teal if stable_g != "None" else self.color_white
        cv2.putText(frame, stable_g, (w - 150, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.65, g_color, 2, cv2.LINE_AA)
        
        # Debouncing visual: draw progress bar of consecutive frame count
        if raw_g != stable_g and raw_g != "None":
            # Draw tiny progress bar for debouncing frames
            progress_w = int((history_len / config.DEBOUNCE_FRAMES) * 80)
            cv2.rectangle(frame, (w - 150, 48), (w - 150 + 80, 52), (50, 50, 50), -1)
            cv2.rectangle(frame, (w - 150, 48), (w - 150 + progress_w, 52), self.color_blue, -1)

        # 5. Bottom Instructions Bar
        hint = "WAKE: Open Palm  |  MOVE: Index  |  DRAG: Fist  |  CANCEL: Victory"
        if active_state == "DRAGGING":
            hint = "DRAGGING: Move Fist Over Phone  |  DROP: Open Palm"
        elif active_state == "TRANSFERRING":
            hint = "TRANSFERRING: Wireless Uploading...  |  CANCEL: Victory"
        elif active_state == "CONFIRMING":
            hint = "COMPLETE: Thumb Up to Continue  |  CANCEL: Victory"
            
        cv2.putText(frame, hint, (15, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.color_gray, 1, cv2.LINE_AA)

        return frame
