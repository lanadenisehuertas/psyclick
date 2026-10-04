# PsyClick Secure

This folder is a separate hardened PsyClick build. It does not share the current `psyclick-clinical` source folder or its development port. The secure build uses:

- SQLite data under `%APPDATA%\\PsyClickSecure` when packaged; `.secure-data` during development.
- API on `127.0.0.1:5101` with debug mode disabled.
- scrypt password hashing with per-account salts and password policy enforcement.
- Server-side bearer sessions with idle/absolute expiry and revocation.
- Role-based access control for administrators, clinicians, and auditors.
- Persisted consent records required before telemetry capture.
- Hash-chained audit events and verification endpoint.
- Windows DPAPI-protected exports and encrypted SQLite backups with SHA-256 verification.
- Restricted CORS origins and Electron renderer isolation.

## Run the secure backend

```powershell
python -m venv .venv
.\\.venv\\Scripts\\pip install -r requirements.txt
python api_server.py
```

The first account created becomes the administrator. Subsequent account provisioning requires an authenticated administrator session.

## Run the secure frontend

```powershell
cd frontend
npm install
npm run dev
```

Use the secure launcher from the project root for the combined workflow:

```powershell
.\\start_secure.bat
```

## Verification

Run the full suite from this folder:

```powershell
$env:PYTHONPATH = "."
python -m unittest discover -s tests
```

- `tests/test_algorithms.py` checks the analysis math: feature extraction against known inputs, the normative baseline matrix, Hotelling T² and its contribution decomposition, the EWMA recursion, fuzzy membership and flag rules, and the normative-stats recomputation.
- `tests/test_integration.py` runs complete assessment sessions through the real API with scripted keyboard/mouse input, including skipped items, very short answers and sessions with no typing.
- `tests/test_security_controls.py` covers hashed credentials, password policy, session revocation, consent fail-closed behavior, audit-chain tamper detection, and encrypted backup restore validation. Windows DPAPI tests require Windows.

`GET /api/db-health` (authenticated) reports `normative_baseline_loaded`; it must be `true` in a packaged build.

This build remains a non-diagnostic research/decision-support system. Production clinical use still requires institutional approval, dynamic penetration testing, a clean installation test, restore-drill evidence, and privacy/clinical-owner sign-off.
