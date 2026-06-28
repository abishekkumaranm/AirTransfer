import cv2
import time
import os
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
from PyQt6.QtCore import QThread, pyqtSignal
import config

MODEL_PATH = "hand_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

def ensure_model_exists():
    """Download hand landmarker task model if missing."""
    if not os.path.exists(MODEL_PATH):
        print(f"Downloading hand landmarker model from {MODEL_URL}...")
        import requests
        response = requests.get(MODEL_URL, stream=True)
        response.raise_for_status()
        with open(MODEL_PATH, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download complete.")

class HandTracker(QThread):
    # Emits dict with frame, landmarks, smoothed_landmarks, hand_side, fps, and confidence
    frame_processed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.running = False
        
        # Make sure model exists
        ensure_model_exists()
        
        # Configure Hand Landmarker Options
        base_options = mp_tasks.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1,
            min_hand_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
            running_mode=vision.RunningMode.VIDEO
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        
        # Landmark smoothing history (EMA state)
        self.prev_smoothed_landmarks = None
        self.alpha = config.CURSOR_SMOOTH_FACTOR
        
        # Monotonically increasing frame timestamp counter for MediaPipe video mode
        self.timestamp_ms = 0

    def run(self):
        self.running = True
        cap = cv2.VideoCapture(config.WEBCAM_INDEX, cv2.CAP_DSHOW) # Use CAP_DSHOW for faster startup on Windows
        if not cap.isOpened():
            cap = cv2.VideoCapture(config.WEBCAM_INDEX)
            
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.WEBCAM_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.WEBCAM_HEIGHT)
        
        while self.running:
            start_time = time.time()
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue
                
            # Mirror frame for intuitive cursor mapping
            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape
            
            # MediaPipe expects RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Create MediaPipe Image object
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            # Update frame timestamp (strictly increasing)
            self.timestamp_ms += 33
            
            # Run task inference
            result = self.detector.detect_for_video(mp_image, self.timestamp_ms)
            
            landmarks_list = []
            smoothed_list = []
            hand_side = "None"
            confidence = 0.0
            
            if result.hand_landmarks:
                # Grab the first hand tracked
                hand_landmarks = result.hand_landmarks[0]
                
                if result.handedness:
                    confidence = result.handedness[0][0].score
                    # category_name is "Left" or "Right"
                    hand_side = result.handedness[0][0].category_name
                
                # Extract coordinates
                for lm in hand_landmarks:
                    landmarks_list.append((lm.x, lm.y, lm.z))
                
                # Apply Landmark Smoothing using Exponential Moving Average
                if self.prev_smoothed_landmarks is None or len(self.prev_smoothed_landmarks) != len(landmarks_list):
                    self.prev_smoothed_landmarks = np.array(landmarks_list)
                    smoothed_list = landmarks_list
                else:
                    raw_arr = np.array(landmarks_list)
                    # Adaptive smoothing factor: if hand moves fast, increase alpha; if slow, decrease
                    diff = np.linalg.norm(raw_arr - self.prev_smoothed_landmarks, axis=1).mean()
                    adaptive_alpha = np.clip(self.alpha + diff * 5.0, self.alpha, 0.8)
                    
                    smoothed_arr = adaptive_alpha * raw_arr + (1.0 - adaptive_alpha) * self.prev_smoothed_landmarks
                    self.prev_smoothed_landmarks = smoothed_arr
                    smoothed_list = [tuple(lm) for lm in smoothed_arr]
            else:
                self.prev_smoothed_landmarks = None
                
            # Calculate real-time FPS
            current_time = time.time()
            fps = 1.0 / (current_time - start_time + 1e-6)
            
            # Emit result dictionary
            self.frame_processed.emit({
                "frame": frame,
                "landmarks": landmarks_list,
                "smoothed_landmarks": smoothed_list,
                "hand_side": hand_side,
                "fps": fps,
                "confidence": confidence
            })
            
            # Cap thread loop slightly above target 60FPS
            elapsed = time.time() - start_time
            sleep_time = max(0.005, (1.0 / 65.0) - elapsed)
            time.sleep(sleep_time)
            
        cap.release()
        self.detector.close()
        
    def stop(self):
        self.running = False
        self.wait()
