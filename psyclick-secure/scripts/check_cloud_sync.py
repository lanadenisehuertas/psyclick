"""
check_cloud_sync.py — end-to-end sync check with two simulated devices.

    python scripts/check_cloud_sync.py

Needs the owner connection ("database_url" in %APPDATA%\PsyClick\config.json).
Runs in a throwaway schema that is dropped afterwards, so real data is never
touched. Covers: a new device pulling accounts before first sign-in, sessions
and the self-harm answer crossing devices, role changes, deletions (with the
cloud copy wiped), and two offline devices creating the same account ID.
"""
import json, os, random, secrets, sys, tempfile
APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [APP, APP + "/scripts"]
SCHEMA = "psyclick_test_" + secrets.token_hex(3)
os.environ["PSYCLICK_SYNC_SCHEMA"] = SCHEMA
owner = json.load(open(os.path.join(os.environ["APPDATA"], "PsyClick", "config.json"), encoding="utf-8-sig"))["database_url"]
os.environ["PSYCLICK_SYNC_URL"] = owner          # the scratch schema belongs to the owner role
tmp = tempfile.mkdtemp(prefix="psy2dev_")
os.environ["PSYCLICK_DB_PATH"] = os.path.join(tmp, "boot.db")

import logging; logging.disable(logging.WARNING)
import psycopg2
import database_manager as db
import supabase_sync as sync
from backend_controller import PsyClickController
from demo_simulation import run_session
import setup_cloud_sync as setup

pg = psycopg2.connect(owner); pg.autocommit = True
pg.cursor().execute(setup.DDL.replace("psyclick.", SCHEMA + ".").replace("SCHEMA IF NOT EXISTS psyclick", f"SCHEMA IF NOT EXISTS {SCHEMA}"))

def device(name):
    db.DB_NAME = os.path.join(tmp, name + ".db"); db.init_db()

def sessions(where=""):
    c = db._conn(); r = c.execute("SELECT student_id, clinician_id, phq_item9, flag FROM intake_sessions " + where).fetchall(); c.close(); return r

def accounts():
    c = db._conn(); r = c.execute("SELECT clinician_id, name, role, status FROM clinicians ORDER BY 1").fetchall(); c.close(); return r

ok = True
def check(label, cond):
    global ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + label)

try:
    # Device A: admin + clinician + a session
    device("A")
    _, a_admin, _ = db.register_clinician("Admin A", "SyncTestPass123", "admin")
    _, a_clin, _ = db.register_clinician("Clinician A", "SyncTestPass123", "clinician")
    run_session(PsyClickController(), db, {"client": "X-1", "phq": 12, "gad": 9, "item9": 2}, a_clin, random.Random(1))
    check("A uploads", sync._sync_once(owner) and db.get_unsynced_count() == 0)

    # Device B: new install pulls everything before first sign-in
    device("B")
    check("B starts empty", accounts() == [])
    check("B pull_now (accounts)", sync.pull_now(timeout=20))
    sync._sync_once(owner, pull_only=True)
    check("B has both accounts", [a[0] for a in accounts()] == [a_admin, a_clin])
    check("A's clinician signs in on B", db.verify_clinician(a_clin, "SyncTestPass123")[0])
    check("A's session on B with owner and item 9", sessions() == [("X-1", a_clin, 2, sessions()[0][3])])

    # B changes A's clinician to auditor, adds its own account and session
    c = db._conn(); c.execute("UPDATE clinicians SET role='auditor' WHERE clinician_id=?", (a_clin,)); db.touch_clinician(c, a_clin); c.commit(); c.close()
    _, b_clin, _ = db.register_clinician("Clinician B", "SyncTestPass123", "clinician")
    run_session(PsyClickController(), db, {"client": "Y-1", "phq": 4, "gad": 3}, b_clin, random.Random(2))
    check("B uploads", sync._sync_once(owner) and db.get_unsynced_count() == 0)

    device("A")
    sync._sync_once(owner)
    check("A sees role change from B", ("auditor") in [a[2] for a in accounts() if a[0] == a_clin])
    check("A sees B's account and session", b_clin in [a[0] for a in accounts()] and ("Y-1",) in [(s[0],) for s in sessions()])

    # A deletes client X-1; the deletion reaches B
    c = db._conn(); db.delete_sessions(c, "student_id=?", ("X-1",)); c.commit(); c.close()
    sync._sync_once(owner)
    device("B"); sync._sync_once(owner)
    check("deletion reaches B", not sessions("WHERE student_id='X-1'"))
    cur = pg.cursor(); cur.execute(f"SELECT data::text FROM {SCHEMA}.sessions WHERE deleted_at IS NOT NULL")
    check("deleted session's data is wiped in the cloud", all(r[0] == "{}" for r in cur.fetchall()))

    # Offline on both devices: each makes a new account with the same next ID
    os.environ["PSYCLICK_SYNC_URL"] = ""
    device("A"); _, idA, _ = db.register_clinician("Offline A", "SyncTestPass123", "clinician")
    run_session(PsyClickController(), db, {"client": "Z-A", "phq": 5, "gad": 5}, idA, random.Random(3))
    device("B"); _, idB, _ = db.register_clinician("Offline B", "SyncTestPass123", "clinician")
    check(f"same offline ID on both devices ({idA})", idA == idB)
    os.environ["PSYCLICK_SYNC_URL"] = owner
    device("A"); sync._sync_once(owner)
    device("B"); sync._sync_once(owner)
    moved = [a for a in accounts() if a[1] == "Offline B"][0][0]
    check(f"B's account moved to a free ID ({moved})", moved != idA)
    check("Offline B still signs in with the new ID", db.verify_clinician(moved, "SyncTestPass123")[0])
    device("A"); sync._sync_once(owner)
    names = {a[1]: a[0] for a in accounts()}
    check("A ends with both offline accounts, distinct IDs", names.get("Offline A") == idA and names.get("Offline B") == moved)
    check("A's offline session kept its owner", sessions("WHERE student_id='Z-A'")[0][1] == idA)
    check("second sync is a no-op", sync._sync_once(owner) and db.get_unsynced_count() == 0)
finally:
    pg.cursor().execute(f"DROP SCHEMA {SCHEMA} CASCADE"); pg.close()
    print("scratch schema dropped;", "ALL PASSED" if ok else "SOME FAILED")
    sys.exit(0 if ok else 1)
