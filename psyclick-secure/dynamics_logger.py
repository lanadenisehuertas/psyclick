"""
dynamics_logger.py  —  PsyClick
Stage 0 (HAL) lives here: every raw timestamp is corrected before
it leaves this module.  Nothing downstream sees un-normalised times.

HAL sub-algorithms :
  1. Jitter Compensation   : t_norm = t_raw - (t_raw mod P_target) + delta_latency
  2. Polling-Rate Normalise: auto-detect via platform; align to 1 ms grid
  3. Device Classification : mechanical vs membrane debounce correction
"""

import threading
import time
from pynput import keyboard, mouse

# ── HAL CONSTANTS ─────────────────────────────────────────────────────────────
_P_TARGET = 0.001          # target polling period: 1 ms standard grid

_DEBOUNCE = {
    "mechanical": -0.0023,  # mechanical switches bounce ~2.3 ms early
    "membrane":    0.0,
}


class HardwareAbstractionLayer:
    """
    Detects the keyboard type and computes the per-session latency offset
    (delta_latency) from calibration events.

    All timestamps produced by KeyLogger / MouseLogger are passed through
    hal.correct(t_raw) before being stored, so nothing downstream ever
    sees a raw, device-polluted timestamp.
    """

    def __init__(self):
        self.device_type   = self._detect_device()
        self.debounce      = _DEBOUNCE[self.device_type]
        self._cal_samples  = []
        self.delta_latency = 0.0

    def _detect_device(self):
        # Safe default: membrane.
        # Future: query HID descriptor via pywin32 registry on Windows.
        return "membrane"

    def record_calibration_sample(self, t_raw):
        self._cal_samples.append(t_raw)

    def finalise_calibration(self):
        """
        delta_latency = mean(t_raw mod P_TARGET) across calibration events.
        Called automatically by KeyLogger.stop_logging(calibration_mode=True).
        """
        if not self._cal_samples:
            self.delta_latency = 0.0
            return
        residuals = [t % _P_TARGET for t in self._cal_samples]
        self.delta_latency = sum(residuals) / len(residuals)

    def correct(self, t_raw):
        """
        HAL formula (Cervin et al., 2004):
            t_norm = t_raw - (t_raw mod P_target) + delta_latency + debounce
        """
        jitter = t_raw % _P_TARGET
        return t_raw - jitter + self.delta_latency + self.debounce


# ── KEY LOGGER ────────────────────────────────────────────────────────────────
# Each logger owns ONE operating-system hook for its whole life. Starting and
# stopping a capture only switches recording on and off. Creating a new hook per
# capture let two hooks run at once (two overlapping start requests, or a stop
# that had not finished), and both wrote into the same buffer, so every key
# press was recorded twice.

_DUPLICATE_S = 0.002   # the same event again within 2 ms is the same physical event


class KeyLogger:
    """Captures key DOWN and UP events with HAL-corrected timestamps."""

    def __init__(self, hal):
        self.hal              = hal
        self.raw_data         = []
        self._is_calibration  = False
        self._logging_active  = False
        self.on_first_key     = None
        self._suspended       = False   # PsyClick window not focused: ignore keys
        self._lock            = threading.Lock()
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.daemon = True
        self.listener.start()

    @staticmethod
    def _name(key):
        try:
            return key.char
        except AttributeError:
            return str(key).replace("Key.", "")

    def _record(self, key, event, t_raw):
        k_char = self._name(key)
        t_norm = self.hal.correct(t_raw)
        last = self.raw_data[-1] if self.raw_data else None
        if last and last["key"] == k_char and last["event"] == event and t_norm - last["time"] <= _DUPLICATE_S:
            return False
        self.raw_data.append({"key": k_char, "event": event, "time": t_norm})
        return True

    def on_press(self, key):
        if not self._logging_active or self._suspended:
            return
        try:
            t_raw = time.perf_counter()
            with self._lock:
                first = not self.raw_data
                if self._record(key, "DOWN", t_raw) and self._is_calibration:
                    self.hal.record_calibration_sample(t_raw)
            if first and self.on_first_key:
                try:
                    self.on_first_key()
                except Exception:
                    pass
        except Exception:
            pass

    def on_release(self, key):
        if not self._logging_active or self._suspended:
            return
        try:
            t_raw = time.perf_counter()
            with self._lock:
                self._record(key, "UP", t_raw)
        except Exception:
            pass

    def suspend(self):
        """Stop recording while the PsyClick window is not focused (keys typed in
        other programs are not the client's answer)."""
        self._suspended = True

    def resume(self):
        """Record again; a BREAK marker keeps the gap out of every measure."""
        with self._lock:
            if self._suspended and self._logging_active:
                self.raw_data.append({"key": None, "event": "BREAK", "time": self.hal.correct(time.perf_counter())})
            self._suspended = False

    def start_logging(self, calibration_mode=False, on_first_key=None):
        with self._lock:
            self.raw_data        = []
            self._is_calibration = calibration_mode
            self.on_first_key    = on_first_key
            self._logging_active = True

    def stop_logging(self):
        with self._lock:
            self._logging_active = False
            data, self.raw_data = self.raw_data, []
            if self._is_calibration:
                self.hal.finalise_calibration()
                self._is_calibration = False
        return data


# ── MOUSE LOGGER ──────────────────────────────────────────────────────────────
class MouseLogger:
    """Captures MOVE and CLICK events with HAL-corrected timestamps (one hook, as above)."""

    def __init__(self, hal):
        self.hal      = hal
        self.raw_data = []
        self._logging_active = False
        self._suspended = False
        self._lock = threading.Lock()
        self.listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click)
        self.listener.daemon = True
        self.listener.start()

    def _record(self, x, y, event):
        t_norm = self.hal.correct(time.perf_counter())
        with self._lock:
            last = self.raw_data[-1] if self.raw_data else None
            if (last and last["event"] == event and last["x"] == x and last["y"] == y
                    and t_norm - last["time"] <= _DUPLICATE_S):
                return
            self.raw_data.append({"x": x, "y": y, "event": event, "time": t_norm})

    def on_move(self, x, y):
        if not self._logging_active or self._suspended:
            return
        try:
            self._record(x, y, "MOVE")
        except Exception:
            pass

    def on_click(self, x, y, button, pressed):
        if not self._logging_active or self._suspended or not pressed:
            return
        try:
            self._record(x, y, "CLICK")
        except Exception:
            pass

    def suspend(self):
        self._suspended = True

    def resume(self):
        with self._lock:
            if self._suspended and self._logging_active:
                self.raw_data.append({"x": 0, "y": 0, "event": "BREAK", "time": self.hal.correct(time.perf_counter())})
            self._suspended = False

    def start_logging(self):
        with self._lock:
            self.raw_data = []
            self._logging_active = True

    def stop_logging(self):
        with self._lock:
            self._logging_active = False
            data, self.raw_data = self.raw_data, []
        return data
