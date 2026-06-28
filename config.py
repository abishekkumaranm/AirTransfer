import os

# Webcam & MediaPipe settings
WEBCAM_INDEX = 0
WEBCAM_WIDTH = 640
WEBCAM_HEIGHT = 480
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.7

# Screen/Window mapping settings
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800

# Virtual Cursor parameters
CURSOR_SMOOTH_FACTOR = 0.25   # EMA filter factor (0 to 1, smaller is smoother)
BASE_SENSITIVITY = 1.6        # Screen coordinates speed scaling multiplier
ADAPTIVE_SENSITIVITY = True   # Enable speed-based scaling

# Gesture recognition settings
DEBOUNCE_FRAMES = 10          # Number of consecutive frames needed to switch gestures
PINCH_THRESHOLD = 0.04        # Normalized distance between thumb tip and index tip for Pinch
FIST_ANGLE_THRESHOLD = 90     # Average angle below which fingers are considered folded

# Swipe detection
SWIPE_THRESHOLD_DIST = 0.12   # Minimum relative distance moved for a swipe
SWIPE_MAX_TIME = 0.5          # Maximum duration in seconds for a swipe
SWIPE_MIN_VELOCITY = 0.4      # Minimum velocity (distance per second) for a swipe

# Networking Settings
UDP_DISCOVERY_PORT = 9999     # Listening/Broadcasting port for device auto-discovery
DEFAULT_FASTAPI_PORT = 8000   # Server port for file transfers
UDP_BROADCAST_INTERVAL = 2.0  # Seconds between UDP broadcast beacons

# File explorer configuration
USER_FOLDERS = {
    "Desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
    "Downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
    "Documents": os.path.join(os.path.expanduser("~"), "Documents"),
    "Pictures": os.path.join(os.path.expanduser("~"), "Pictures"),
    "Videos": os.path.join(os.path.expanduser("~"), "Videos")
}

# Supported file formats mapped to readable categories
SUPPORTED_EXTENSIONS = {
    # PDF
    ".pdf": "PDF Document",
    # Images
    ".png": "Image", ".jpg": "Image", ".jpeg": "Image", ".gif": "Image", ".bmp": "Image",
    # Videos
    ".mp4": "Video", ".mkv": "Video", ".avi": "Video", ".mov": "Video",
    # Word documents
    ".doc": "Word Document", ".docx": "Word Document",
    # Excel files
    ".xls": "Excel Sheet", ".xlsx": "Excel Sheet",
    # PowerPoint
    ".ppt": "PowerPoint Presentation", ".pptx": "PowerPoint Presentation",
    # ZIP files
    ".zip": "ZIP Archive", ".rar": "RAR Archive", ".tar": "Archive", ".gz": "Archive",
    # Text files
    ".txt": "Text File", ".md": "Markdown File", ".log": "Log File", ".json": "JSON File"
}

# Modern UI Themes (CSS Formats)
THEMES = {
    "dark": {
        "background": "#0F0F1A",        # Deep dark space background
        "card_bg": "rgba(25, 25, 45, 0.6)", # Glassmorphic dark card
        "border": "rgba(255, 255, 255, 0.1)",
        "accent_teal": "#00F2FE",      # Neon teal highlight
        "accent_blue": "#4FACFE",      # Smooth blue gradient start
        "accent_purple": "#7F00FF",    # Purple accent
        "text_primary": "#FFFFFF",
        "text_secondary": "#B3B3CC",
        "success": "#00FF87",          # Vivid emerald
        "error": "#FF416C"             # Bright warning red
    },
    "light": {
        "background": "#F4F4F9",        # Light clean workspace background
        "card_bg": "rgba(255, 255, 255, 0.8)", # Clean card bg
        "border": "rgba(0, 0, 0, 0.1)",
        "accent_teal": "#008B9B",      # Deep dark teal (readable on light bg)
        "accent_blue": "#0052D4",      # Deep blue
        "accent_purple": "#6B00D4",    # Violet
        "text_primary": "#1A1A2E",
        "text_secondary": "#555577",
        "success": "#00994D",          # Forest green
        "error": "#D32F2F"             # Deep red
    }
}

CURRENT_THEME = "dark"

COLORS = dict(THEMES[CURRENT_THEME])

def toggle_theme():
    """Toggles the active theme mode in-place so all dictionary references stay valid."""
    global CURRENT_THEME, COLORS
    CURRENT_THEME = "light" if CURRENT_THEME == "dark" else "dark"
    COLORS.clear()
    COLORS.update(THEMES[CURRENT_THEME])
    print(f"[Theme] Active theme switched to: {CURRENT_THEME.upper()}")
