# PsyClick Secure — CS0029 InfoSec Deliverable: Session Handoff

**Written:** 11 July 2026, end of session (model switch mid-Cowork-task is not currently supported, so this document exists to brief a fresh session with zero memory of this conversation).

**Read this first, then verify against the actual files before doing anything — don't trust any number in here that you can re-check in 30 seconds.**

---

## 1. Project identity

- **Thesis:** PsyClick — a Clinical Decision Support System that detects single-session psychomotor disturbances via EWMA-based multivariate analysis of keystroke and cursor dynamics.
- **Team:** Añonuevo, Ballano, Huertas (Crisp — the user), Tablate. Adviser: Mr. Justine Jude C. Pura. FEU Institute of Technology, Manila, BS CS (Software Engineering).
- **This task:** a *separate, layered* deliverable — the CS0029 (Information Assurance & Security) Final Project, built on top of the same PsyClick system but graded against different requirements than the main thesis defense.
- **Workspace root:** `C:\Users\Lana\Documents\psyclick-1` (the user's connected folder — persists across sessions). Contains:
  - `psyclick-clinical/` — the original, non-hardened app. **Left untouched intentionally** — keep it that way unless told otherwise.
  - `psyclick-secure/` — a separate, hardened build. This is where all CS0029 security work happens. Runs on port **5101** (clinical uses 5001). Data directory is `PSYCLICK_SECURE_HOME` env var, defaults to `%APPDATA%\PsyClickSecure`.
  - `artifacts/` — prior-session deliverables (see Section 3).

## 2. Source spec (Final Project Specification.docx) — required deliverables

Per Section IX of the spec, each group must submit: (1) Complete Thesis Manuscript Ch 1–6, (2) System Prototype/Working Application, (3) Security Architecture Diagram, (4) Risk Assessment Report, (5) Security Testing Report, (6) User Manual, (7) Source Code Repository, (8) Presentation Slides, (9) Final Defense Demonstration.

Mandatory security features (Section III): Authentication (login, password policy, MFA optional), Authorization (RBAC, privilege mgmt), Data Protection (encryption, secure password storage, secure transmission), Audit/Accountability (activity logs, action tracking, login history), Availability (backup/recovery, redundancy), Security Monitoring (IDS concept, incident response).

Penetration testing is explicitly allowed to be **"Simulation or Conceptual"** — this matters, don't feel obligated to fabricate live pentest results.

## 3. What existed before this session (prior session, dated 10 July 2026)

Found already in `psyclick-1/artifacts/`: a completed thesis docx, a completed security document, a user manual, a UAT form template, a defense deck (`PsyClick_CS0029_Final_Defense_Presentation.pptx`), diagrams (`system-architecture.png`, `dfd.png`, `erd.png`, `network-architecture.png`), `psyclick-secure-source.zip`, `psyclick-secure-frontend-build.zip`, and a few evidence markdown files. A `FINAL_PROJECT_DELIVERABLE_CHECKLIST.md` in that folder claimed several security "release blockers" were still unaddressed — **on inspection this session, that checklist was stale/overly conservative**: most controls were actually already implemented in code. Don't trust that checklist as current status; this document supersedes it.

## 4. What I actually did this session (11 July 2026) — verified, not assumed

1. **Audited `psyclick-secure` source code directly** (not just docs). Confirmed real, working: scrypt password hashing with policy (12-char min), 5-attempt/15-min account lockout, RBAC (admin/clinician/auditor) via `require_roles()`, hashed+expiring bearer sessions, ownership-scoped queries (`_scoped_clinician_id()`), server-side fail-closed consent gate, hash-chained audit log with `verify_audit_chain()`, DPAPI-encrypted backups with SHA-256 + isolated-directory restore validation, restricted CORS.
2. **Added `intrusion_monitor.py`** (new file) — a threshold-based brute-force/credential-stuffing detector (8 failures/5-min window, tracked by both source IP and target account). Wired into `POST /api/login` in `api_server.py`: throttles the offending source for 2 minutes and writes a `"security"` category hash-chained audit event. Added a new `GET /api/security/intrusion-alerts` endpoint (admin/auditor only). Added 4 new regression tests to `tests/test_security_controls.py` (`IntrusionMonitorTests` class).
3. **Ran the full test suite for real:** `pytest tests/test_security_controls.py` → **9 passed, 1 failed** (`test_encrypted_backup_passes_restore_validation` fails only because Windows DPAPI isn't available on the Linux dev sandbox — expected to pass on the Windows target platform; not a code defect).
4. **Ran bandit SAST** on all 10 backend modules (4,094 LOC): **0 High**, 13 Medium (all rule B608, SQL string-construction in `api_server.py`/`database_manager.py` — manually reviewed and confirmed as false positives: only static query-shape fragments are in f-strings, all caller-supplied values go through parameterized `?` binds), 15 Low (rule B110, broad `try/except/pass` in non-security-critical paths — telemetry logging, optional cloud sync).
5. **Ran `npm audit`** on the frontend: 16 advisories initially (1 critical, 9 high, 5 moderate, 1 low) → ran `npm audit fix` (non-breaking) → **8 remain (7 high, 1 moderate)**, all confined to devDependencies (Electron/Vite/electron-builder toolchain, not shipped to end users). Zero advisories remain in shipped runtime dependencies.
6. **Edited the INFOSEC documentation docx** (paragraph/table-level, not a rewrite):
   - Fixed the "six passing tests" claim → accurate "ten tests, nine pass on any platform, DPAPI test is Windows-only."
   - Added new subsection **4.6.4 Security Monitoring and Intrusion Detection** describing `intrusion_monitor.py`.
   - Expanded **5.4.3 Vulnerability Assessment** with the real bandit + npm audit findings and disposition.
   - Added 3 rows to the security test-evidence table (SEC-10 SAST, SEC-11 SCA, SEC-12 intrusion monitor).
   - Added 2 rows to the in-doc Risk Assessment Matrix (brute-force risk, vulnerable build-toolchain deps).
   - **Found and fixed a genuine gap:** the "API Documentation" heading in the Appendix had zero content underneath it. Filled it in with all 47 real API endpoints (grouped by function), pulled directly from `api_server.py`.
   - Verified the Security Architecture Diagram (Figure 38), DFD (Figure 39), ERD (Figure 40), and Network Architecture (Figure 41) are already embedded with real images — no changes needed there.
7. **Updated the User Manual** (`PsyClick_CS0029_User_Manual.docx` → `PsyClick_Secure_User_Manual.docx`): retitled to "PsyClick Secure," added lockout/intrusion-monitor guidance to the sign-in and troubleshooting sections.
8. **Created two new standalone deep-dive reports** (not just in-doc summaries — full separate documents):
   - `PsyClick_Secure_Risk_Assessment_Report.docx` — 16-item risk register scored Likelihood×Impact (inherent vs. residual), asset inventory, threat actor profiles, risk heat map, treatment plan, approval page.
   - `PsyClick_Secure_Security_Testing_Report.docx` — full bandit findings table, full npm audit before/after table, full regression test results, a 10-scenario conceptual penetration-test walkthrough, findings summary, remediation status.

## 5. Final deliverable files from this session

Location: `C:\Users\Lana\...\outputs\` (temporary scratch area) — **these need to be copied into `psyclick-1` or wherever you want them to live permanently; they don't persist in outputs between sessions.**

| File | Status |
|---|---|
| `PsyClick_INFOSEC_Documentation_COMPLETED_v2.docx` | **Use this one.** Final, most complete version. |
| `INFOSEC - DOCUMENTATION (Completed).docx` | Stray — an unmodified duplicate from a failed early save. Ignore/delete. |
| `PsyClick_INFOSEC_Documentation_COMPLETED.docx` | Superseded v1 (missing the API Documentation fix). Ignore/delete. |
| `PsyClick_Secure_Risk_Assessment_Report.docx` | New standalone deliverable. |
| `PsyClick_Secure_Security_Testing_Report.docx` | New standalone deliverable. |
| `PsyClick_Secure_User_Manual.docx` | Updated deliverable. |

## 6. Code changes (already committed to disk in the workspace folder — these persist)

- `psyclick-1/psyclick-secure/intrusion_monitor.py` — **new file**
- `psyclick-1/psyclick-secure/api_server.py` — modified (import + wire-in at `/api/login`, new `/api/security/intrusion-alerts` route)
- `psyclick-1/psyclick-secure/tests/test_security_controls.py` — modified (added `IntrusionMonitorTests`, 4 new tests)
- `psyclick-1/psyclick-clinical/` — **untouched**, kept as the non-secure baseline

## 7. Outstanding gaps / suggested priority order for the next session

1. **`psyclick-secure-source.zip` is stale** — doesn't include `intrusion_monitor.py` or the updated tests. My re-zip attempt timed out (the frontend tree is large; a 45-second tool budget wasn't enough even with `node_modules`/`dist` excluded). Retry with a longer-lived process, or zip just the backend `.py` files + `tests/` if the frontend archive is tracked/rebuilt separately.
2. **Defense deck untouched** — `artifacts/PsyClick_CS0029_Final_Defense_Presentation.pptx` still reflects the pre-session state (old test counts, no intrusion-monitor mention).
3. **Chapter 4 (Results and Discussion) statistics were NOT verified this session** — flagged from an earlier, separate session's memory: numbers like κ=0.466, 89.4–90.1% variance reduction, ISO/IEC 25010 scores, etc. were previously flagged as possibly generated from the theoretical framework rather than actual computed data, not confirmed against a real dataset. This is out of scope for the INFOSEC deliverable specifically, but it's the single biggest risk sitting in the manuscript before a defense. **Recommend an explicit pass verifying every Chapter 4 number traces to an actual computation/dataset before submission** — this is a research-integrity issue, not a security one, so treat it as high priority regardless of what InfoSec work is next.
4. **Live/external evidence still needed** (requires real people/hardware, can't be done by an agent): authorized dynamic penetration test against a running deployment, clean install on an independent workstation, signed UAT forms, a live restore drill, a live defense rehearsal.
5. **The automated "empty section" sweep of the INFOSEC docx was inconclusive** — the document has inconsistent heading styles (some body paragraphs are styled as Headings), which broke a scripted completeness check. I manually found and fixed one true gap (API Documentation); there could be others. Worth a manual skim before final submission, especially Chapters 1–3, which were only spot-checked this session, not deeply re-audited.
6. **MFA** — documented as a recommendation only, not implemented in code.
7. **Field/column-level encryption of the live SQLite database** (as opposed to just encrypted backups) — documented as a known limitation (Risk Assessment Report, item R-06), not implemented. A deterministic blind-index scheme would be needed to encrypt lookup fields (e.g. `student_id`) without breaking `WHERE`/`GROUP BY` queries — flagged as non-trivial, don't rush it.

## 8. Useful technical facts (so you don't have to re-derive them)

- psyclick-secure port: **5101**. Clinical: 5001.
- Roles: `admin`, `clinician`, `auditor` — enforced via `require_roles()` decorator + `_scoped_clinician_id()` ownership scoping in `api_server.py`.
- Password hashing: `hashlib.scrypt`, format `"scrypt:..."`, 12-char minimum policy in `database_manager.py`.
- Backup encryption is **Windows DPAPI only** (`ctypes.windll`) — will always fail on non-Windows dev machines. Expected, not a bug.
- Full API surface: 47 routes (auth, clinical workflow, records/reporting, audit/security monitoring, admin, sync/health, normative/research mode) — the complete list now lives in the INFOSEC docx Appendix "API Documentation" section, and in `api_server.py` directly (`grep -n "@app.route"`).
- To generate/edit `.docx` files with `docx` (npm) in this sandbox: `export NODE_PATH=/usr/local/lib/node_modules_global/lib/node_modules` before `require('docx')` will resolve.
- To read/edit files under `psyclick-1/` in the sandbox, use the Bash tool against the mounted path (varies by session — check the `<env>`/system prompt's path mapping at the start of each new session); the Read/Write/Edit file tools may not reach that path directly depending on how the folder is connected.

## 9. Suggested opening message for the next session

> Continue the CS0029 InfoSec deliverable work on PsyClick Secure. Read `HANDOFF.md` in the `psyclick-1` folder root for full context on what's done and outstanding. Priority order: (1) regenerate `psyclick-secure-source.zip` to include `intrusion_monitor.py` and the updated tests, (2) update the defense deck to reflect the intrusion monitor and corrected test counts, (3) do a dedicated pass verifying every Chapter 4 statistical claim in the thesis against real source data — this is flagged as the highest-risk open item.
