from pynput import keyboard
import time

class KeyLogger:
    def __init__(self):
        self.raw_data = [] 
        self.listener = None

    def on_press(self, key):
        """Callback when a key is pressed."""
        try:
            # Try getting the character (letters/numbers)
            k_char = key.char
        except AttributeError:
            # Handle special keys (Space, Enter, Shift)
            k_char = str(key).replace("Key.", "")
        
        # Log: [Key, Event, Timestamp]
        self.raw_data.append({
            'key': k_char, 
            'event': 'DOWN', 
            'time': time.perf_counter()
        })

    def start_logging(self):
        """Starts the background listener."""
        self.raw_data = []
        # Suppress errors implies non-blocking
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()
        print(">> Logger Started (Background)...")

    def stop_logging(self):
        """Stops the listener and returns the data."""
        if self.listener:
            self.listener.stop()
            self.listener = None
        print(f">> Logger Stopped. Captured {len(self.raw_data)} events.")
        return self.raw_data