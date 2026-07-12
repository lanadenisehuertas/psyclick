# PsyClick Secure Backup/Restore Evidence

Date executed: 10 July 2026  
Environment: Windows workspace; PsyClick Secure source tree; synthetic temporary SQLite database

## Executed test

`psyclick-secure/tests/test_security_controls.py::test_encrypted_backup_passes_restore_validation`

## Observed result

- Backup created successfully.
- Backup file was not SQLite plaintext (`SQLite format 3` header was absent).
- SHA-256 digest verification passed.
- Windows DPAPI decryption passed.
- Isolated temporary restore opened successfully.
- SQLite `PRAGMA integrity_check` returned `ok`.
- Backup metadata was updated to `verified`.

## Evidence boundary

This is a repeatable synthetic regression/restore-validation test, not an institutional production backup drill. A full submission still requires an administrator to execute the documented procedure against the approved target backup location, record RPO/RTO, verify record counts and sample reports, and sign the recovery record.
