from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\Users\Lana\Downloads\00 Thesis Paper FULL (9).docx")
ART = ROOT / "artifacts"
OUTPUT = ART / "00 Thesis Paper FULL (9)_COMPLETED.docx"
DIAGRAMS = ART / "diagrams"
ART.mkdir(parents=True, exist_ok=True)


def set_cell(cell, value, bold=False, size=8.5, color=None):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(str(value))
    r.bold = bold
    r.font.name = "Arial"
    r.font.size = Pt(size)
    if color:
        r.font.color.rgb = RGBColor.from_string(color)


def format_table(table):
    table.style = "Table Grid"
    for i, cell in enumerate(table.rows[0].cells):
        set_cell(cell, cell.text, bold=True, color="FFFFFF")
        tc_pr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd"); shd.set(qn("w:fill"), "17324D"); tc_pr.append(shd)
    for row_i, row in enumerate(table.rows[1:], start=1):
        for cell in row.cells:
            if row_i % 2 == 0:
                tc_pr = cell._tc.get_or_add_tcPr(); shd = OxmlElement("w:shd"); shd.set(qn("w:fill"), "F2F4F6"); tc_pr.append(shd)
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                for r in p.runs:
                    r.font.name = "Arial"; r.font.size = Pt(8.5)


def make_paragraph(doc, text, style="Normal"):
    return doc.add_paragraph(text, style=style)


def make_table(doc, headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    for i, header in enumerate(headers):
        set_cell(t.rows[0].cells[i], header, bold=True, color="FFFFFF")
    for row in rows:
        cells = t.add_row().cells
        for i, value in enumerate(row):
            set_cell(cells[i], value)
    format_table(t)
    return t


def insert_before(anchor, nodes):
    previous = None
    for factory in nodes:
        element = factory()
        xml = element._p if hasattr(element, "_p") else element._tbl
        if previous is None:
            anchor._p.addprevious(xml)
        else:
            prev_xml = previous._p if hasattr(previous, "_p") else previous._tbl
            prev_xml.addnext(xml)
        previous = element


def insert_after(anchor, nodes):
    previous = anchor
    for factory in nodes:
        element = factory()
        previous._p.addnext(element._p if hasattr(element, "_p") else element._tbl)
        previous = element if hasattr(element, "_p") else previous
    return previous


def p_factory(doc, text, style="Normal"):
    return lambda: make_paragraph(doc, text, style)


def table_factory(doc, headers, rows):
    return lambda: make_table(doc, headers, rows)


def picture_factory(doc, path, caption):
    def factory():
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(path), width=Inches(6.4))
        p.add_run().add_break()
        cap = p.add_run(caption); cap.italic = True; cap.font.size = Pt(9)
        return p
    return factory


def find_paragraph(doc, predicate):
    for p in doc.paragraphs:
        if predicate(p.text):
            return p
    raise ValueError("Anchor paragraph not found")


def create_uat_form():
    out = ART / "PsyClick_CS0029_User_Acceptance_Test_Form.docx"
    d = Document(); d.add_heading("PsyClick CS0029 User Acceptance Test Form", 0)
    d.add_paragraph("This form must be completed by actual representative users. Blank signature fields are intentional; no acceptance result or signature is fabricated by this document.")
    d.add_paragraph("Version / Build: ____________________    Date: ____________________    Test site: ____________________")
    d.add_paragraph("Evaluator name and role: ____________________________________________")
    rows = [
        ("UAT-01", "Authentication", "Authorized user can log in; unauthorized attempts are denied and logged.", "", ""),
        ("UAT-02", "Consent", "User understands capture and system cannot begin before consent.", "", ""),
        ("UAT-03", "Workflow", "Complete a 10–15 minute session without confusion or data loss.", "", ""),
        ("UAT-04", "Dashboard", "User can identify flag, threshold, PSI/PAI, confidence, and domain.", "", ""),
        ("UAT-05", "Privacy", "User understands what is captured and what is not retained.", "", ""),
        ("UAT-06", "Reports", "Authorized user generates and protects a readable report.", "", ""),
        ("UAT-07", "Recovery", "Administrator follows the restore procedure using a verified backup.", "", ""),
        ("UAT-08", "Audit", "Auditor locates login, consent, access, export, and configuration events.", "", ""),
        ("UAT-09", "Clinical safety", "User recognizes output is non-diagnostic and does not replace judgment.", "", ""),
        ("UAT-10", "Overall quality", "Mean acceptance rating ≥4.0/5.0 with no unresolved critical defect.", "", ""),
    ]
    make_table(d, ["ID", "Area", "Acceptance Criterion", "Pass/Fail + Evidence", "Evaluator Initials"], rows)
    d.add_heading("Sign-off", 1)
    d.add_paragraph("Evaluator signature: __________________________________  Date: ______________")
    d.add_paragraph("Clinical owner signature: ______________________________  Date: ______________")
    d.add_paragraph("Project adviser / professor signature: _____________________  Date: ______________")
    d.save(out)
    return out


