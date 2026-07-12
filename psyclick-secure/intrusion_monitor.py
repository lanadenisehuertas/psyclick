"""
Lightweight in-process intrusion detection / brute-force monitor for PsyClick Secure.

This implements the "Security Monitoring: Intrusion detection concept" requirement
from the CS0029 Final Project Specification. It is a signature-free, threshold-based
anomaly monitor (not a full network IDS) that watches authentication traffic for
brute-force / credential-stuffing patterns and produces auditable security alerts.

Design:
- Sliding-window failure counter keyed by source (client IP address).
- A second counter keyed by target account catches slow/low-and-slow attacks
  against a single clinician ID from rotating source addresses.
- When a source or target crosses FAILURE_THRESHOLD failures inside WINDOW_SECONDS,
  the source is throttled (soft block) for COOLDOWN_SECONDS and a "security" audit
  event is written via database_manager.log_audit so the alert is durable,
  hash-chained, and reviewable by an auditor/admin — not just an in-memory event.

This module holds no PHI/PII and only tracks IP strings, clinician IDs, and
timestamps for the lifetime of the process.
"""

import threading
import time
from collections import deque, defaultdict

FAILURE_THRESHOLD = 8          # failed attempts ...
WINDOW_SECONDS = 300            # ... within this rolling window ...
COOLDOWN_SECONDS = 120           # ... triggers a throttle for this long
MAX_TRACKED_SOURCES = 5000      # bound memory use under sustained attack

_lock = threading.Lock()
_failures_by_source = defaultdict(deque)   # ip -> deque[timestamp]
_failures_by_target = defaultdict(deque)   # clinician_id/str -> deque[timestamp]
_throttled_until = {}                       # ip -> unix ts
_alerts = deque(maxlen=200)                 # recent alerts, for the admin dashboard


def _prune(dq, now):
    while dq and now - dq[0] > WINDOW_SECONDS:
        dq.popleft()


def is_source_throttled(source_ip):
    """Return remaining cooldown seconds (0 if not throttled)."""
    now = time.time()
    with _lock:
        until = _throttled_until.get(source_ip)
        if until and until > now:
            return round(until - now, 1)
        if until:
            _throttled_until.pop(source_ip, None)
        return 0


def record_success(source_ip, target_id):
    """Clear failure history for a source (and target account) on successful auth."""
    with _lock:
        _failures_by_source.pop(source_ip, None)
        if target_id is not None:
            _failures_by_target.pop(str(target_id), None)


def record_failure(source_ip, target_id, log_audit_fn=None):
    """
    Record a failed authentication attempt. Returns a dict describing whether
    this event triggered a new intrusion alert (for callers that want to react,
    e.g. return HTTP 429 or surface a banner).
    """
    now = time.time()
    triggered = False
    reason = None
    with _lock:
        if len(_failures_by_source) > MAX_TRACKED_SOURCES:
            _failures_by_source.clear()  # defensive reset under memory pressure

        src_dq = _failures_by_source[source_ip]
        src_dq.append(now)
        _prune(src_dq, now)

        tgt_key = str(target_id) if target_id is not None else None
        if tgt_key:
            tgt_dq = _failures_by_target[tgt_key]
            tgt_dq.append(now)
            _prune(tgt_dq, now)
        else:
            tgt_dq = deque()

        if len(src_dq) >= FAILURE_THRESHOLD:
            triggered = True
            reason = f"{len(src_dq)} failed logins from {source_ip} in {WINDOW_SECONDS}s"
            _throttled_until[source_ip] = now + COOLDOWN_SECONDS
        elif tgt_key and len(tgt_dq) >= FAILURE_THRESHOLD:
            triggered = True
            reason = f"{len(tgt_dq)} failed logins against account {tgt_key} in {WINDOW_SECONDS}s (rotating sources)"

        if triggered:
            _alerts.append({"ts": now, "source": source_ip, "target": tgt_key, "reason": reason})

    if triggered and log_audit_fn:
        try:
            log_audit_fn("security", "Intrusion alert: brute-force pattern detected", reason,
                         actor_id=None, outcome="denied")
        except Exception:
            pass

    return {"triggered": triggered, "reason": reason}


def get_recent_alerts():
    with _lock:
        return list(_alerts)


def reset():
    """Test helper: clear all in-memory state."""
    with _lock:
        _failures_by_source.clear()
        _failures_by_target.clear()
        _throttled_until.clear()
        _alerts.clear()
