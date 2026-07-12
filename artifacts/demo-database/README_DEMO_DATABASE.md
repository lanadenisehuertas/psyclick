# PsyClick Secure — Demonstration Database

This `psyclick_data.db` is a ready-to-use SQLite database populated from your CSV exports, so you have real data to show during the demo. It matches the current secure schema.

## What's inside

- **3 clinician accounts** (below)
- **5 completed assessment sessions** (flags: RED, AMBER, RED, AMBER, GREEN) owned by the admin account
- **1,627 per-question snapshots**
- **106 normative sessions** + normative statistics (population baseline)
- **9,407 audit-log entries**, rebuilt with a **valid hash chain** (the in-app "verify" will report the log as valid, and new actions during the demo chain on correctly)

## Login credentials

| Clinician ID | Name | Password | Role |
|---|---|---|---|
| `2026003` | Aida Maria Perez | `Psychprofile` | **Administrator** (owns the 5 sessions) |
| `2026004` | Dra. Sanchez | `smartmind` | Clinician |
| `2026005` | Frankie | `ilovefrankie` | **Auditor** |

All three roles (administrator, clinician, auditor) are pre-created, so you don't have to create any account live during the demo — though you can still demonstrate creating one.

You log in with the **numeric Clinician ID + password** (not the name).

Notes:
- These accounts were imported with legacy plaintext passwords; **on first login the app automatically upgrades them to scrypt hashing** — that's expected and secure.
- For the demo flow: sign in as **2026003 (admin)** to show account/role management, the 5 existing sessions, backups, and audit verification. Sign in as **2026004 (clinician)** to show a clinician is blocked from admin areas, and as **2026005 (auditor)** to show the auditor can read the audit log but cannot manage accounts.

## Where to put the file

**If you run the packaged/installed app** (reads from %APPDATA%):

1. Close PsyClick Secure completely.
2. Open this folder in Explorer: press `Win + R`, type `%APPDATA%\PsyClickSecure`, press Enter (create the folder if it doesn't exist).
3. Copy `psyclick_data.db` into it, replacing any existing file (back up the old one first if you want to keep it).
4. Start the app and sign in with an account above.

**If you run in development mode** (`start_secure.bat` / `npm run dev`):

- A copy has already been placed at `psyclick-secure\.secure-data\psyclick_data.db`. Just start the app in dev mode and sign in.

## Reset / safety

- Keep a backup of any existing database before replacing it.
- This is synthetic demonstration data — pseudonymous client codes (C-001…C-005), no real patient identities.