def create_archives():
    source_zip = ART / "psyclick-secure-source.zip"
    build_zip = ART / "psyclick-secure-frontend-build.zip"
    source_root = ROOT / "psyclick-secure"
    with ZipFile(source_zip, "w", ZIP_DEFLATED) as z:
        for path in source_root.rglob("*"):
            if path.is_file() and "node_modules" not in path.parts and "dist-python" not in path.parts and "dist" not in path.parts and "__pycache__" not in path.parts and "dist-electron-clinical" not in path.parts:
                z.write(path, path.relative_to(ROOT))
    with ZipFile(build_zip, "w", ZIP_DEFLATED) as z:
        dist = source_root / "frontend" / "dist"
        for path in dist.rglob("*"):
            if path.is_file(): z.write(path, path.relative_to(source_root))
        for name in ["api_server.py", "database_manager.py", "security_manager.py", "backend_controller.py", "anomaly_engine.py", "feature_extractor.py", "dynamics_logger.py", "requirements.txt"]:
            z.write(source_root / name, Path("backend") / name)
    return source_zip, build_zip


doc = Document(SOURCE)
# The supplied thesis contains fractional twip margin values that python-docx
# cannot reuse when creating new tables. Normalize only the section margins so
# inserted security tables can be serialized without corrupting the manuscript.
for section in doc.sections:
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)

# Chapter 2: make the research gap explicit, as required by the CS0029 specification.
chapter3_heading = find_paragraph(doc, lambda t: t.strip() == "Chapter 3")
research_gap_nodes = [
    p_factory(doc, "2.6 Research Gap", "Heading 2"),
    p_factory(doc, "The reviewed literature establishes that keystroke and cursor dynamics can provide behavioral signals, but much prior work treats a single feature, relies on population-level thresholds, or provides limited clinician-facing explanation. The thesis addresses a gap in single-session, within-person, multivariate analysis by combining hardware normalization, an EWMA personal baseline, Hotelling’s T², feature contribution analysis, PSI/PAI, fuzzy outputs, and domain profiling. The CS0029 extension addresses the parallel information-assurance gap: a functional behavioral prototype must also demonstrate consent enforcement, authentication, authorization, protected storage/export, accountability, recovery, and documented security testing."),
]
insert_before(chapter3_heading, research_gap_nodes)

