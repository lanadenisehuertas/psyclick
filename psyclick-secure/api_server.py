"""
PsyClick API Server
Run:  python api_server.py
"""

import os, sys, json, traceback
from functools import wraps
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, g
from flask_cors import CORS

# Support both dev (script) and production (PyInstaller frozen bundle)
if getattr(sys, 'frozen', False):
    _BASE = os.environ.get('PSYCLICK_SECURE_HOME', os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'PsyClickSecure'))
    if hasattr(sys, '_MEIPASS'):
        sys.path.insert(0, sys._MEIPASS)
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, _BASE)

os.makedirs(_BASE, exist_ok=True)
# ── Startup error log (catches silent crashes in packaged build) ──────────────
_LOG_DIR = os.environ.get('PSYCLICK_SECURE_HOME', os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'PsyClickSecure'))
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_PATH = os.path.join(_LOG_DIR, 'api_startup.log')
import builtins as _bi, traceback as _tb
_orig_excepthook = sys.excepthook
def _log_excepthook(exc_type, exc_val, exc_tb):
    with open(_LOG_PATH, 'a') as _lf:
        _lf.write(f"\n--- CRASH {__import__('datetime').datetime.now()} ---\n")
        _tb.print_exception(exc_type, exc_val, exc_tb, file=_lf)
    _orig_excepthook(exc_type, exc_val, exc_tb)
sys.excepthook = _log_excepthook



from backend_controller import PsyClickController
import supabase_sync
import intrusion_monitor
from database_manager import (
    _conn, _exec, _sql, _ph,
    log_audit, get_audit_logs,
    get_student_session_count, get_sessions_by_student,
    get_latest_sessions,
    get_normative_count, get_normative_stats,
    compute_normative_stats, get_normative_compare,
    register_clinician, get_clinician_by_id, verify_clinician as db_verify_clinician,
    create_security_session, authenticate_security_session, revoke_security_session,
    record_consent, has_active_consent, verify_audit_chain,
    reapply_db_config,
    get_db_mode,
    get_db_status,
    DatabaseUnavailableError,
    get_next_client_id,
    get_next_tester_id,
)
from report_exporter import export_report, export_summary
from security_manager import protect_file, create_encrypted_backup, validate_encrypted_backup

# Ensure DB mode reflects PSYCLICK_DB_URL / config after all imports (packaged API).
reapply_db_config()

app  = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:5173", "http://127.0.0.1:5173", "null"
]}})
STARTUP_ERRORS = []


def _safe_error(exc, message="Something went wrong."):
    return {"success": False, "error": message}


def _db_unavailable_response(exc):
    return jsonify({
        "success": False,
        "error": "The protected local database is unavailable. Contact the administrator.",
    }), 503


# Initialize controller in background so Flask starts immediately
# and /api/ping responds before Supabase/DB connection completes
import threading as _threading
back = None
_back_ready = False

def _init_controller_bg():
    global back, _back_ready
    try:
        back = PsyClickController()
    except Exception as e:
        traceback.print_exc()
        STARTUP_ERRORS.append(f"Controller startup failed: {e}")
    finally:
        _back_ready = True
    # Start background Supabase sync (safe no-op if not configured)
    try:
        supabase_sync.start_sync_service()
    except Exception as e:
        STARTUP_ERRORS.append(f"Sync service startup warning: {e}")

_threading.Thread(target=_init_controller_bg, daemon=True).start()


def require_controller():
    global back
    # Wait up to 30s for background init to complete
    import time as _time
    for _ in range(60):
        if _back_ready:
            break
        _time.sleep(0.5)
    if back is None:
        try:
            back = PsyClickController()
        except Exception as e:
            traceback.print_exc()
            STARTUP_ERRORS.append(f"Controller unavailable: {e}")
            raise RuntimeError(
                "PsyClick assessment engine is unavailable. "
                "Check database settings, device permissions, and packaged API logs."
            ) from e
    return back


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    traceback.print_exc()
    return jsonify(_safe_error(e, "Unexpected server error.")), 500


@app.errorhandler(DatabaseUnavailableError)
def handle_database_unavailable(e):
    return _db_unavailable_response(e)

PUBLIC_ENDPOINTS = {"login", "register", "ping"}


