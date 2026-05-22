"""
dynamics_logger.py  —  PsyClick
Stage 0 (HAL) lives here: every raw timestamp is corrected before
it leaves this module.  Nothing downstream sees un-normalised times.

HAL sub-algorithms :
  1. Jitter Compensation   : t_norm = t_raw - (t_raw mod P_target) + delta_latency
  2. Polling-Rate Normalise: auto-detect via platform; align to 1 ms grid
  3. Device Classification : mechanical vs membrane debounce correction
"""

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
class KeyLogger:
    """
    Captures key DOWN and UP events with HAL-corrected timestamps.
    """

    def __init__(self, hal):
        self.hal              = hal
        self.raw_data         = []
        self._is_calibration  = False
        self._logging_active  = False
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release,
        )
        self.listener.start()

    def on_press(self, key):
        if not self._logging_active: return
        
        # Fire callback on first key press (when raw_data is empty)
        if not self.raw_data and hasattr(self, 'on_first_key') and self.on_first_key:
            try:
                self.on_first_key()
            except Exception:
                pass

        try:
            t_raw = time.perf_counter()
            if self._is_calibration:
                self.hal.record_calibration_sample(t_raw)
            t_norm = self.hal.correct(t_raw)
            try:
                k_char = key.char
            except AttributeError:
                k_char = str(key).replace("Key.", "")
            self.raw_data.append({"key": k_char, "event": "DOWN", "time": t_norm})
        except Exception:
            pass

    def on_release(self, key):
        if not self._logging_active: return
        try:
            t_norm = self.hal.correct(time.perf_counter())
            try:
                k_char = key.char
            except AttributeError:
                k_char = str(key).replace("Key.", "")
            self.raw_data.append({"key": k_char, "event": "UP", "time": t_norm})
        except Exception:
            pass

    def start_logging(self, calibration_mode=False, on_first_key=None):
        # Force a clean start: stop any existing listener first
        self.stop_logging()
        
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release,
        )
        self.listener.start()
        
        self.raw_data        = []
        self._is_calibration = calibration_mode
        self._logging_active = True
        self.on_first_key = on_first_key

    def stop_logging(self):
        self._logging_active = False
        
        # Explicitly stop and join the listener thread to release OS hooks
        if hasattr(self, 'listener') and self.listener:
            try:
                self.listener.stop()
                self.listener.join(timeout=0.5)
            except Exception:
                pass
            self.listener = None

        if self._is_calibration:
            self.hal.finalise_calibration()
            self._is_calibration = False
        return self.raw_data


# ── MOUSE LOGGER ──────────────────────────────────────────────────────────────
class MouseLogger:
    """Captures MOVE and CLICK events with HAL-corrected timestamps."""

    def __init__(self, hal):
        self.hal      = hal
        self.raw_data = []
        self._logging_active = False
        self.listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click)
        self.listener.start()

    def on_move(self, x, y):
        if not self._logging_active: return
        try:
            t_norm = self.hal.correct(time.perf_counter())
            self.raw_data.append({"x": x, "y": y, "event": "MOVE", "time": t_norm})
        except Exception:
            pass

    def on_click(self, x, y, button, pressed):
        if not self._logging_active: return
        try:
            if pressed:
                t_norm = self.hal.correct(time.perf_counter())
                self.raw_data.append({"x": x, "y": y, "event": "CLICK", "time": t_norm})
        except Exception:
            pass

    def start_logging(self):
        self.stop_logging()
        self.listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click)
        self.listener.start()
        self.raw_data = []
        self._logging_active = True

    def stop_logging(self):
        self._logging_active = False
        if hasattr(self, 'listener') and self.listener:
            try:
                self.listener.stop()
                self.listener.join(timeout=0.5)
            except Exception:
                pass
            self.listener = None
        return self.raw_data
