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

## Offline-first sync

PsyClick always works on the local SQLite database, with or without internet. When `config.json` holds a `sync_url`, a background thread uploads new accounts, account changes, sessions and deletions, and downloads what other devices changed (immediately after a change, otherwise every minute). Any account can then sign in on any device that has synced once; a new device fetches accounts before its first sign-in. If two offline devices create the same account ID, the second one to sync moves to the next free ID and the change is written to the audit log.

```powershell
python scripts\setup_cloud_sync.py   # once, by the project owner: schema, restricted role, config.json
python scripts\check_cloud_sync.py   # two simulated devices against a throwaway schema
```

The app connects as `psyclick_app`, which can read and write only the `psyclick` schema (accounts and sessions); it cannot see the rest of the Supabase project. `config.json` is git-ignored and is bundled into the installer, so anyone holding an installer can reach the synced data: this suits a demo deployment, not real clinical data.

## Demo data (demonstration only)

```powershell
python scripts\seed_demo.py
```

Creates the administrator **Demo Admin (simulation)** (password `PsyClickDemo2026`; the ID is printed) with fifteen sample clients that cover every result the engine produces: No concerns, Follow up and Review now; slowing, restlessness and mixed patterns; not enough typing; self-harm answers; topic- and load-specific reactions; and improving and worsening histories. Each session is simulated keyboard and mouse input run through the real scoring pipeline (`scripts/demo_simulation.py`), so the scores are what PsyClick computes. The clients belong to the demo account and sync like any other account's data. DEMO-14 and DEMO-15 (restlessness) use hand-set overall scores, because the current engine cannot reach that pattern from simulated input; their flag and label still come from the engine's classifier. Running the script again replaces the demo clients.

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
