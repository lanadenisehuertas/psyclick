from pynput import keyboard, mouse
import time

class KeyLogger:
    def __init__(self):
        self.raw_data = [] 
        self.listener = None

    def on_press(self, key):
        try:
            k_char = key.char
        except AttributeError:
            k_char = str(key).replace("Key.", "")
        
        self.raw_data.append({
            'key': k_char, 
            'event': 'DOWN', 
            'time': time.perf_counter()
        })

    def start_logging(self):
        self.raw_data = []
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()
        print(">> KeyLogger Started...")

    def stop_logging(self):
        if self.listener:
            self.listener.stop()
            self.listener = None
        return self.raw_data

class MouseLogger:
    def __init__(self):
        self.raw_data = []
        self.listener = None

    def on_move(self, x, y):
        # Capture continuous movement for Velocity/Curvature calculations
        self.raw_data.append({
            'x': x,
            'y': y,
            'event': 'MOVE',
            'time': time.perf_counter()
        })

    def on_click(self, x, y, button, pressed):
        if pressed:
            self.raw_data.append({
                'x': x,
                'y': y,
                'event': 'CLICK',
                'time': time.perf_counter()
            })

    def start_logging(self):
        self.raw_data = []
        # Listen to both Move and Click events
        self.listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click)
        self.listener.start()
        print(">> MouseLogger Started (Tracking Path)...")

    def stop_logging(self):
        if self.listener:
            self.listener.stop()
            self.listener = None
        return self.raw_data