def _bearer_token():
    header = request.headers.get("Authorization", "")
    return header[7:].strip() if header.startswith("Bearer ") else ""


@app.before_request
def enforce_authenticated_api():
    if request.method == "OPTIONS" or request.endpoint in PUBLIC_ENDPOINTS:
        return None
    user = authenticate_security_session(_bearer_token())
    if not user:
        return jsonify({"success": False, "error": "Authentication required or session expired."}), 401
    g.current_user = user


def require_roles(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if not user or user.get("role") not in roles:
                log_audit("security", "Authorization denied", request.path,
                          actor_id=user.get("id") if user else None, outcome="denied")
                return jsonify({"success": False, "error": "Insufficient permission."}), 403
            return fn(*args, **kwargs)
        return wrapped
    return decorator


def _scoped_clinician_id(requested=None):
    user = g.current_user
    if user["role"] == "admin" and requested:
        try:
            return int(requested)
        except (TypeError, ValueError):
            return user["id"]
    return user["id"]

# ─── Auth ──────────────────────────────────────────────────────────────────────
@app.route("/api/login", methods=["POST"])
def login():
    source_ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
    cooldown = intrusion_monitor.is_source_throttled(source_ip)
    if cooldown:
        log_audit("security", "Login blocked by intrusion monitor", f"source={source_ip}", outcome="denied")
        return jsonify({
            "success": False,
            "error": f"Too many failed attempts from this source. Try again in {int(cooldown)}s.",
        }), 429

    d   = request.get_json() or {}
    uid = str(d.get("id", "")).strip()
    pwd = str(d.get("password", "")).strip()
    if not uid or not pwd:
        return jsonify({"success": False, "error": "Please enter ID and password."})
    if not uid.isdigit():
        return jsonify({"success": False, "error": "Clinician ID must be a number."})
    try:
        clinician_id = int(uid)
        success, error_msg = db_verify_clinician(clinician_id, pwd)
        if success:
            intrusion_monitor.record_success(source_ip, clinician_id)
            clinician_data = get_clinician_by_id(clinician_id)
            if clinician_data:
                token, expires_at = create_security_session(clinician_id, clinician_data["role"])
                log_audit("clinician", "Logged in", clinician_data["name"], actor_id=clinician_id)
                return jsonify({
                    "success": True, "name": clinician_data["name"], "id": clinician_id,
                    "role": clinician_data["role"], "token": token, "expires_at": expires_at,
                })
            return jsonify({"success": False, "error": "Clinician not found."})
        log_audit("security", "Failed login", f"clinician_id={uid}", outcome="denied")
        intrusion_monitor.record_failure(source_ip, clinician_id, log_audit_fn=log_audit)
        return jsonify({"success": False, "error": error_msg or "Invalid clinician ID or password."}), 401
    except DatabaseUnavailableError as e:
        return _db_unavailable_response(e)
    except Exception:
        intrusion_monitor.record_failure(source_ip, uid, log_audit_fn=log_audit)
        return jsonify({"success": False, "error": "Authentication service unavailable."}), 503

@app.route("/api/register", methods=["POST"])
def register():
    d = request.get_json() or {}
    name = str(d.get("name", "")).strip()
    pwd = str(d.get("password", "")).strip()
    if not name or not pwd:
        return jsonify({"success": False, "error": "Please enter name and password."})
    # First account bootstraps administration. Later provisioning is admin-only.
    conn = _conn(); count = _exec(conn, "SELECT COUNT(*) FROM clinicians").fetchone()[0]; conn.close()
    requested_role = "admin" if count == 0 else "clinician"
    actor = None
    if count > 0:
        actor = authenticate_security_session(_bearer_token())
        if not actor or actor.get("role") != "admin":
            return jsonify({"success": False, "error": "Administrator authorization is required."}), 403
        requested_role = str(d.get("role", "clinician")).lower()
        if requested_role not in {"clinician", "auditor", "admin"}:
            return jsonify({"success": False, "error": "Invalid role."}), 400
    success, clinician_id, error_msg = register_clinician(name, pwd, requested_role)
    if success:
        log_audit("admin" if actor else "system", "Registered account", name,
                  actor_id=actor.get("id") if actor else clinician_id)
        return jsonify({"success": True, "clinician_id": clinician_id, "name": name, "role": requested_role})
    return jsonify({"success": False, "error": error_msg or "Registration failed."})

@app.route("/api/verify-clinician", methods=["POST"])
def verify_clinician_endpoint():
    d = request.get_json() or {}
    uid = str(d.get("id", "")).strip()
    pwd = str(d.get("password", "")).strip()
    if not uid or not pwd:
        return jsonify({"success": False, "error": "Please provide ID and password."})
    try:
        clinician_id = int(uid)
        success, error_msg = db_verify_clinician(clinician_id, pwd)
        if success and (g.current_user["role"] == "admin" or clinician_id == g.current_user["id"]):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Verification failed."}), 401
    except Exception:
        return jsonify({"success": False, "error": "Verification failed."}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    revoke_security_session(_bearer_token())
    log_audit("clinician", "Logged out", actor_id=g.current_user["id"])
    return jsonify({"success": True})

# ─── Dashboard stats ───────────────────────────────────────────────────────────
@app.route("/api/stats")
def stats():
    try:
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        ph = _ph()
        conn = _conn()
        c = conn.cursor()
        cid = _scoped_clinician_id(request.args.get("clinician_id"))
        if cid:
            cid_filter = f" WHERE clinician_id={ph}"
            cid_and    = f" AND clinician_id={ph}"
            c.execute(f"SELECT COUNT(*) FROM intake_sessions{cid_filter}", (cid,));               total  = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM intake_sessions WHERE timestamp>={ph}{cid_and}", (week_ago, cid)); week = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM intake_sessions WHERE flag={ph}{cid_and}", ('GREEN', cid));        normal = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM intake_sessions WHERE flag IN ({ph},{ph}){cid_and}", ('AMBER','RED',cid)); review = c.fetchone()[0]
        else:
            c.execute("SELECT COUNT(*) FROM intake_sessions");                                         total  = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM intake_sessions WHERE timestamp >= {ph}", (week_ago,));   week   = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM intake_sessions WHERE flag={ph}", ('GREEN',));            normal = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM intake_sessions WHERE flag IN ({ph},{ph})", ('AMBER','RED',)); review = c.fetchone()[0]
        conn.close()
        return jsonify({"total": total, "week": week, "normal": normal, "review": review})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/sessions/recent")
