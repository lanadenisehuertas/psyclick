# PsyClick Final Defense Rehearsal Runbook

This runbook prepares the team for the required 30–40 minute defense. It is a preparation artifact; no live rehearsal, presentation, or signatures are claimed here.

## Proposed timing

- 3 minutes — title, background, and problem
- 4 minutes — objectives and proposed solution
- 5 minutes — workflow, architecture, DFD, ERD, and network boundaries
- 5 minutes — analytical pipeline and thesis results
- 6 minutes — security architecture, threat model, and risk matrix
- 5 minutes — security controls, testing evidence, and remaining limitations
- 8–12 minutes — live demonstration and questions

## Demonstration checklist

- [ ] Start the separate `psyclick-secure` build and confirm API readiness on port 5101.
- [ ] Create the first administrator account using a strong password.
- [ ] Show login, bearer-session creation, logout, and session revocation.
- [ ] Create a clinician account and demonstrate role-limited navigation.
- [ ] Attempt intake without consent and show the fail-closed response.
- [ ] Record consent, run calibration/assessment with synthetic data, and review the dashboard.
- [ ] Export a protected report and show the audit event.
- [ ] Verify the audit chain in Security Center.
- [ ] Create and verify an encrypted backup; show the restore-validation evidence.
- [ ] State clearly that dynamic HTTP penetration testing, institutional UAT signatures, and production clinical approval are external prerequisites.

## Sign-off after the real rehearsal

Presenter 1: __________________________  Date: __________  
Presenter 2: __________________________  Date: __________  
Technical demonstrator: _________________  Date: __________  
Adviser / professor: ____________________  Date: __________