# Chapter 3: add required security/system-analysis subsections and diagrams.
chapter3_anchor = find_paragraph(doc, lambda t: t.startswith("3.4 Hardware and Software Specifications"))
db_rows = [
    ("clinicians", "clinician_id", "scrypt password_hash; role; status; failed_attempts; locked_until", "Restricted identity"),
    ("security_sessions", "session_id", "token_hash; clinician_id; role; last_seen_at; expires_at; revoked_at", "Confidential session metadata"),
    ("consent_records", "consent_id", "patient_id; clinician_id; consent_version; decision; recorded_at; withdrawn_at", "Restricted consent"),
    ("intake_sessions", "session_id", "patient/session identifiers; features; scores; flag; rationale", "Restricted clinical/behavioral"),
    ("audit_log", "log_id", "actor; actor_id; action; outcome; prev_hash; entry_hash; timestamp", "Confidential accountability"),
    ("backup_records", "backup_id", "created_by; file_path; SHA-256; encrypted; status; verified_at", "Confidential recovery metadata"),
]
chapter3_nodes = [
    p_factory(doc, "3.3.4 Security Architecture", "Heading 3"),
    p_factory(doc, "The secure build applies defense in depth: a local Electron/React presentation layer communicates with a loopback API; server middleware authenticates bearer sessions; role checks and clinician ownership scope protected records; consent records gate telemetry; SQLite persistence uses parameterized queries and transactions; audit events are hash-chained; Windows DPAPI protects exports and backups; and administrators can verify backup integrity before restore. Controls described as target or proposed remain release requirements until independently tested.") ,
    picture_factory(doc, DIAGRAMS / "system-architecture.png", "Figure 38. PsyClick security architecture for the secure build."),
    p_factory(doc, "3.3.5 Data Flow Diagram (DFD)", "Heading 3"),
    p_factory(doc, "The context and Level-1 DFD identify clinicians, patients/participants, administrators, and auditors as external actors. Authenticated requests flow through intake/consent, capture/HAL, feature analysis, reporting, and security operations. Raw telemetry remains local by default; protected reports and encrypted backups are handled as restricted outputs."),
    picture_factory(doc, DIAGRAMS / "dfd.png", "Figure 39. Security-aware PsyClick context and Level-1 DFD."),
    p_factory(doc, "3.3.6 Entity Relationship Diagram (ERD)", "Heading 3"),
    p_factory(doc, "The ERD separates clinician identity, security sessions, consent, clinical sessions, analysis results, reports, audit evidence, and backup metadata. This separation supports least privilege, retention decisions, and independent integrity checks."),
    picture_factory(doc, DIAGRAMS / "erd.png", "Figure 40. Security-aware core PsyClick ERD."),
    p_factory(doc, "3.3.7 Network Architecture", "Heading 3"),
    p_factory(doc, "The secure development system uses a local-first topology: the Electron renderer communicates with the API on 127.0.0.1:5101, and the API accesses the separate secure SQLite data directory. The packaged deployment uses %APPDATA%\\PsyClickSecure. No raw telemetry is sent to a cloud service by default. External institutional backup storage is a future controlled integration, not an executed claim."),
    picture_factory(doc, DIAGRAMS / "network-architecture.png", "Figure 41. PsyClick Secure local-first network and trust boundaries."),
    p_factory(doc, "3.3.8 Database Design and Data Classification", "Heading 3"),
    p_factory(doc, "The secure database design classifies clinician identity, consent, clinical/behavioral records, sessions, audit evidence, and recovery metadata as restricted or confidential. Direct SQL string concatenation is prohibited; parameterized queries, foreign-key constraints, transaction boundaries, protected file paths, and application-level authorization are required."),
    table_factory(doc, ["Entity", "Primary Key", "Security-Relevant Fields", "Classification"], db_rows),
    p_factory(doc, "3.3.9 System Requirements and Feasibility Study", "Heading 3"),
    p_factory(doc, "Functional requirements are secure clinician account management; authenticated access; pseudonymous client intake; recorded consent; keyboard and mouse calibration; PHQ-9, GAD-7, and emotional tasks; feature extraction; EWMA/T²/PSI/PAI analysis; dashboard/report generation; audit review; and encrypted backup verification. Non-functional requirements are local-first operation, ordinary-workstation support, usability for clinicians, non-diagnostic language, least privilege, recoverability, and controlled performance during a standard 10–15 minute session."),
    table_factory(doc, ["Feasibility Area", "Assessment"], [
        ("Technical", "The supplied desktop stack, SQLite persistence, statistical pipeline, and secure build controls run locally; the frontend production build and six security regression tests passed."),
        ("Operational", "The workflow fits a supervised assessment session, but staff training, consent practice, account provisioning, and incident reporting are required."),
        ("Economic", "The system uses existing workstations and input devices; costs remain for endpoint protection, encrypted backup media, training, maintenance, and testing."),
        ("Legal / ethical", "Use requires informed consent, purpose limitation, approved retention, Data Privacy Act/ethics review, and non-diagnostic clinician oversight."),
        ("Schedule", "Prototype and documentation are prepared; external UAT, clean installation, penetration test, restore drill, and defense remain scheduled activities."),
    ]),
]
insert_before(chapter3_anchor, chapter3_nodes)

