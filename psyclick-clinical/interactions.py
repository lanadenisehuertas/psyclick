"""interactions.py — Animation & Interaction utilities for PsyClick (CustomTkinter)"""
import customtkinter as ctk


# ── Color helpers ──────────────────────────────────────────────────────────────
def _lerp_color(c1, c2, t):
    """Interpolate between two hex colors (t in [0,1])."""
    def parse(h):
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r1, g1, b1 = parse(c1)
    r2, g2, b2 = parse(c2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _ease(t):
    """Smooth-step easing: 3t²-2t³"""
    return t * t * (3 - 2 * t)


# ── Smooth card hover ──────────────────────────────────────────────────────────
def smooth_hover(frame, normal="#E4F0F0", hover="#0ABFBC", steps=8, delay=12):
    """Smooth border-color transition on hover for CTkFrame cards."""
    _state = {"inside": False, "job": None, "step": 0, "direction": 1}

    def _cancel():
        if _state["job"]:
            try:
                frame.after_cancel(_state["job"])
            except Exception:
                pass
            _state["job"] = None

    def _animate():
        _state["step"] = max(0, min(steps, _state["step"] + _state["direction"]))
        t = _ease(_state["step"] / steps)
        color = _lerp_color(normal, hover, t)
        try:
            frame.configure(border_color=color)
        except Exception:
            return
        if 0 < _state["step"] < steps:
            _state["job"] = frame.after(delay, _animate)

    def _on(e=None):
        _cancel()
        _state["direction"] = 1
        _animate()

    def _off(e=None):
        _cancel()
        _state["direction"] = -1
        _animate()

    def _attach(w):
        for ch in w.winfo_children():
            ch.bind("<Enter>", _on, add="+")
            ch.bind("<Leave>", _off, add="+")
            _attach(ch)

    frame.bind("<Enter>", _on, add="+")
    frame.bind("<Leave>", _off, add="+")
    frame.after(150, lambda: _attach(frame))
    return frame


# ── Button click flash ─────────────────────────────────────────────────────────
def click_flash(widget, flash_color, normal_color, duration=130):
    """Briefly flash a CTkButton to confirm a click."""
    def _restore():
        try:
            widget.configure(fg_color=normal_color)
        except Exception:
            pass
    try:
        widget.configure(fg_color=flash_color)
        widget.after(duration, _restore)
    except Exception:
        pass


# ── Animated counter ───────────────────────────────────────────────────────────
def animate_counter(label, target, duration=650, prefix="", suffix="", steps=28):
    """Count-up from current value to target on a CTkLabel."""
    try:
        current = label.cget("text").strip().lstrip(prefix).rstrip(suffix)
        start = int("".join(c for c in current if c.isdigit()) or "0")
    except Exception:
        start = 0

    if start == target:
        return

    interval = max(8, duration // steps)

    def _tick(step):
        t = _ease(step / steps)
        value = int(start + (target - start) * t)
        try:
            label.configure(text=f"{prefix}{value}{suffix}")
        except Exception:
            return
        if step < steps:
            label.after(interval, lambda: _tick(step + 1))
        else:
            try:
                label.configure(text=f"{prefix}{target}{suffix}")
            except Exception:
                pass

    _tick(1)


# ── Toast notification ─────────────────────────────────────────────────────────
_TOAST_COLORS = {
    "success": ("#36C98E", "#ECFDF5", "✓"),
    "error":   ("#F27C7C", "#FFF0F0", "✕"),
    "info":    ("#0ABFBC", "#E0FAFA", "i"),
    "warning": ("#F5A623", "#FFFBEB", "!"),
}


class Toast:
    """Slide-up toast notification (non-blocking, auto-dismisses)."""
    _stack = []

    def __init__(self, root, message, kind="success", duration=2800):
        Toast._stack.append(self)
        self.root = root
        self.duration = duration

        color, bg, icon = _TOAST_COLORS.get(kind, _TOAST_COLORS["info"])

        self.win = ctk.CTkToplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(fg_color=bg)

        root.update_idletasks()
        rw = root.winfo_width()
        rh = root.winfo_height()
        rx = root.winfo_rootx()
        ry = root.winfo_rooty()
        w, h = 340, 58

        # Stack toasts if multiple are showing
        offset = len([t for t in Toast._stack if t is not self and t.win.winfo_exists()]) * (h + 8)
        self._x = rx + rw - w - 24
        self._y_end = ry + rh - h - 24 - offset
        self._y_start = ry + rh + h

        self.win.geometry(f"{w}x{h}+{self._x}+{self._y_start}")

        frame = ctk.CTkFrame(self.win, fg_color=bg, corner_radius=10,
                              border_width=1, border_color=color)
        frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Colored left accent strip
        strip = ctk.CTkFrame(frame, width=4, fg_color=color, corner_radius=0)
        strip.pack(side="left", fill="y", padx=(0, 0))
        strip.pack_propagate(False)

        ctk.CTkLabel(frame, text=icon, font=("DM Sans", 15, "bold"),
                     text_color=color, fg_color="transparent"
                     ).pack(side="left", padx=(10, 4))
        ctk.CTkLabel(frame, text=message, font=("DM Sans", 12),
                     text_color="#0D2D2D", wraplength=248, justify="left",
                     fg_color="transparent"
                     ).pack(side="left", fill="x", expand=True, padx=(0, 12))

        self._slide_in(steps=10, step=0)

    def _slide_in(self, steps, step):
        t = _ease((step + 1) / steps)
        y = int(self._y_start + (self._y_end - self._y_start) * t)
        try:
            self.win.geometry(f"340x58+{self._x}+{y}")
        except Exception:
            return
        if step < steps - 1:
            self.win.after(12, lambda: self._slide_in(steps, step + 1))
        else:
            self.win.after(self.duration, self._dismiss)

    def _dismiss(self):
        try:
            geom = self.win.geometry()
            y_cur = int(geom.split("+")[2])
        except Exception:
            self._destroy()
            return
        self._slide_out(steps=8, step=0, y_cur=y_cur)

    def _slide_out(self, steps, step, y_cur):
        t = _ease((step + 1) / steps)
        y = int(y_cur + (self._y_start - y_cur) * t)
        try:
            self.win.geometry(f"340x58+{self._x}+{y}")
        except Exception:
            self._destroy()
            return
        if step < steps - 1:
            self.win.after(14, lambda: self._slide_out(steps, step + 1, y_cur))
        else:
            self._destroy()

    def _destroy(self):
        try:
            self.win.destroy()
        except Exception:
            pass
        if self in Toast._stack:
            Toast._stack.remove(self)


def show_toast(root, message, kind="success", duration=2800):
    """Show a slide-up toast. kind: 'success' | 'error' | 'info' | 'warning'"""
    Toast(root, message, kind, duration)


# ── Loading spinner ────────────────────────────────────────────────────────────
class LoadingSpinner(ctk.CTkLabel):
    """Animated braille spinner with a text label."""
    _FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, parent, text="Loading…", color="#0ABFBC", **kwargs):
        super().__init__(parent, text=f"{self._FRAMES[0]}  {text}",
                         text_color=color, font=("DM Sans", 13), **kwargs)
        self._idx = 0
        self._running = False
        self._msg = text

    def start(self):
        self._running = True
        self._spin()

    def stop(self):
        self._running = False

    def _spin(self):
        if not self._running:
            return
        self._idx = (self._idx + 1) % len(self._FRAMES)
        try:
            self.configure(text=f"{self._FRAMES[self._idx]}  {self._msg}")
            self.after(80, self._spin)
        except Exception:
            pass


# ── Skeleton row ───────────────────────────────────────────────────────────────
class SkeletonRow(ctk.CTkFrame):
    """Pulsing placeholder row shown while table data loads."""
    _WIDTHS = [110, 160, 80, 80, 140, 240, 80]

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._phase = 0
        self._running = False
        self._bars = []
        for w in self._WIDTHS:
            bar = ctk.CTkFrame(self, height=14, width=w,
                               corner_radius=7, fg_color="#E2E8F0")
            bar.pack(side="left", padx=4, pady=8)
            bar.pack_propagate(False)
            self._bars.append(bar)

    def start(self):
        self._running = True
        self._pulse()

    def stop(self):
        self._running = False

    def _pulse(self):
        if not self._running:
            return
        self._phase = (self._phase + 1) % 24
        t = abs(self._phase - 12) / 12.0
        color = _lerp_color("#E2E8F0", "#CBD5E1", _ease(t))
        for bar in self._bars:
            try:
                bar.configure(fg_color=color)
            except Exception:
                pass
        try:
            self.after(55, self._pulse)
        except Exception:
            pass


# ── Animated progress bar ──────────────────────────────────────────────────────
def animate_progress(bar, target, duration=420, steps=24):
    """Smoothly animate a CTkProgressBar to a target value (0.0–1.0)."""
    try:
        start = bar.get()
    except Exception:
        start = 0.0

    if abs(target - start) < 0.001:
        bar.set(target)
        return

    interval = max(8, duration // steps)

    def _tick(step):
        t = _ease(step / steps)
        value = start + (target - start) * t
        try:
            bar.set(value)
        except Exception:
            return
        if step < steps:
            bar.after(interval, lambda: _tick(step + 1))
        else:
            try:
                bar.set(target)
            except Exception:
                pass

    _tick(1)


# ── Page fade transition ───────────────────────────────────────────────────────
def fade_transition(root, callback, steps=7, delay=11):
    """
    Fade the window to ~20% alpha, switch frame, then fade back to full.
    Total duration ≈ 150ms — fast enough to feel snappy, slow enough to be visible.
    """
    def _fade_out(step):
        alpha = max(0.20, 1.0 - (_ease(step / steps) * 0.80))
        try:
            root.attributes("-alpha", alpha)
        except Exception:
            pass
        if step < steps:
            root.after(delay, lambda: _fade_out(step + 1))
        else:
            callback()
            root.after(delay, lambda: _fade_in(0))

    def _fade_in(step):
        alpha = min(1.0, 0.20 + _ease(step / steps) * 0.80)
        try:
            root.attributes("-alpha", alpha)
        except Exception:
            pass
        if step < steps:
            root.after(delay, lambda: _fade_in(step + 1))
        else:
            try:
                root.attributes("-alpha", 1.0)
            except Exception:
                pass

    _fade_out(0)
