# AI-Powered Air Gesture File Transfer (AirTransfer)

AirTransfer is a production-quality, touch-free gesture-controlled file manager desktop application. It enables users to browse, select, drag, and wirelessly transfer any file from a Windows laptop to an Android phone using only hand gestures. The desktop app leverages OpenCV and MediaPipe Hands to capture webcam input, smoothing coordinates to control an in-app virtual mouse, while a background thread automatically discovers and syncs with a FastAPI server running on the Android phone.

---

## Hand Gesture Reference Guide

To interact with the file manager without a physical keyboard or mouse, use the following gestures. Ensure your hand is in clear view of the webcam. All actions require **10 consecutive frames** of stability to prevent accidental triggers.

| Gesture | Hand Shape | Action | Context |
| :--- | :--- | :--- | :--- |
| **Open Palm** | All 5 fingers extended | **Wake System** / **Drop File** | Wakes system from sleep; Drops grabbed file in the drop zone. |
| **Index Finger** | Index extended, others closed | **Control Virtual Cursor** | Moves the circular in-app cursor smoothly. |
| **Pinch** | Index tip & Thumb tip touching | **Select File** | Highlights a file and displays details in the file explorer. |
| **Closed Fist** | All fingers closed tightly | **Grab / Drag File** | Grabs the selected file. A floating icon follows your hand. |
| **Thumb Up** | Thumb up, other fingers closed | **Confirm Transfer** | Dismisses the "Transfer Success" screen and returns to explorer. |
| **Victory** | Index & Middle open, others closed | **Cancel / Reset** | Cancels a drag, dismisses errors, or resets to Hover mode. |
| **Swipe Up** | Rapid upward hand movement | **Scroll Down** | Scrolls the active file list downward. |
| **Swipe Down** | Rapid downward hand movement | **Scroll Up** | Scrolls the active file list upward. |
| **Swipe Left** | Rapid leftward hand movement | **Previous Folder** | Navigates back to the previous folder directory. |
| **Swipe Right** | Rapid rightward hand movement | **Next Folder** | Navigates forward in your folder history. |

---

## Installation & Setup

### 1. Windows Desktop Setup

1. **Install Python**: Make sure Python 3.8+ is installed on your Windows laptop.
2. **Install Dependencies**:
   Open PowerShell or Command Prompt, navigate to the project directory, and run:
   ```powershell
   pip install -r requirements.txt
   ```
3. **Run Application**:
   Launch the desktop file manager by running:
   ```powershell
   python main.py
   ```

---

### 2. Android Receiver Setup

You can run the FastAPI receiver app on Android using either **Termux** or **Pyroid 3**.

#### Option A: Setup using Termux (Recommended - Free)
1. Download and install **Termux** from F-Droid.
2. Open Termux and update your packages:
   ```bash
   pkg update && pkg upgrade
   ```
3. Install Python:
   ```bash
   pkg install python
   ```
4. Install the required Python packages:
   ```bash
   pip install fastapi uvicorn python-multipart
   ```
5. **Copy `phone_receiver/server.py` to your phone**:
   * *Method 1 (USB)*: Connect phone to laptop, transfer `server.py` to the phone's storage.
   * *Method 2 (Local Server)*: On your Windows laptop, open a terminal in the `phone_receiver` folder and run `python -m http.server 8000`. On your phone's browser, open `http://<laptop_ip>:8000` and download `server.py`.
6. Run the server inside Termux:
   ```bash
   python server.py
   ```

#### Option B: Setup using Pyroid 3 (Google Play Store)
1. Install **Pyroid 3** from the Google Play Store.
2. Open Pyroid 3 and tap the menu icon (top-left) -> select **Pip**.
3. Install packages: `fastapi`, `uvicorn`, `python-multipart`.
4. Open the `server.py` file in Pyroid 3, and press the yellow **Play** icon to run the server.

*Once running, the receiver dashboard is accessible on your phone's local browser at `http://localhost:8000`.*

---

## How It Works: Zero-Configuration Networking

1. **Broadcasting**: As soon as `server.py` starts on your Android phone, it starts broadcasting discovery beacons containing its IP and port over UDP port `9999` to the entire local network (`255.255.255.255`) every 2 seconds.
2. **Auto-Discovery**: The Windows application runs a listener on UDP port `9999`. It captures the beacon packet, parses the device IP, and connects immediately.
3. **Reconnection & Interruptions**: If your Wi-Fi changes or the network drops, the listener will notice the lack of a beacon for 5 seconds, mark the device as offline, and immediately search again to automatically reconnect when the device becomes available.

---

## Troubleshooting Guide

### 1. The desktop app displays "Scanning Local Network..." but won't connect.
* **Same Wi-Fi Network**: Ensure both your laptop and phone are connected to the exact same Wi-Fi router.
* **AP/Client Isolation**: Some public or school Wi-Fi networks enable AP Isolation which prevents devices on the same Wi-Fi from talking to each other. Use a home network or your phone's **Wi-Fi Hotspot** (connect your laptop to your phone's hotspot).
* **Windows Firewall**: Windows might block incoming UDP broadcast beacons. Allow Python through the Windows Defender Firewall.

### 2. The webcam feed is black or shows a different camera.
* Open `config.py` on your laptop and check the `WEBCAM_INDEX` variable. If you have an external webcam, change the index from `0` to `1` or `2` and restart the application.

### 3. The cursor is jittery or jumps around.
* **Lighting**: Ensure your face/hand is well-lit and not back-lit (e.g. don't sit directly in front of a bright window).
* **Smoothing**: You can increase the smoothing level by lowering `CURSOR_SMOOTH_FACTOR` in `config.py` (e.g. change it from `0.25` to `0.15`).
