# PsyClick Secure Installation and Test Evidence

Date: 10 July 2026

## Evidence actually executed

- `python -m unittest discover -s psyclick-secure/tests -p test_*.py`: 6 tests passed.
- `python -m py_compile` on the secure Python modules: passed.
- `npm.cmd run build` in `psyclick-secure/frontend`: Vite production build passed.
- Encrypted synthetic SQLite backup: DPAPI encryption, SHA-256 verification, and SQLite `integrity_check` passed in the regression test.

## Not claimed

A clean installation on an independent target workstation, dynamic HTTP vulnerability scanning, authorized penetration testing, signed UAT, backup drill at an institutional destination, live defense rehearsal, and team presentation were not executed by Codex. They remain required external evidence.