# Chapter 4: implementation and security controls, with status labels.
chapter5_anchor = find_paragraph(doc, lambda t: t.strip() == "Chapter V")
chapter4_nodes = [
    p_factory(doc, "4.6 Security Controls Implemented in PsyClick Secure", "Heading 2"),
    p_factory(doc, "The separate PsyClick Secure build implements the following controls in code: scrypt password hashing with per-account salts and a 12-character policy; five-attempt/15-minute lockout; server-side bearer sessions with 15-minute idle and 8-hour absolute limits; role-based access for administrators, clinicians, and auditors; record ownership scoping; consent records required before capture; parameterized SQLite access; restricted CORS; hash-chained audit events; and Windows DPAPI-protected exports and encrypted backups. These claims are supported by the source files in psyclick-secure and the six passing security regression tests listed in Chapter 5."),
    p_factory(doc, "4.6.1 Encryption Techniques", "Heading 3"),
    p_factory(doc, "Passwords are protected with Python hashlib.scrypt using a unique random salt and stored parameters. Exported reports and SQLite backup packages are protected with Windows DPAPI in the secure build and receive a SHA-256 digest for verification. The secure build does not claim TLS for the loopback channel because it is bound to 127.0.0.1; any future network transfer must use an institution-approved encrypted channel."),
    p_factory(doc, "4.6.2 Authentication and Authorization Mechanisms", "Heading 3"),
    p_factory(doc, "The API permits unauthenticated access only to login, first-account bootstrap registration, and readiness checks. Other routes require a bearer session stored server-side as a token hash. Roles are enforced in service middleware; clinician queries are scoped to the authenticated clinician unless an administrator is authorized; and logout revokes the session. Authentication results are recorded without logging passwords or tokens."),
    p_factory(doc, "4.6.3 Secure Coding Practices", "Heading 3"),
    p_factory(doc, "The secure build uses parameterized SQL, generic authentication errors, bounded identifiers, fixed local paths for protected backups, restrictive CORS, no Flask debug mode, Electron context isolation, disabled Node integration, session revocation, audit-chain verification, and temporary-directory restore validation. Development/test bypasses and plaintext legacy credentials are not acceptable for a new deployment; the migration path exists only to convert an academic prototype database and must be followed by credential reset."),
    p_factory(doc, "4.7 Development Methodology and System Features", "Heading 2"),
    p_factory(doc, "PsyClick was developed iteratively using the Agile/Scrum-oriented process described in Chapter 3. Each increment combined workflow functionality with misuse cases, security acceptance criteria, and regression checks. The separate secure build preserves the analytical features of the thesis while adding a security-focused administration surface."),
    table_factory(doc, ["Required Module", "Secure Build Evidence", "Status"], [
        ("User Management", "Administrator account provisioning, account status, and role selection for administrator, clinician, and auditor.", "Implemented"),
        ("Authentication", "scrypt password hashes, 12-character policy, lockout, server-side session token, expiry, and logout revocation.", "Implemented; MFA remains recommended"),
        ("Dashboard", "Clinician dashboard, session history, client/patient views, and analytical report navigation.", "Implemented"),
        ("Main Business Process", "Intake, consent, calibration, questionnaires, emotional task, analysis, and decision-support report.", "Implemented; supervised use only"),
        ("Reports", "HTML report generation plus DPAPI-protected export workflow and audit event.", "Implemented in secure build"),
        ("Audit Logs", "Hash-chained audit records, verification endpoint, and administrator/auditor review surface.", "Implemented in secure build"),
    ]),
]
insert_before(chapter5_anchor, chapter4_nodes)

