"""Security services for encrypted exports and verified SQLite backups."""

import hashlib
import os
import sqlite3
import tempfile
import ctypes
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

import database_manager as db


APP_DIR = Path(os.environ.get("PSYCLICK_SECURE_HOME", Path.home() / "PsyClickSecure"))
BACKUP_DIR = APP_DIR / "backups"


def _ensure_dirs():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data):
    buffer = ctypes.create_string_buffer(data, len(data))
    return DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def _dpapi_protect(data):
    if os.name != "nt":
        raise RuntimeError("PsyClick protected exports require Windows DPAPI.")
    in_blob, in_buffer = _blob(data)
    out_blob = DATA_BLOB()
    description = "PsyClick protected clinical data"
    result = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob), description, None, None, None, 0x01,
        ctypes.byref(out_blob),
    )
    if not result:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def _dpapi_unprotect(data):
    if os.name != "nt":
        raise RuntimeError("PsyClick protected exports require Windows DPAPI.")
    in_blob, in_buffer = _blob(data)
    out_blob = DATA_BLOB()
    result = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, None, None, None, 0x01,
        ctypes.byref(out_blob),
    )
    if not result:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def protect_file(path, remove_plaintext=True):
    """Encrypt a report/export and return (encrypted_path, sha256)."""
    source = Path(path).resolve()
    if not source.is_file():
        raise FileNotFoundError("Export file was not created.")
    encrypted_path = source.with_suffix(source.suffix + ".psyclick")
    ciphertext = _dpapi_protect(source.read_bytes())
    encrypted_path.write_bytes(ciphertext)
    digest = hashlib.sha256(ciphertext).hexdigest()
    if remove_plaintext:
        source.unlink(missing_ok=True)
    return str(encrypted_path), digest


def create_encrypted_backup(created_by):
    """Create a consistent SQLite copy, encrypt it, and record its digest."""
    _ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_path = BACKUP_DIR / f"PsyClick_Backup_{timestamp}.db.psyclick"

    with tempfile.TemporaryDirectory(prefix="psyclick_backup_") as tmp:
        plain_copy = Path(tmp) / "psyclick_backup.db"
        source_conn = sqlite3.connect(db.DB_NAME)
        backup_conn = sqlite3.connect(plain_copy)
        try:
            source_conn.backup(backup_conn)
        finally:
            backup_conn.close()
            source_conn.close()
        ciphertext = _dpapi_protect(plain_copy.read_bytes())

    final_path.write_bytes(ciphertext)
    digest = hashlib.sha256(ciphertext).hexdigest()
    created_at = datetime.now().isoformat(timespec="seconds")
    conn = db._conn()
    db._exec(conn, """
        INSERT INTO backup_records
        (created_at, created_by, file_path, sha256, encrypted, status)
        VALUES (?,?,?,?,1,'created')
    """, (created_at, created_by, str(final_path), digest))
    conn.commit(); conn.close()
    return {"file": str(final_path), "sha256": digest, "created_at": created_at}


def validate_encrypted_backup(path, expected_sha256=None):
    """Decrypt only in a temporary directory and run SQLite integrity_check."""
    backup_path = Path(path).resolve()
    if BACKUP_DIR.resolve() not in backup_path.parents:
        raise ValueError("Backup path is outside the protected backup directory.")
    ciphertext = backup_path.read_bytes()
    digest = hashlib.sha256(ciphertext).hexdigest()
    if expected_sha256 and digest != expected_sha256:
        return {"valid": False, "sha256": digest, "reason": "SHA-256 mismatch"}
    try:
        plaintext = _dpapi_unprotect(ciphertext)
    except OSError:
        return {"valid": False, "sha256": digest, "reason": "Decryption failed"}

    with tempfile.TemporaryDirectory(prefix="psyclick_restore_test_") as tmp:
        db_copy = Path(tmp) / "validation.db"
        db_copy.write_bytes(plaintext)
        conn = sqlite3.connect(db_copy)
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
            table_count = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
        finally:
            conn.close()
    valid = result == "ok"
    if valid:
        conn = db._conn()
        db._exec(conn, """
            UPDATE backup_records SET verified_at=?, status='verified'
            WHERE file_path=?
        """, (datetime.now().isoformat(timespec="seconds"), str(backup_path)))
        conn.commit(); conn.close()
    return {
        "valid": valid,
        "sha256": digest,
        "integrity_check": result,
        "table_count": table_count,
    }