def recent_sessions():
    try:
        conn = _conn(); c = conn.cursor()
        ph = _ph()
        cid = _scoped_clinician_id(request.args.get("clinician_id"))
        if cid:
            c.execute(f"""SELECT session_id,student_id,timestamp,flag,
                                phq_score,gad_score,psi,pai,fuzzy_label
                         FROM intake_sessions WHERE clinician_id={ph}
                         ORDER BY timestamp DESC LIMIT 12""", (cid,))
        else:
            c.execute("""SELECT session_id,student_id,timestamp,flag,
                                phq_score,gad_score,psi,pai,fuzzy_label
                         FROM intake_sessions ORDER BY timestamp DESC LIMIT 12""")
        rows = c.fetchall(); conn.close()
        return jsonify([{
            "session_id": r[0], "patient_id": r[1], "timestamp": str(r[2])[:16],
            "flag": r[3], "phq": r[4] or 0, "gad": r[5] or 0,
            "psi": r[6] or 0, "pai": r[7] or 0, "label": r[8] or "",
        } for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Patients ──────────────────────────────────────────────────────────────────
@app.route("/api/patients")
def patients():
    try:
        conn = _conn(); c = conn.cursor()
        ph = _ph()
        cid = _scoped_clinician_id(request.args.get("clinician_id"))
        if cid:
            c.execute(f"""SELECT student_id,COUNT(*) as n,MAX(timestamp),
                                MAX(CASE flag WHEN 'RED' THEN 3 WHEN 'AMBER' THEN 2
                                             WHEN 'GREEN' THEN 1 ELSE 0 END)
                         FROM intake_sessions WHERE clinician_id={ph}
                         GROUP BY student_id ORDER BY MAX(timestamp) DESC""", (cid,))
        else:
            c.execute("""SELECT student_id,COUNT(*) as n,MAX(timestamp),
                                MAX(CASE flag WHEN 'RED' THEN 3 WHEN 'AMBER' THEN 2
                                             WHEN 'GREEN' THEN 1 ELSE 0 END)
                         FROM intake_sessions GROUP BY student_id ORDER BY MAX(timestamp) DESC""")
        rows = c.fetchall(); conn.close()
        flag_map = {3:"RED",2:"AMBER",1:"GREEN",0:None}
        return jsonify([{
            "id": r[0], "sessions": r[1], "last_seen": str(r[2])[:16],
            "flag": flag_map.get(r[3]),
        } for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/patients/<patient_id>/sessions")
def patient_sessions(patient_id):
    try:
        ph = _ph()
        conn = _conn(); c = conn.cursor()
        clinician_id = _scoped_clinician_id()
        c.execute(f"""SELECT session_id,timestamp,phq_score,gad_score,flag,
                              fuzzy_label,t2_score,psi,pai
                      FROM intake_sessions WHERE student_id={ph} AND clinician_id={ph}
                      ORDER BY timestamp DESC""", (patient_id, clinician_id))
        rows = c.fetchall(); conn.close()
        return jsonify([{
            "session_id": r[0], "timestamp": str(r[1])[:16],
            "phq": r[2] or 0, "gad": r[3] or 0, "flag": r[4],
            "label": r[5] or "", "t2": r[6] or 0,
            "psi": r[7] or 0, "pai": r[8] or 0,
        } for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/session/<int:session_id>")
def session_detail(session_id):
    try:
        ph = _ph()
        conn = _conn(); c = conn.cursor()
        clinician_id = _scoped_clinician_id()
        c.execute(f"""SELECT student_id,timestamp,phq_score,gad_score,
                              t2_score,t2_threshold,psi,pai,
                              fuzzy_label,fuzzy_confidence,flag,rationale,
                              domain_t2_json,question_snapshots_json,flight_times_json
                      FROM intake_sessions WHERE session_id={ph} AND clinician_id={ph}""",
                  (session_id, clinician_id))
        row = c.fetchone(); conn.close()
        if not row: return jsonify({"error":"Session not found"}), 404
        sid,ts,phq,gad,t2,thr,psi,pai,label,conf,flag,rat,dom_j,snap_j,flight_j = row
        snaps = json.loads(snap_j or "[]")
        # Compute level_t2 from stored snapshots (not persisted separately)
        level_groups = {}
        for snap in snaps:
            lv = snap.get("level", "A")
            level_groups.setdefault(lv, []).append(snap.get("t2_score") or 0)
        level_t2 = {lv: sum(vals)/len(vals) for lv, vals in level_groups.items() if vals}
        
        # Load exact flight times array if available; otherwise fallback to approximations
        flights_array = json.loads(flight_j or "[]") if flight_j else []
        if not flights_array:
            flights_array = [snap.get("flight_time") or 0 for snap in snaps if snap.get("flight_time")]
        return jsonify({
            "student_id": sid, "timestamp": str(ts),
            "phq": {"score": phq or 0}, "gad": {"score": gad or 0},
            "analysis": {"flag": flag, "t2_score": t2, "t2_threshold": thr,
                         "psi": psi, "pai": pai, "label": label,
                         "confidence": conf, "rationale": rat},
            "visuals": {
                "question_snapshots": snaps,
                "domain_t2": {int(k):v for k,v in json.loads(dom_j or "{}").items()},
                "level_t2": level_t2,
                "flight_times": flights_array,
                "pause_coords": [],
            },
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Intake ────────────────────────────────────────────────────────────────────
@app.route("/api/intake/start", methods=["POST"])
def intake_start():
    d   = request.get_json() or {}
    pid = d.get("patient_id", "PT-UNKNOWN").strip() or "PT-UNKNOWN"
    cid = _scoped_clinician_id(d.get("clinician_id"))
    consent = d.get("consent") is True
    consent_version = str(d.get("consent_version", "1.0")).strip() or "1.0"
    if not consent:
        log_audit("clinician", "Consent gate blocked", pid, actor_id=cid, outcome="denied")
        return jsonify({"success": False, "error": "Recorded informed consent is required."}), 400
    record_consent(pid, cid, "granted", consent_version)
    existing = get_student_session_count(pid, cid)
    controller = require_controller()
    controller.set_student_id(pid)
    controller.session_data["clinician_id"] = cid
    controller.session_data["consent_verified"] = True
    log_audit("clinician", "Consent granted and session started", pid, actor_id=cid)
    return jsonify({"success": True, "existing_sessions": existing, "patient_id": pid})


@app.route("/api/next-client-id")
def next_client_id():
    try:
        cid = _scoped_clinician_id(request.args.get("clinician_id"))
        nid = get_next_client_id(cid)
        if nid:
            return jsonify({"success": True, "id": nid})
        return jsonify({"success": False, "error": "All client IDs C-001 to C-100 are taken."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/next-tester-id")
def next_tester_id():
    try:
        nid = get_next_tester_id()
        if nid:
            return jsonify({"success": True, "id": nid})
        return jsonify({"success": False, "error": "All tester IDs T-001 to T-100 are taken."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ─── Keyboard calibration ──────────────────────────────────────────────────────
@app.route("/api/calibration/keyboard/start", methods=["POST"])
def kcal_start():
    controller = require_controller()
    if not controller.session_data.get("consent_verified"):
        return jsonify({"success": False, "error": "Consent verification is required before capture."}), 403
    controller.start_key_capture(calibration_mode=True)
    log_audit("patient", "Entered Keyboard Calibration", controller.session_data["student_id"])
    return jsonify({"success": True})

@app.route("/api/calibration/keyboard/save", methods=["POST"])
def kcal_save():
    require_controller().save_kbase()
    return jsonify({"success": True})

# ─── Mouse calibration ─────────────────────────────────────────────────────────
@app.route("/api/calibration/mouse/start", methods=["POST"])
def mcal_start():
    controller = require_controller()
    if not controller.session_data.get("consent_verified"):
        return jsonify({"success": False, "error": "Consent verification is required before capture."}), 403
    controller.start_mouse_capture()
    log_audit("patient", "Entered Mouse Calibration", controller.session_data["student_id"])
    return jsonify({"success": True})

@app.route("/api/calibration/mouse/save", methods=["POST"])
def mcal_save():
    require_controller().save_mbase()
    return jsonify({"success": True})

# ─── PHQ-9 ─────────────────────────────────────────────────────────────────────
@app.route("/api/assessment/phq/start", methods=["POST"])
def phq_start():
    controller = require_controller()
    if not controller.session_data.get("consent_verified"):
        return jsonify({"success": False, "error": "Consent verification is required before capture."}), 403
    controller.start_mouse_capture()
    log_audit("patient", "Entered PHQ-9", controller.session_data["student_id"])
    return jsonify({"success": True})

@app.route("/api/assessment/phq/save", methods=["POST"])
def phq_save():
    require_controller().save_phq((request.get_json() or {}).get("score", 0))
    return jsonify({"success": True})

# ─── GAD-7 ─────────────────────────────────────────────────────────────────────
@app.route("/api/assessment/gad/start", methods=["POST"])
def gad_start():
    controller = require_controller()
    if not controller.session_data.get("consent_verified"):
        return jsonify({"success": False, "error": "Consent verification is required before capture."}), 403
    controller.start_mouse_capture()
    log_audit("patient", "Entered GAD-7", controller.session_data["student_id"])
    return jsonify({"success": True})

@app.route("/api/assessment/gad/save", methods=["POST"])
def gad_save():
    require_controller().save_gad((request.get_json() or {}).get("score", 0))
    return jsonify({"success": True})

# ─── Emotional Task ────────────────────────────────────────────────────────────
@app.route("/api/assessment/emotional/start", methods=["POST"])
def emotional_start():
    controller = require_controller()
    if not controller.session_data.get("consent_verified"):
        return jsonify({"success": False, "error": "Consent verification is required before capture."}), 403
    controller.start_mouse_capture()
    controller.start_key_capture()
    log_audit("patient", "Entered Clinical Assessment", controller.session_data["student_id"])
    return jsonify({"success": True})

@app.route("/api/assessment/question/set", methods=["POST"])
def question_set():
    d = request.get_json() or {}
    q = d.get("question", {})
    require_controller().set_current_question(q)
    log_audit("patient", f"Entered {q.get('group_name','')}", q.get("level_name",""))
    return jsonify({"success": True})

@app.route("/api/assessment/word-boxes", methods=["POST"])
def word_boxes():
    """Receive word bounding boxes from the DOM (JS getBoundingClientRect)."""
    d    = request.get_json() or {}
    boxes = d.get("boxes", [])
    try:
        require_controller().register_word_boxes(boxes)
    except Exception:
        pass
    return jsonify({"success": True})

@app.route("/api/assessment/question/snapshot", methods=["POST"])
def question_snapshot():
    d = request.get_json() or {}
    log_audit("patient", "Clicked Next", f"Q{d.get('qi',0)+1} of {d.get('total',0)}")
    require_controller().save_question_snapshot(d.get("question", {}), d.get("response", ""))
    return jsonify({"success": True})

@app.route("/api/assessment/finish", methods=["POST"])
def assessment_finish():
    try:
        controller = require_controller()
        result = controller.process_final_task()
        if result:
            log_audit("patient", "Finished Session", controller.session_data["student_id"])
            return jsonify({"success": True, "report": result})
        return jsonify({"success": False, "error": "No biometric data captured — ensure calibration completed."})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/assessment/audit/choice", methods=["POST"])
def audit_choice():
    d = request.get_json() or {}
    log_audit("patient", f"Made choice: {d.get('label','')}", d.get("context",""))
    return jsonify({"success": True})

@app.route("/api/assessment/idle", methods=["POST"])
def audit_idle():
    d = request.get_json() or {}
    log_audit("patient", "Idle (10+ seconds)", d.get("context",""))
    return jsonify({"success": True})

# ─── Audit log ─────────────────────────────────────────────────────────────────
@app.route("/api/audit")
@require_roles("admin", "auditor")
def audit():
    actor = request.args.get("actor") or None   # None → all actors; "clinician"/"patient" → filtered
    rows  = get_audit_logs(actor=actor)
    if actor:
        # 3-column result: (timestamp, action, detail)
        return jsonify([{"timestamp": r[0], "action": r[1], "detail": r[2]} for r in rows])
    else:
        # 4-column result: (timestamp, actor, action, detail)
        return jsonify([{"timestamp": r[0], "actor": r[1], "action": r[2], "detail": r[3]} for r in rows])

@app.route("/api/audit/log", methods=["POST"])
def audit_log():
    d = request.get_json() or {}
    action = str(d.get("action", ""))[:120]
    detail = str(d.get("detail", ""))[:500]
    log_audit(g.current_user["role"], action, detail, actor_id=g.current_user["id"])
    return jsonify({"success": True})


@app.route("/api/audit/verify")
@require_roles("admin", "auditor")
def audit_verify():
    valid, checked, first_invalid = verify_audit_chain()
    return jsonify({"valid": valid, "checked": checked, "first_invalid_log_id": first_invalid})

@app.route("/api/security/intrusion-alerts")
@require_roles("admin", "auditor")
def intrusion_alerts():
    """Recent brute-force / credential-stuffing alerts raised by the in-process
    intrusion monitor (Security Monitoring requirement, CS0029 spec Section III)."""
    return jsonify({"alerts": intrusion_monitor.get_recent_alerts()})

# ─── Export ────────────────────────────────────────────────────────────────────
@app.route("/api/export/report", methods=["POST"])
def do_export_report():
    d = request.get_json() or {}
    try:
        fp = export_report(d.get("report", {}))
        protected_file, digest = protect_file(fp)
        log_audit(g.current_user["role"], "Exported encrypted clinical report",
                  os.path.basename(protected_file), actor_id=g.current_user["id"])
        return jsonify({"success": True, "file": protected_file, "sha256": digest, "encrypted": True})
    except Exception:
        return jsonify({"success": False, "error": "Secure report export failed."}), 500

@app.route("/api/export/summary", methods=["POST"])
def do_export_summary():
    try:
        conn = _conn(); c = conn.cursor()
        c.execute("""SELECT student_id,timestamp,flag,phq_score,gad_score,
                            psi,pai,fuzzy_label FROM intake_sessions ORDER BY timestamp DESC""")
        rows = c.fetchall(); conn.close()
        log_audit(g.current_user["role"], "Exported generated reports", actor_id=g.current_user["id"])
        if not rows:
            return jsonify({"success": False, "error": "No sessions to export."})
        fp = export_summary(rows)
        protected_file, digest = protect_file(fp)
        return jsonify({"success": True, "file": protected_file, "sha256": digest, "encrypted": True})
    except Exception:
        return jsonify({"success": False, "error": "Secure summary export failed."}), 500

# ─── Delete ────────────────────────────────────────────────────────────────────
@app.route("/api/clients/<client_id>", methods=["DELETE"])
@require_roles("admin", "clinician")
def delete_client(client_id):
    try:
        ph = _ph()
        conn = _conn(); c = conn.cursor()
        clinician_id = _scoped_clinician_id()
        c.execute(f"DELETE FROM intake_sessions WHERE student_id={ph} AND clinician_id={ph}",
                  (client_id, clinician_id))
        deleted = c.rowcount
        conn.commit(); conn.close()
        log_audit(g.current_user["role"], f"Deleted client record: {client_id}",
                  f"{deleted} session(s) removed", actor_id=g.current_user["id"])
        return jsonify({"success": True, "deleted": deleted})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ─── Normative baseline ────────────────────────────────────────────────────────
@app.route("/api/normative/login", methods=["POST"])
@require_roles("admin")
def normative_login():
    d   = request.get_json() or {}
    tid = str(d.get("tester_id", "")).strip() or "NORMER"
    controller = require_controller()
    controller.normative_mode = True
    controller.set_student_id(tid)
    log_audit("admin", "Enabled normative mode", tid, actor_id=g.current_user["id"])
    return jsonify({"success": True, "tester_id": tid})

@app.route("/api/normative/mode", methods=["POST"])
def set_normative_mode():
    d = request.get_json() or {}
    controller = require_controller()
    controller.normative_mode = bool(d.get("active", False))
    return jsonify({"success": True, "active": controller.normative_mode})

@app.route("/api/normative/stats")
def normative_stats():
    return jsonify(get_normative_stats())

@app.route("/api/normative/compute", methods=["POST"])
@require_roles("admin")
def normative_compute():
    try:
        ok = compute_normative_stats()
        if ok:
            count = get_normative_count()
            log_audit("admin", "Computed normative baseline", f"{count} sessions",
                      actor_id=g.current_user["id"])
            return jsonify({"success": True, "count": count})
        return jsonify({"success": False, "error": "No normative sessions found."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/normative/compare/<int:session_id>")
def normative_compare(session_id):
    result = get_normative_compare(session_id)
    if result is None:
        return jsonify({"available": False, "reason": "Normative baseline not yet computed or session not found."})
    return jsonify({"available": True, "metrics": result})

# ─── Cloud sync ───────────────────────────────────────────────────────────────
@app.route("/api/sync/status")
def sync_status():
    """Return current offline→cloud sync status for the UI indicator."""
    try:
        return jsonify(supabase_sync.get_sync_status())
    except Exception as e:
        return jsonify({"enabled": False, "error": str(e)}), 500


@app.route("/api/sync/now", methods=["POST"])
@require_roles("admin")
def sync_now():
    """Trigger an immediate sync attempt (clinician-initiated)."""
    try:
        result = supabase_sync.trigger_sync_now()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sync/pull", methods=["POST"])
@require_roles("admin")
def sync_pull():
    """Pull existing sessions from Supabase into local SQLite (one-time migration)."""
    try:
        pulled, error = supabase_sync.pull_from_supabase()
        if error:
            return jsonify({"success": False, "error": error, "pulled": 0})
        return jsonify({"success": True, "pulled": pulled})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "pulled": 0}), 500


@app.route("/api/admin/backup", methods=["POST"])
@require_roles("admin")
def admin_backup():
    try:
        result = create_encrypted_backup(g.current_user["id"])
        log_audit("admin", "Created encrypted backup", os.path.basename(result["file"]),
                  actor_id=g.current_user["id"])
        return jsonify({"success": True, **result})
    except Exception:
        return jsonify({"success": False, "error": "Encrypted backup failed."}), 500


@app.route("/api/admin/backup/verify", methods=["POST"])
@require_roles("admin", "auditor")
def admin_backup_verify():
    d = request.get_json() or {}
    try:
        result = validate_encrypted_backup(str(d.get("file", "")), d.get("sha256"))
        log_audit(g.current_user["role"], "Verified encrypted backup",
                  os.path.basename(str(d.get("file", ""))), actor_id=g.current_user["id"],
                  outcome="success" if result.get("valid") else "failed")
        return jsonify({"success": bool(result.get("valid")), **result})
    except Exception:
        return jsonify({"success": False, "error": "Backup verification failed."}), 400


@app.route("/api/admin/users")
@require_roles("admin")
def admin_users():
    conn = _conn()
    rows = _exec(conn, """
        SELECT clinician_id, name, role, status, created_at, last_login_at
        FROM clinicians ORDER BY name
    """).fetchall()
    conn.close()
    return jsonify([{
        "id": r[0], "name": r[1], "role": r[2] or "clinician",
        "status": r[3] or "active", "created_at": r[4], "last_login_at": r[5],
    } for r in rows])


@app.route("/api/admin/users/<int:clinician_id>", methods=["PATCH"])
@require_roles("admin")
def admin_update_user(clinician_id):
    d = request.get_json() or {}
    role = str(d.get("role", "")).lower()
    status = str(d.get("status", "")).lower()
    if role not in {"admin", "clinician", "auditor"} or status not in {"active", "disabled"}:
        return jsonify({"success": False, "error": "Invalid role or status."}), 400
    if clinician_id == g.current_user["id"] and (role != "admin" or status != "active"):
        return jsonify({"success": False, "error": "You cannot remove your own active administrator access."}), 400
    conn = _conn()
    existing = _exec(conn, "SELECT name FROM clinicians WHERE clinician_id=?", (clinician_id,)).fetchone()
    if not existing:
        conn.close(); return jsonify({"success": False, "error": "User not found."}), 404
    _exec(conn, "UPDATE clinicians SET role=?, status=? WHERE clinician_id=?",
          (role, status, clinician_id))
    if status == "disabled":
        _exec(conn, "UPDATE security_sessions SET revoked_at=? WHERE clinician_id=? AND revoked_at IS NULL",
              (datetime.now().isoformat(timespec="seconds"), clinician_id))
    conn.commit(); conn.close()
    log_audit("admin", "Updated user access", f"{clinician_id}: {role}/{status}",
              actor_id=g.current_user["id"])
    return jsonify({"success": True})


@app.route("/api/admin/security-status")
@require_roles("admin", "auditor")
def admin_security_status():
    valid, checked, first_invalid = verify_audit_chain()
    conn = _conn()
    latest = _exec(conn, """
        SELECT created_at, file_path, sha256, verified_at, status
        FROM backup_records ORDER BY backup_id DESC LIMIT 1
    """).fetchone()
    active_users = _exec(conn, "SELECT COUNT(*) FROM clinicians WHERE status='active'").fetchone()[0]
    active_sessions = _exec(conn, """
        SELECT COUNT(*) FROM security_sessions
        WHERE revoked_at IS NULL AND expires_at>?
    """, (datetime.now().isoformat(timespec="seconds"),)).fetchone()[0]
    conn.close()
    return jsonify({
        "audit": {"valid": valid, "checked": checked, "first_invalid_log_id": first_invalid},
        "latest_backup": None if not latest else {
            "created_at": latest[0], "file": latest[1], "sha256": latest[2],
            "verified_at": latest[3], "status": latest[4],
        },
        "active_users": active_users, "active_sessions": active_sessions,
    })


# ─── Health check ──────────────────────────────────────────────────────────────
@app.route("/api/ping")
def ping():
    return jsonify({"ok": True, "ready": _back_ready, "startup_errors": STARTUP_ERRORS, "db": get_db_status()})


@app.route("/api/db-health")
def db_health():
    """
    Diagnostics: which DB backend is active and whether a connection works.
    Does not expose passwords. If backend is sqlite, cloud (Supabase) is not in use.
    """
    try:
        mode, info = get_db_mode()
        conn = _conn()
        c = conn.cursor()
        c.execute("SELECT 1")
        c.fetchone()
        conn.close()
        payload = {"ok": True, "backend": mode, "info": info, "status": get_db_status()}
        if mode == "sqlite":
            payload["warning"] = (
                "Data is stored only on this PC. For Supabase, set database_url in "
                "%APPDATA%\\PsyClick\\config.json or rebuild the installer with config.json bundled."
            )
        return jsonify(payload)
    except Exception as e:
        mode, info = get_db_mode()
        return jsonify({"ok": False, "backend": mode, "info": info, "error": str(e)}), 500

if __name__ == "__main__":
    print("PsyClick Secure API Server starting on http://127.0.0.1:5101")
    app.run(host="127.0.0.1", port=5101, debug=False, threaded=True)