# Chapter 5: security evaluation and testing with actual evidence boundaries.
chapter6_anchor = find_paragraph(doc, lambda t: t.strip() == "Chapter VI")
test_rows = [
    ("SEC-01", "Password hashing and policy", "Weak password rejected; stored password is scrypt hash; first account is admin", "PASS – regression test"),
    ("SEC-02", "Session revocation", "Bearer session authenticates, then fails after revocation", "PASS – regression test"),
    ("SEC-03", "Consent fail-closed", "No active consent before grant; withdrawal removes active consent", "PASS – data-layer regression test"),
    ("SEC-04", "Audit integrity", "Hash chain verifies; tampered detail is detected", "PASS – regression test"),
    ("SEC-05", "Encrypted backup restore", "DPAPI backup is not plaintext; SHA-256 and SQLite integrity check pass", "PASS – Windows regression test"),
    ("SEC-06", "Frontend build", "Secure React frontend compiles with Vite", "PASS – production build"),
    ("SEC-07", "Dynamic HTTP vulnerability/penetration test", "Authorized request-level evidence against a running deployment", "NOT EXECUTED in this environment"),
    ("SEC-08", "Clean target-workstation installation", "Fresh workstation install and launch evidence", "NOT DEMONSTRATED in this environment"),
    ("SEC-09", "User acceptance signatures", "Representative users complete and sign UAT form", "PENDING external participants"),
]
risk_rows = [
    ("SQL injection / malicious input", "Medium", "High", "Parameterized queries, input validation, negative tests"),
    ("Data breach / plaintext export", "Medium", "High", "DPAPI-protected exports, encrypted database/backup policy, restricted paths"),
    ("Account hijacking", "Medium", "High", "scrypt, lockout, session expiry/revocation, MFA recommended before institutional use"),
    ("Unauthorized access / IDOR", "Medium", "High", "Bearer sessions, RBAC, ownership-scoped queries, deny-by-default middleware"),
    ("Malware / ransomware", "Medium", "High", "Endpoint protection, least privilege, encrypted verified backups"),
    ("Insider misuse", "Possible", "High", "Least privilege, audit chain, administrator review, separation of duties"),
    ("Denial of Service", "Unlikely", "Moderate", "Local binding, bounded inputs, resource monitoring, graceful failure"),
    ("XSS / unsafe report content", "Unlikely", "High", "React escaping, fixed report template, no untrusted HTML injection; dynamic scan pending"),
]
mapping_rows = [
    ("Confidentiality", "Encryption and least privilege", "scrypt credentials; DPAPI exports/backups; RBAC; ownership scope"),
    ("Integrity", "Hashing and transactions", "SHA-256 backup digests; hash-chained audit log; SQLite transactions; parameterized SQL"),
    ("Availability", "Backup system", "Encrypted backup creation and restore validation; RPO/RTO policy remains to be exercised operationally"),
    ("Authentication", "Unique identity and secure sessions", "Server-side bearer sessions, lockout, idle/absolute expiry, revocation"),
    ("Authorization", "RBAC and record-level checks", "Admin, clinician, auditor roles; scoped clinical queries"),
    ("Accountability", "Audit logs", "Login, denial, consent, access, export, configuration, backup, and restore events"),
]
chapter5_nodes = [
    p_factory(doc, "5.4 Security Evaluation and Testing", "Heading 2"),
    p_factory(doc, "The secure build was evaluated using source-level regression tests, a production frontend build, and synthetic encrypted-backup restoration. The evidence below reports only actions actually executed in the supplied workspace on 10 July 2026. Dynamic HTTP vulnerability testing, an authorized penetration test against a running deployment, clean target-workstation installation, UAT signatures, and live defense activities were not executed by this document and remain external deliverables."),
    p_factory(doc, "5.4.1 Functional Testing", "Heading 3"),
    p_factory(doc, "The thesis contains functional and black-box testing of the research prototype. The secure build adds regression coverage for password policy, session revocation, consent state, audit-chain tamper detection, and encrypted backup validation. The secure frontend production build completed successfully with Vite."),
    p_factory(doc, "5.4.2 Vulnerability Assessment", "Heading 3"),
    p_factory(doc, "The source review covered authentication, authorization, consent, SQL construction, report/export paths, audit logging, backup handling, Electron isolation, CORS, and secret handling. The secure build closes the previously identified plaintext-password, missing-session, consent-bypass, and unprotected-audit gaps in the reviewed code. A dependency scan, dynamic DAST scan, and independent review are still required before production claims."),
    table_factory(doc, ["Threat Identification", "PsyClick Exposure", "Current Control / Required Follow-up"], [
        ("Unauthorized access", "Compromised or shared clinician account; direct local API attempt", "Hashed credentials, lockout, server sessions, RBAC, ownership scope; MFA remains recommended"),
        ("Data leakage", "Database, report, backup, temporary file, or external transfer", "DPAPI exports/backups, local-first design; institutional encryption/key policy required"),
        ("Malware infection", "Compromised workstation or ransomware", "Least privilege, endpoint controls, encrypted backups; operational endpoint policy required"),
        ("Insider threat", "Excessive access, export, or record browsing", "RBAC, ownership scope, hash-chained audit review"),
        ("Denial of Service", "Repeated requests, disk exhaustion, corrupt state", "Loopback binding, input limits, transactions, monitoring and operational recovery"),
        ("SQL injection", "Malicious text/identifier input", "Parameterized queries and validation; dynamic test evidence still required"),
        ("Cross-Site Scripting", "Untrusted content rendered in report/UI", "React escaping and fixed templates; dynamic XSS test still required"),
    ]),
    p_factory(doc, "5.4.3 Risk Assessment", "Heading 3"),
    table_factory(doc, ["Risk", "Likelihood", "Impact", "Mitigation"], risk_rows),
    p_factory(doc, "5.4.4 Penetration Testing Results (Simulation or Conceptual)", "Heading 3"),
    p_factory(doc, "Conceptual cases include password guessing, session reuse after logout, IDOR/role manipulation, SQL metacharacters, path traversal, plaintext database access, report tampering, audit deletion, consent bypass, and interruption during database writes. No live authorized penetration-test run was performed in this environment; therefore, these cases are recorded as a test plan rather than Passed results."),
    p_factory(doc, "5.4.5 Security Analysis", "Heading 3"),
    p_factory(doc, "The secure build provides a materially stronger baseline than the original prototype: credential hashes are no longer stored as plaintext for new accounts, API routes require sessions, roles and ownership constrain access, consent is persisted and checked, audit integrity is verifiable, and backup/restore validation is automated. Residual risks include endpoint compromise, absence of completed MFA, operational key/DPAPI recovery procedures, the need for dynamic DAST/penetration testing, and clinical automation bias."),
    p_factory(doc, "5.4.6 User Acceptance Testing", "Heading 3"),
    p_factory(doc, "A blank UAT form is supplied as a separate artifact. It contains ten acceptance criteria covering authentication, consent, workflow, dashboard interpretation, privacy, reports, recovery, audit, clinical safety, and overall quality. No participant signatures or acceptance ratings are fabricated; the form must be completed by representative users."),
    table_factory(doc, ["Test ID", "Scenario", "Expected Result", "Evidence Status"], test_rows),
    p_factory(doc, "5.5 Security Evaluation Report", "Heading 2"),
    p_factory(doc, "The security evaluation report consists of the vulnerability assessment, risk analysis, security controls review, and security recommendations above. Threat identification explicitly covers unauthorized access, data leakage, malware infection, insider threats, denial of service, SQL injection, and XSS. The security controls mapping below links confidentiality to encryption, integrity to hashing, availability to backup, authentication/authorization to sessions and RBAC, and accountability to audit logs."),
    table_factory(doc, ["Component", "Requirement", "Evidence / Status"], [
        ("Vulnerability Assessment", "Required", "Source review completed; dynamic DAST/dependency scanning remains external work."),
        ("Risk Analysis", "Required", "Risk matrix and treatment mapping included in Section 5.4.3."),
        ("Security Controls Review", "Required", "Implemented secure controls and remaining limitations documented in Sections 4.6–4.7."),
        ("Security Recommendations", "Required", "Release prerequisites and future enhancements documented in Sections 6.10–6.11."),
    ]),
    table_factory(doc, ["Security Objective", "Control", "PsyClick Implementation"], mapping_rows),
]
insert_before(chapter6_anchor, chapter5_nodes)

