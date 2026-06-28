class AppState:
    HOVER = "HOVER"               # Moving cursor using Index finger, browsing/hovering files
    DRAGGING = "DRAGGING"         # File attached to cursor (toggled by a pinch click)
    TRANSFERRING = "TRANSFERRING" # Uploading file to Android device
    CONFIRMING = "CONFIRMING"     # Success/Error dialog displayed (auto-dismisses or dismisses on click)

class FileTransferStateMachine:
    def __init__(self):
        self.state = AppState.HOVER  # Start awake directly
        self.dragged_file_path = None
        self.is_over_phone_zone = False
        self.last_pinch_time = 0

    def get_state(self):
        return self.state

    def handle_gesture(self, gesture, is_hovering_file=False, selected_path=None):
        """Processes gestures based on simplified comfort-mode state transitions."""
        old_state = self.state

        # Check for Pinch (Click) gesture
        is_click = (gesture == "Pinch")

        # --- FSM Transitions ---

        if self.state == AppState.HOVER:
            # Pinch over a file picks it up (attaches to cursor)
            if is_click and is_hovering_file and selected_path:
                self.dragged_file_path = selected_path
                self.state = AppState.DRAGGING

        elif self.state == AppState.DRAGGING:
            # Cancel drag with Victory (two fingers)
            if gesture == "Victory":
                self.dragged_file_path = None
                self.state = AppState.HOVER
            # Pinch again acts as click to Drop
            elif is_click:
                if self.is_over_phone_zone:
                    self.state = AppState.TRANSFERRING
                else:
                    # Drop outside zone, cancel grab
                    self.dragged_file_path = None
                    self.state = AppState.HOVER

        elif self.state == AppState.TRANSFERRING:
            # Cancel transfer with Victory
            if gesture == "Victory":
                self.dragged_file_path = None
                self.state = AppState.HOVER

        elif self.state == AppState.CONFIRMING:
            # Click (Pinch) or Victory dismisses confirmation
            if is_click or gesture == "Victory":
                self.dragged_file_path = None
                self.state = AppState.HOVER

        # Log transition if changed
        if old_state != self.state:
            print(f"[FSM] State transition: {old_state} -> {self.state}")
            return True
            
        return False
        
    def reset(self):
        """Forces return to hover state."""
        self.state = AppState.HOVER
        self.dragged_file_path = None
        self.is_over_phone_zone = False
