# PsyClick CS0029 Final Project Submission Checklist

Generated 10 July 2026 from the Final Project Specification, thesis, and supplied system.

## Prepared artifacts

- [x] Completed thesis manuscript with inserted CS0029 security chapters/annex: `00 Thesis Paper FULL (9)_COMPLETED.docx`
- [x] Completed security document: `PsyClick_CS0029_Security_Document_COMPLETED.docx`
- [x] User manual: `PsyClick_CS0029_User_Manual.docx`
- [x] User acceptance form template: `PsyClick_CS0029_User_Acceptance_Test_Form.docx`
- [x] Final defense deck: `PsyClick_CS0029_Final_Defense_Presentation.pptx`
- [x] Architecture, DFD, ERD, and network figures: `diagrams/`
- [x] Separate secure source archive: `psyclick-secure-source.zip`
- [x] Separate secure frontend build archive: `psyclick-secure-frontend-build.zip`
- [x] Backup/restore synthetic evidence: `BACKUP_RESTORE_DRILL_EVIDENCE.md`
- [x] Installation/build/test evidence: `INSTALLATION_AND_TEST_EVIDENCE.md`
- [x] Deliverable/rubric traceability matrix embedded in the security document
- [x] Source-code review and release-gate findings embedded in the security document

## Required separate submissions

- [ ] Full thesis manuscript Chapters 1–6, with bibliography, appendices, and approved institutional formatting
- [ ] Source code repository/archive and working prototype build
- [ ] Demonstrated clean installation on the target workstation
- [ ] Dynamic functional, vulnerability, and authorized penetration-test evidence
- [ ] User acceptance test forms/signatures
- [ ] Backup/restore drill evidence
- [ ] Final defense rehearsal, live demonstration, and team presentation

## Release blockers found in the supplied system

- [ ] Replace plaintext clinician passwords with Argon2id/bcrypt and remove development bypasses
- [ ] Add authenticated server sessions, RBAC, record ownership, expiry, revocation, and lockout/MFA
- [ ] Enforce consent in the backend before any capture starts
- [ ] Encrypt restricted database fields/files, reports, backups, and protect keys
- [ ] Make audit events authenticated, append-only/hash-chained, and reviewable
- [ ] Implement encrypted scheduled backups and a verified restore workflow
- [ ] Remove/rotate exposed configuration secrets and restrict CORS/IPC/external report resources

**Conclusion:** the documentation package is substantially complete, but the final project as a whole is not yet ready to claim full security completion until the separate artifacts and release blockers above are addressed and evidenced.