# Chapter 6: explicit recommendations and future enhancements.
bibliography_anchor = find_paragraph(doc, lambda t: t.strip() == "BIBLIOGRAPHY")
chapter6_nodes = [
    p_factory(doc, "6.10 Security Recommendations", "Heading 2"),
    p_factory(doc, "Before institutional or clinical deployment, complete a clean installation test; require MFA for administrators and remote/backup access; define DPAPI recovery-key custody and rotation; run dynamic vulnerability scanning and an authorized penetration test; complete signed UAT; perform quarterly restore drills; review dependency and secret exposure; and obtain privacy, ethics, and clinical-owner approval. Maintain the non-diagnostic warning and independent clinician review in every report."),
    p_factory(doc, "6.11 Future Enhancements", "Heading 2"),
    p_factory(doc, "Future work includes longitudinal validation, broader and more diverse clinical samples, additional clinical instruments, FHIR/EHR integration only after identity/API security review, hardware-backed MFA, centralized institutional key management, formal retention/deletion workflows, signed releases, automated DAST/SAST/dependency scanning, and a multi-site security assessment."),
    p_factory(doc, "6.12 Summary of Findings and Conclusions", "Heading 2"),
    p_factory(doc, "The thesis findings support PsyClick as an explainable, local-first, single-session decision-support prototype with measured analytical and software-quality results. The secure build adds a documented security baseline and passing regression evidence for credential hashing, session revocation, consent state, audit tamper detection, encrypted backup verification, and frontend compilation. These results do not replace the remaining external evidence required for institutional production use: independent installation, dynamic security testing, signed UAT, operational restore drill, and responsible approval."),
]
insert_before(bibliography_anchor, chapter6_nodes)

# Append a concise security documentation annex for the required proposed-system outputs.
annex_nodes = [
    p_factory(doc, "APPENDIX – CS0029 SECURITY DOCUMENTATION ANNEX", "Heading 1"),
    p_factory(doc, "Threat Model", "Heading 2"),
    p_factory(doc, "Assets: patient/client identifiers, consent, screening scores, telemetry, derived features, T²/PSI/PAI results, reports, accounts, session tokens, keys, audit logs, backups, and clinical trust. Actors: unauthorized local users, compromised accounts, malware, accidental users, supply-chain attackers, and participants attempting administrative access. Trust boundaries: patient interaction, Electron renderer, loopback API, protected SQLite data, backup target, and administrator functions."),
    p_factory(doc, "Security Policy", "Heading 2"),
    p_factory(doc, "Use unique accounts; apply least privilege; require consent before capture; collect only approved data; protect restricted files; prohibit unencrypted email/file sharing; log access and exports; retain no semantic typed content unless separately approved; patch and lock workstations; verify encrypted backups; report suspected loss, malware, unauthorized access, consent failure, corruption, or disclosure immediately; and never treat PsyClick output as a diagnosis."),
    p_factory(doc, "Incident Response Plan", "Heading 2"),
    p_factory(doc, "Preparation → identification → containment → eradication → recovery → post-incident review. The Incident Coordinator, System Administrator, Data Protection Officer/Privacy Lead, Clinical Lead, and management/communications roles are defined in the accompanying security document. Critical incidents include restricted-data exfiltration, ransomware, key compromise, and widespread unauthorized access."),
    p_factory(doc, "Backup and Recovery Plan", "Heading 2"),
    p_factory(doc, "The secure build creates an encrypted SQLite backup, records its SHA-256 digest and metadata, and validates the copy in an isolated temporary directory using SQLite integrity_check. Operational deployment should use daily/after-session backups, weekly full backups, encrypted/offline separation, a proposed 24-hour RPO, a proposed 4-hour RTO, and quarterly restoration drills. The executed regression test is synthetic and is not a substitute for an institutional drill."),
    p_factory(doc, "Technical Documentation and User Manual", "Heading 2"),
    p_factory(doc, "System architecture, DFD, ERD, network architecture, database schema, API endpoint summary, installation steps, and clinician operating steps are included in the completed CS0029 Security Document. A separate PsyClick Secure User Manual is supplied with this thesis package."),
    p_factory(doc, "API Documentation", "Heading 2"),
    table_factory(doc, ["Endpoint Group", "Purpose", "Authorization"], [
        ("/api/login, /api/register, /api/ping", "Bootstrap, authenticate, and check readiness", "Login/public only; later registration requires administrator"),
        ("/api/stats, /api/patients, /api/session", "Dashboard and scoped clinical record access", "Authenticated session and clinician ownership / administrator scope"),
        ("/api/intake, /api/calibration, /api/assessment", "Consent-gated assessment workflow", "Authenticated clinician session; consent required before capture"),
        ("/api/audit, /api/audit/verify", "Audit review and hash-chain verification", "Administrator or auditor according to route policy"),
        ("/api/admin/backup, /api/admin/backup/verify", "Encrypted backup and restore validation", "Administrator"),
    ]),
    p_factory(doc, "Installation Guide", "Heading 2"),
    p_factory(doc, "Create a Python virtual environment, install requirements.txt, set PSYCLICK_SECURE_HOME for packaged/controlled deployments, start api_server.py on 127.0.0.1:5101, install frontend dependencies, run npm.cmd run build or npm run dev, then create the first administrator account. The separate source archive and frontend build archive are supplied; a fresh independent-workstation installation still requires recorded evidence."),
    p_factory(doc, "User Manual", "Heading 2"),
    p_factory(doc, "Clinicians sign in, create/select a pseudonymous client, explain and record consent, complete calibration and assessment tasks, review the non-diagnostic dashboard/report, protect exports, review audit evidence when authorized, log out, and lock the workstation. Administrators provision accounts, review security status, create/verify encrypted backups, and follow the incident-response plan. The full user manual is supplied separately."),
    p_factory(doc, "Final Project Submission Boundary", "Heading 2"),
    p_factory(doc, "Prepared in this workspace: completed thesis manuscript, secure source archive, secure frontend build archive, security document, user manual, defense presentation, diagrams, regression tests, and UAT form. Not fabricated: clean installation on a separate target workstation, dynamic HTTP vulnerability/penetration-test evidence, UAT signatures, a live defense/rehearsal, and institutional approvals. Those require real people, a controlled environment, and recorded evidence."),
]
for factory in annex_nodes:
    element = factory()
    doc.element.body.append(element._p if hasattr(element, "_p") else element._tbl)

doc.core_properties.comments = "Updated with CS0029 security architecture, implementation, evaluation, threat/risk documentation, and explicit evidence boundaries on 10 July 2026."
# Ask Word to refresh the table of contents and the lists of figures/tables when
# the completed manuscript is opened, so the inserted headings and figures appear.
settings = doc.settings.element
update_fields = settings.find(qn("w:updateFields"))
if update_fields is None:
    update_fields = OxmlElement("w:updateFields")
    settings.append(update_fields)
update_fields.set(qn("w:val"), "true")
doc.save(OUTPUT)

uat = create_uat_form()
source_zip, build_zip = create_archives()
install_report = ART / "INSTALLATION_AND_TEST_EVIDENCE.md"
install_report.write_text("""# PsyClick Secure Installation and Test Evidence\n\nDate: 10 July 2026\n\n## Evidence actually executed\n\n- `python -m unittest discover -s psyclick-secure/tests -p test_*.py`: 6 tests passed.\n- `python -m py_compile` on the secure Python modules: passed.\n- `npm.cmd run build` in `psyclick-secure/frontend`: Vite production build passed.\n- Encrypted synthetic SQLite backup: DPAPI encryption, SHA-256 verification, and SQLite `integrity_check` passed in the regression test.\n\n## Not claimed\n\nA clean installation on an independent target workstation, dynamic HTTP vulnerability scanning, authorized penetration testing, signed UAT, backup drill at an institutional destination, live defense rehearsal, and team presentation were not executed by Codex. They remain required external evidence.\n""", encoding="utf-8")
print(OUTPUT)
print(uat)
print(source_zip)
print(build_zip)
print(install_report)
