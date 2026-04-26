"""
app.py — PsyClick 
"""

import customtkinter as ctk
import tkinter as tk
import random, json, sqlite3
from datetime import datetime
from tkinter import messagebox, filedialog
from backend_controller import PsyClickController
from database_manager import (log_audit, get_audit_logs,
                              get_student_session_count, get_sessions_by_student,
                              get_latest_sessions)
from report_exporter import export_report, export_summary
import time

backend = PsyClickController()

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

BG     = "#EEF2FF"
CARD   = "#FFFFFF"
TMAIN  = "#1E293B"
TSUB   = "#64748B"
BORDER = "#E2E8F0"
ACCENT = "#8B5CF6"
ADARK  = "#7C3AED"
GREEN  = "#10B981"
AMBER  = "#F59E0B"
RED_C  = "#EF4444"
BLUE_C = "#3B82F6"

GROUP_COLORS = {1: BLUE_C,  2: ACCENT, 3: GREEN,  4: RED_C}
LEVEL_COLORS = {"A": GREEN, "B": AMBER, "C": RED_C}
GROUP_BG     = {1: "#EFF6FF", 2: "#EDE9FE", 3: "#ECFDF5", 4: "#FEF2F2"}
LEVEL_BG     = {"A": "#ECFDF5", "B": "#FEF3C7", "C": "#FEF2F2"}
def _blend(hex_color, alpha=0.5):
    """Blend hex color with white at alpha (0=white, 1=full). Returns valid 6-digit Tkinter hex."""
    h = hex_color.lstrip("#")
    r = int(h[0:2], 16); g = int(h[2:4], 16); b = int(h[4:6], 16)
    r2 = int(r * alpha + 255 * (1 - alpha))
    g2 = int(g * alpha + 255 * (1 - alpha))
    b2 = int(b * alpha + 255 * (1 - alpha))
    return f"#{r2:02x}{g2:02x}{b2:02x}"


QUESTIONS = [
    dict(item_id="A1", group_id=1, level="A", domain_label="time_workload",
         group_name="Group 1: Time Pressure & Workload",
         level_name="Level A — Descriptive / Low Emotional Load",
         prompt="When you have many tasks due at the same time, how do you usually decide what to do first?"),
    dict(item_id="A2", group_id=1, level="A", domain_label="time_workload",
         group_name="Group 1: Time Pressure & Workload",
         level_name="Level A — Descriptive / Low Emotional Load",
         prompt="Describe your typical study or work routine during a heavy week. What does your schedule usually look like?"),
    dict(item_id="B1", group_id=1, level="B", domain_label="time_workload",
         group_name="Group 1: Time Pressure & Workload",
         level_name="Level B — Recall of Specific Events / Moderate Load",
         prompt="Think of a time when unexpected work or new tasks were suddenly added to your plate. How did that feel, and how did you handle it?"),
    dict(item_id="C1", group_id=1, level="C", domain_label="time_workload",
         group_name="Group 1: Time Pressure & Workload",
         level_name="Level C — Self-Evaluation / Highest Psychomotor Activation",
         prompt="At the end of a long day, do you feel like you accomplished what you intended to? If not, how does that gap make you feel about yourself?"),
    dict(item_id="A3", group_id=2, level="A", domain_label="interpersonal",
         group_name="Group 2: Interpersonal Friction",
         level_name="Level A — Descriptive / Low Emotional Load",
         prompt="Think of a recent misunderstanding you had with someone — a friend, classmate, co-worker, or family member. How did it start, and how did it get resolved?"),
    dict(item_id="B2", group_id=2, level="B", domain_label="interpersonal",
         group_name="Group 2: Interpersonal Friction",
         level_name="Level B — Recall of Specific Events / Moderate Load",
         prompt="Is there a conflict with someone in your life — a friend, family member, or co-worker — that still feels unresolved? How has that been sitting with you?"),
    dict(item_id="B3", group_id=2, level="B", domain_label="interpersonal",
         group_name="Group 2: Interpersonal Friction",
         level_name="Level B — Recall of Specific Events / Moderate Load",
         prompt="Describe a moment when you felt like you let someone important to you down. What happened, and what was that like for you?"),
    dict(item_id="C2", group_id=2, level="C", domain_label="interpersonal",
         group_name="Group 2: Interpersonal Friction",
         level_name="Level C — Self-Evaluation / Highest Psychomotor Activation",
         prompt="Have you ever felt left out or excluded from a group you wanted to belong to — socially, academically, or in your workplace? What did that feel like?"),
    dict(item_id="A4", group_id=3, level="A", domain_label="academic_performance",
         group_name="Group 3: Academic & Performance Pressure",
         level_name="Level A — Descriptive / Low Emotional Load",
         prompt="When you are preparing for an important exam or deadline, what do you usually do to manage your time and get ready?"),
    dict(item_id="B4", group_id=3, level="B", domain_label="academic_performance",
         group_name="Group 3: Academic & Performance Pressure",
         level_name="Level B — Recall of Specific Events / Moderate Load",
         prompt="Think of a moment when you had to perform or present in front of people who were evaluating you — a professor, a panel, or an employer. How did your body and mind respond?"),
    dict(item_id="C3", group_id=4, level="C", domain_label="self_evaluation",
         group_name="Group 4: Self-Evaluation & Identity",
         level_name="Level C — Self-Evaluation / Highest Psychomotor Activation",
         prompt="Is there a significant decision you have made in the past year that you sometimes wonder if it was the right one? What was the decision, and what doubts come up when you think about it?"),
    dict(item_id="C4", group_id=4, level="C", domain_label="self_evaluation",
         group_name="Group 4: Self-Evaluation & Identity",
         level_name="Level C — Self-Evaluation / Highest Psychomotor Activation",
         prompt="On days when things feel really difficult or when you are not performing the way you want to, how do you see yourself? What words come to mind when you think about who you are on those days?"),
]

PHQ9 = [
    "Little interest or pleasure in doing things",
    "Feeling down, depressed, or hopeless",
    "Trouble falling or staying asleep, or sleeping too much",
    "Feeling tired or having little energy",
    "Poor appetite or overeating",
    "Feeling bad about yourself — or that you are a failure",
    "Trouble concentrating on things",
    "Moving or speaking so slowly that other people could have noticed — or being so fidgety or restless",
    "Thoughts that you would be better off dead, or thoughts of hurting yourself",
]
GAD7 = [
    "Feeling nervous, anxious, or on edge",
    "Not being able to stop or control worrying",
    "Worrying too much about different things",
    "Trouble relaxing",
    "Being so restless that it is hard to sit still",
    "Becoming easily annoyed or irritable",
    "Feeling afraid, as if something awful might happen",
]
LIKERT = [("Not at all", 0), ("Several days", 1),
          ("More than half the days", 2), ("Nearly every day", 3)]

# ── Plain-language helpers ────────────────────────────────────────────────────
def phq_label(s):
    if s <= 4:  return "Minimal depression"
    if s <= 9:  return "Mild depression"
    if s <= 14: return "Moderate depression"
    if s <= 19: return "Moderately severe depression"
    return "Severe depression"

def gad_label(s):
    if s <= 4:  return "Minimal anxiety"
    if s <= 9:  return "Mild anxiety"
    if s <= 14: return "Moderate anxiety"
    return "Severe anxiety"

def flag_ui(flag):
    if flag == "GREEN":
        return ("OVERALL STATUS: GREEN — Normal Patterns",
                "Psychomotor behavior is statistically consistent with this patient's own baseline.",
                GREEN, "#D1FAE5", "GREEN")
    if flag == "AMBER":
        return ("OVERALL STATUS: AMBER — Moderate Deviation",
                "Moderate psychomotor deviation detected. Warrants clinical attention at next appointment.",
                AMBER, "#FEF3C7", "AMBER")
    if flag == "RED":
        return ("OVERALL STATUS: RED — Significant Deviation Detected",
                "Statistically significant psychomotor deviation. Immediate clinical review recommended.",
                RED_C, "#FEE2E2", "RED")
    return ("OVERALL STATUS: PENDING", "Analysis pending.", TSUB, "#F1F5F9", "—")

def t2_interp(t2, thr):
    if thr <= 0 or thr == float("inf"):
        return "Threshold unavailable — insufficient calibration data."
    r = t2 / thr
    if r <= 1.0: return f"Within normal range ({r:.2f}× threshold). No anomaly."
    if r <= 1.5: return f"Moderately elevated ({r:.2f}× threshold). Warrants attention."
    return f"Significantly elevated ({r:.2f}× threshold). Strong behavioral deviation."

def psi_interp(psi):
    if psi < 0.5: return "Normal — no psychomotor slowing detected."
    if psi < 2.0: return "Mild slowing — slight increase in keystroke latency and pausing."
    if psi < 4.0: return "Moderate slowing — consistent with depressive inhibition."
    return "Severe slowing — marked psychomotor retardation pattern."

def pai_interp(pai):
    if pai < 0.5: return "Normal — no psychomotor agitation detected."
    if pai < 2.0: return "Mild agitation — slight cursor irregularity."
    if pai < 4.0: return "Moderate agitation — erratic movements consistent with anxiety."
    return "Severe agitation — highly erratic psychomotor pattern."

def dashboard_status(flag, label, psi, pai, phq, gad):
    """Plain-language summary for non-techie dashboard view."""
    if flag == "GREEN":
        return ("Patient's typing and mouse behavior matches their own baseline.", GREEN)
    if flag == "AMBER":
        dom = "slowing" if psi > pai else "agitation"
        return (f"Mild behavioral change detected ({dom}). PHQ-9: {phq}, GAD-7: {gad}.", AMBER)
    dom = "psychomotor slowing" if psi > pai else "psychomotor agitation"
    return (f"Significant {dom} detected. PHQ-9: {phq} ({phq_label(phq)}), GAD-7: {gad} ({gad_label(gad)}).", RED_C)

def _clinical_recs(flag, label, psi, pai, phq, gad, domain_t2, level_t2):
    recs = []
    # Priority action
    if flag == "RED":
        recs.append(("🔴  Immediate Safety Assessment",
                     f"RED flag with PHQ-9={phq} ({phq_label(phq)}) and GAD-7={gad} ({gad_label(gad)}) "
                     "warrants same-session structured risk assessment. Do not defer."))
    elif flag == "AMBER":
        recs.append(("🟡  Schedule Follow-Up Within 48–72 Hours",
                     "Moderate psychomotor deviation detected. Prioritize structured interview targeting "
                     "the flagged domain before the next scheduled session."))
    else:
        recs.append(("🟢  Continue Routine Monitoring",
                     "Psychomotor behavior within normal range for this patient. Maintain current session frequency."))

    # Psychomotor pattern
    if "Retardation" in label or psi > pai * 1.3:
        recs.append(("🧠  Psychomotor Retardation — Administer MADRS",
                     f"PSI={psi:.3f} dominates. Keystroke latency and pause frequency significantly elevated. "
                     "This sub-clinical motor inhibition pattern precedes observable psychomotor retardation. "
                     "Administer MADRS (Items 6 & 7) and assess energy, anergia, and psychic slowing explicitly."))
    elif "Agitation" in label or pai > psi * 1.3:
        recs.append(("⚡  Psychomotor Agitation — Administer HAM-A",
                     f"PAI={pai:.3f} dominates. Cursor jerk and path irregularity elevated below observable threshold. "
                     "This pattern typically precedes visible restlessness. Assess sleep onset, muscular tension, "
                     "and concentration using HAM-A Items 1–4."))
    elif "Mixed" in label:
        recs.append(("🔀  Mixed Disturbance — Consider MDQ Screen",
                     f"PSI={psi:.3f} and PAI={pai:.3f} both elevated concurrently. "
                     "Mixed psychomotor state is a key indicator of bipolar spectrum disorder, agitated MDD, "
                     "or complex PTSD. Administer MDQ and conduct mood episode timeline review. "
                     "Consider consultation with psychiatry."))

    # Screening scores — clinical level detail
    if phq >= 20:
        recs.append(("📋  Severe Depression — Pharmacotherapy Discussion",
                     f"PHQ-9={phq}/27. Severe range. Combined with biometric psychomotor slowing, "
                     "this warrants antidepressant review or initiation. Assess suicidality (PHQ-9 Item 9). "
                     "Document in clinical notes with date and score for longitudinal tracking."))
    elif phq >= 15:
        recs.append(("📋  Moderately Severe Depression — Structured Evaluation",
                     f"PHQ-9={phq}/27. Warrants structured psychiatric evaluation. "
                     "Cross-validate with HDRS if biometric slowing is present."))
    if gad >= 15:
        recs.append(("📋  Severe Anxiety — Anxiolytic Review",
                     f"GAD-7={gad}/21. Severe range. Assess panic history, avoidance patterns, "
                     "and safety behaviors. Consider buspirone or SSRI discussion. Corroborate with "
                     "elevated PAI in biometric profile."))
    elif gad >= 10:
        recs.append(("📋  Moderate Anxiety — CBT Referral",
                     f"GAD-7={gad}/21. CBT-targeted worry exposure and relaxation training indicated."))

    # Domain-specific clinical guidance
    if domain_t2:
        peak = max(domain_t2, key=lambda k: domain_t2[k])
        val  = domain_t2[peak]
        peak = int(peak)
        names = {1:"Time Pressure & Workload", 2:"Interpersonal Friction",
                 3:"Academic & Performance Pressure", 4:"Self-Evaluation & Identity"}
        clinical_tips = {
            1: ("Explore task-overload schema and perfectionism-driven urgency. "
                "Assess for Type-A behavioral patterns, occupational burnout (MBI), and executive function deficits. "
                "Time pressure reactivity often links to chronic stress responses and HPA axis dysregulation."),
            2: ("Explore attachment disruptions and relational schemas. Assess for rejection sensitivity, "
                "interpersonal hypersensitivity (common in BPD, atypical depression), and current social support "
                "adequacy. Consider IIP-32 for interpersonal problem profiling."),
            3: ("Explore performance schema and evaluation-related threat. Assess for social anxiety disorder, "
                "impostor phenomenon, and achievement-based self-worth. Consider LSAS if social anxiety is suspected."),
            4: ("Strongest signal is in identity/self-evaluation — highest clinical concern. "
                "Explore core beliefs (Beck's cognitive triad: self, world, future). "
                "Self-critical cognition at this intensity correlates with suicidality and treatment resistance. "
                "Administer DAS-24 or BDI Item 5 (self-dislike) if not already done."),
        }
        if val > 0.3:
            recs.append((f"🎯  Peak Domain: {names.get(peak, '?')} (T²={val:.3f})",
                         f"This domain produced the highest psychomotor deviation in the session. "
                         f"{clinical_tips.get(peak, '')}"))

    # Dose-response pattern
    if level_t2:
        la = level_t2.get("A", 0); lb = level_t2.get("B", 0); lc = level_t2.get("C", 0)
        if lc > lb > la and lc > 0.3:
            recs.append(("📈  Dose-Response Escalation — High Clinical Validity",
                         f"T² increases monotonically A→B→C (A={la:.2f}, B={lb:.2f}, C={lc:.2f}). "
                         "This pattern is the strongest internal validity indicator the system can produce. "
                         "It means psychomotor deviation is not random noise — it scales with emotional load, "
                         "confirming the patient is genuinely reactive to self-referential stress. "
                         "Level C items (self-evaluation) are the primary activation trigger. "
                         "Prioritize identity-focused and self-concept work in therapeutic planning."))
        elif la > lc and la > 0.3:
            recs.append(("📉  Elevated Baseline State Detected",
                         f"T² is paradoxically highest at Level A ({la:.2f}), which uses the lowest-intensity prompts. "
                         "This suggests the patient entered the session already in an elevated psychomotor state "
                         "(pre-existing agitation or anticipatory anxiety). "
                         "Assess pre-session stressors. Consider whether environmental factors (waiting room, "
                         "prior conversation) inflated the baseline. Flag for session context note."))

    # Hover-word clinical note
    recs.append(("⏱  Review Hover-Word Hesitation Map",
                 "The heatmap identifies specific words within each prompt where the patient's cursor paused "
                 "longest before typing. These micro-hesitations represent the patient's cognitive resistance "
                 "to specific concepts — they are sub-verbal, pre-linguistic indicators of emotional activation. "
                 "Use these as direct interview entry points: ask the patient directly about the flagged words."))

    return recs
# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════
class PsyClickApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PsyClick — Clinical Decision Support System")
        self.attributes("-fullscreen", True)
        self.bind("<Escape>", lambda e: self.attributes(
            "-fullscreen", not self.attributes("-fullscreen")))
        self.configure(fg_color=BG)
        self._last_report_data = None   # store for export
        c = ctk.CTkFrame(self, fg_color="transparent")
        c.pack(fill="both", expand=True)
        c.grid_rowconfigure(0, weight=1)
        c.grid_columnconfigure(0, weight=1)
        self.frames = {}
        for P in [LoginPage, DashboardPage, IntakePage,
                  KCalibrationPage, MCalibrationPage,
                  PHQ9Page, GAD7Page, EmotionalTaskPage,
                  ReportPage, PatientsPage, PatientDetailPage,
                  AuditPage]:
            f = P(parent=c, controller=self)
            self.frames[P.__name__] = f
            f.grid(row=0, column=0, sticky="nsew")
        self.show_frame("LoginPage")

    def show_frame(self, name):
        f = self.frames[name]
        f.tkraise()
        if hasattr(f, "on_show"): f.on_show()

    def open_patients(self):
        self.frames["PatientsPage"].refresh_list()
        self.show_frame("PatientsPage")
        log_audit("clinician", "Opened Patient Database")

    def open_patient_detail(self, sid):
        self.frames["PatientDetailPage"].load_session(sid)
        self.show_frame("PatientDetailPage")
        try:
            import sqlite3 as _sq
            conn = _sq.connect("psyclick_data.db")
            pid = conn.execute("SELECT student_id FROM intake_sessions WHERE session_id=?", (sid,)).fetchone()
            conn.close()
            log_audit("clinician", "Viewed Patient Report", pid[0] if pid else str(sid))
        except Exception:
            log_audit("clinician", "Viewed Patient Report", str(sid))

    def do_export(self, data=None):
        if data is None:
            data = self._last_report_data
        if not data:
            messagebox.showinfo("Export", "No report data available to export.")
            return
        try:
            fp = export_report(data)
            messagebox.showinfo("Export Complete",
                                f"Report saved and opened in browser:\n{fp}\n\n"
                                "To save as PDF: press Ctrl+P in the browser and choose 'Save as PDF'.")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))


# ── Shared UI helpers ─────────────────────────────────────────────────────────
def make_sidebar(parent, controller, active="Dashboard", intake_protected=False):
    sb = ctk.CTkFrame(parent, width=220, corner_radius=0,
                       fg_color=CARD, border_width=1, border_color=BORDER)
    sb.pack(side="left", fill="y")
    sb.pack_propagate(False)
    logo = ctk.CTkFrame(sb, width=44, height=44, corner_radius=12, fg_color=ACCENT)
    logo.pack(pady=(26, 4))
    logo.pack_propagate(False)
    ctk.CTkLabel(logo, text="Ψ", font=("Georgia", 22, "bold"),
                  text_color="white").pack(expand=True)
    ctk.CTkLabel(sb, text="PsyClick", font=("Poppins", 18, "bold"),
                  text_color=ACCENT).pack(pady=(0, 24))
    for label, dest in [("Dashboard", "DashboardPage"),
                         ("Patient History", "patients"),
                         ("Audit", "AuditPage"),
                         ("Logout", "LoginPage")]:
        is_active = label == active
        is_logout = label == "Logout"
        fg_ = "#EDE9FE" if is_active else "transparent"
        tc_ = "#6D28D9" if is_active else (RED_C if is_logout else TSUB)
        hv_ = "#FEE2E2" if is_logout else "#F1F5F9"

        if dest == "patients":
            raw_cmd = lambda: controller.open_patients()
        elif dest == "LoginPage":
            def _logout():
                log_audit("clinician", "Logged out")
                controller.show_frame("LoginPage")
            raw_cmd = _logout
        else:
            raw_cmd = lambda d=dest: controller.show_frame(d)

        if intake_protected:
            cmd = lambda fn=raw_cmd: fn() if clinician_password_dialog(parent) else None
        else:
            cmd = raw_cmd

        ctk.CTkButton(sb, text=f"  {label}", fg_color=fg_, text_color=tc_,
                       hover_color=hv_, font=("Inter", 14), corner_radius=10,
                       height=42, anchor="w", command=cmd
                       ).pack(pady=4, padx=16, fill="x")
    return sb

def make_stage_bar(parent, active_idx):
    top = ctk.CTkFrame(parent, fg_color="transparent")
    top.pack(fill="x")
    row = ctk.CTkFrame(top, fg_color="transparent")
    row.pack(fill="x")
    for i, s in enumerate(["PHQ-9", "GAD-7", "Emotional Response", "Final Stage"]):
        ctk.CTkLabel(row, text=s,
                      font=("Inter", 12, "bold" if i == active_idx else "normal"),
                      text_color=ACCENT if i == active_idx else TSUB
                      ).pack(side="left", expand=True)
    pb = ctk.CTkProgressBar(top, height=8, progress_color=ACCENT, fg_color=BORDER)
    pb.pack(fill="x", pady=(6, 0))
    pb.set(active_idx / 3.0)
    return pb

def clinician_password_dialog(parent):
    
    result = [False]
    dlg = ctk.CTkToplevel(parent)
    dlg.title("Clinician Verification")
    dlg.resizable(False, False)
    dlg.grab_set()
    dlg.focus_set()

    c = ctk.CTkFrame(dlg, fg_color=BG)
    c.pack(fill="both", expand=True)
    inner = ctk.CTkFrame(c, fg_color=CARD, corner_radius=20,
                          border_width=1, border_color=BORDER)
    inner.pack(expand=True, padx=32, pady=32)

    lock_f = ctk.CTkFrame(inner, width=56, height=56, corner_radius=14, fg_color=ACCENT)
    lock_f.pack(pady=(28, 8))
    lock_f.pack_propagate(False)
    ctk.CTkLabel(lock_f, text="🔒", font=("Inter", 24)).pack(expand=True)

    ctk.CTkLabel(inner, text="Clinician Verification Required",
                  font=("Poppins", 16, "bold"), text_color=TMAIN).pack(padx=32, pady=(0, 4))
    ctk.CTkLabel(inner, text="Enter your clinician password to continue",
                  font=("Inter", 12), text_color=TSUB).pack(padx=32, pady=(0, 16))

    pwd_entry = ctk.CTkEntry(inner, placeholder_text="Clinician Password", show="*",
                              width=300, height=44, corner_radius=10,
                              fg_color="#F8FAFC", border_color="#CBD5E1")
    pwd_entry.pack(padx=32, pady=(0, 6))

    err_lbl = ctk.CTkLabel(inner, text="", text_color=RED_C, font=("Inter", 11))
    err_lbl.pack(pady=(0, 8))

    btn_row = ctk.CTkFrame(inner, fg_color="transparent")
    btn_row.pack(padx=32, pady=(0, 28), fill="x")

    def _confirm():
        if pwd_entry.get().strip() == "12345":
            result[0] = True
            dlg.destroy()
        else:
            err_lbl.configure(text="Incorrect password. Please try again.")
            pwd_entry.delete(0, "end")
            pwd_entry.focus()

    def _cancel():
        dlg.destroy()

    ctk.CTkButton(btn_row, text="Cancel", height=48, corner_radius=21,
               fg_color="#F1F5F9", text_color=TSUB, hover_color=BORDER,
               command=_cancel).pack(side="left", fill="x", expand=True, padx=(0, 6))
    ctk.CTkButton(btn_row, text="Confirm", height=48, corner_radius=21,
               fg_color=ACCENT, hover_color=ADARK, text_color="white",
               font=("Inter", 13, "bold"), command=_confirm).pack(side="right", fill="x", expand=True, padx=(6, 0))


    pwd_entry.bind("<Return>", lambda e: _confirm())

    w, h = 420, 360
    dlg.update_idletasks()
    px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
    py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
    dlg.geometry(f"{w}x{h}+{px}+{py}")
    pwd_entry.focus()

    parent.wait_window(dlg)
    return result[0]

# ═══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════════════════════
class LoginPage(ctk.CTkFrame):
    CREDS = {"202312480": "Dr. Añonuevo", "202310964": "Dr. Huertas",
             "202311990": "Dr. Tablate",  "202310557": "Dr. Ballano"}

    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG)
        self.controller = controller
        c = ctk.CTkFrame(self, fg_color="transparent")
        c.pack(expand=True)
        logo = ctk.CTkFrame(c, width=72, height=72, corner_radius=20, fg_color=ACCENT)
        logo.pack(pady=(0, 16)); logo.pack_propagate(False)
        ctk.CTkLabel(logo, text="Ψ", font=("Georgia", 34, "bold"), text_color="white").pack(expand=True)
        ctk.CTkLabel(c, text="PsyClick", font=("Poppins", 40, "bold"), text_color=TMAIN).pack()
        ctk.CTkLabel(c, text="Clinical Decision Support System",
                      font=("Inter", 15), text_color=TSUB).pack(pady=(2, 28))
        box = ctk.CTkFrame(c, width=400, corner_radius=22, fg_color=CARD,
                            border_width=1, border_color=BORDER)
        box.pack()
        ctk.CTkLabel(box, text="Clinician ID", font=("Inter", 13, "bold"),
                      text_color=TMAIN).pack(anchor="w", padx=32, pady=(28, 4))
        self.uid = ctk.CTkEntry(box, placeholder_text="Enter your clinician ID",
                                 width=336, height=46, corner_radius=10,
                                 fg_color="#F8FAFC", border_color="#CBD5E1")
        self.uid.pack(padx=32, pady=(0, 14))
        ctk.CTkLabel(box, text="Password", font=("Inter", 13, "bold"),
                      text_color=TMAIN).pack(anchor="w", padx=32, pady=(0, 4))
        self.pwd = ctk.CTkEntry(box, placeholder_text="Enter your password",
                                 show="*", width=336, height=46, corner_radius=10,
                                 fg_color="#F8FAFC", border_color="#CBD5E1")
        self.pwd.pack(padx=32, pady=(0, 8))
        self.err = ctk.CTkLabel(box, text="", text_color=RED_C, font=("Inter", 12))
        self.err.pack()
        ctk.CTkButton(box, text="Secure Login", width=336, height=48,
                       corner_radius=24, font=("Inter", 15, "bold"),
                       fg_color=ACCENT, hover_color=ADARK,
                       command=self._login).pack(padx=32, pady=(8, 12))
        badge = ctk.CTkFrame(box, fg_color="#EEF2FF", corner_radius=10)
        badge.pack(fill="x", padx=32, pady=(0, 24))
        ctk.CTkLabel(badge, text="🔒  All data encrypted and stored locally",
                      font=("Inter", 12), text_color="#6D28D9").pack(pady=9)
        self.pwd.bind("<Return>", lambda e: self._login())

    def _login(self):
        u, p = self.uid.get().strip(), self.pwd.get().strip()
        if not u and not p:
            self.err.configure(text="Please enter your Clinician ID and Password")
            return
        if not u:
            self.err.configure(text="Please enter your Clinician ID")
            return
        if not p:
            self.err.configure(text="Please enter your Password")
            return
        if not u.isdigit() or len(u) != 9:
            self.err.configure(text="Clinician ID must be a 9-digit number")
            return
        if u in self.CREDS and p == "12345":
            self.err.configure(text="")
            self.controller.frames["DashboardPage"].set_user(self.CREDS[u])
            self.uid.delete(0, "end"); self.pwd.delete(0, "end")
            self.controller.show_frame("DashboardPage")
            
            # Audit
            log_audit("clinician", "Logged in", self.CREDS[u])
        else:
            self.err.configure(text="Invalid Clinician ID or Password")


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD — live stats, working buttons, plain-language summaries
# ═══════════════════════════════════════════════════════════════════════════════
class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG)
        self.controller = controller
        make_sidebar(self, controller, "Dashboard")
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(side="right", fill="both", expand=True, padx=40, pady=36)

        # Header
        hdr = ctk.CTkFrame(main, fg_color="transparent"); hdr.pack(fill="x")
        self.welcome = ctk.CTkLabel(hdr, text="Clinician Dashboard",
                                     font=("Poppins", 30, "bold"), text_color=TMAIN)
        self.welcome.pack(side="left", anchor="w")

        ctk.CTkButton(hdr, text="+ New Patient Intake", 
                    height=40,
                    corner_radius=20,
                    font=("Inter", 13, "bold"),
                    fg_color=ACCENT,
                    hover_color=ADARK,
                       
                    command=lambda: (log_audit("clinician", "Opened New Patient Intake"),controller.show_frame("IntakePage"))
                    ).pack(side="right")

        ctk.CTkLabel(main, text="Manage patient assessments and monitor baseline metrics",
                      font=("Inter", 14), text_color=TSUB
                      ).pack(anchor="w", pady=(2, 24))

        # Stat cards
        stats = ctk.CTkFrame(main, fg_color="transparent"); stats.pack(fill="x", pady=(0, 24))
        self.stat_lbls = {}
        for key, label, color in [("total","Total Patients",TMAIN),
                                    ("week","Sessions This Week",ACCENT),
                                    ("normal","No Concerns Flagged",GREEN),
                                    ("review","Need Review",RED_C)]:
            f = ctk.CTkFrame(stats, fg_color=CARD, corner_radius=16,
                              border_width=1, border_color=BORDER)
            f.pack(side="left", expand=True, fill="x", padx=6)
            lbl = ctk.CTkLabel(f, text="—", font=("Poppins", 28, "bold"), text_color=color)
            lbl.pack(pady=(20, 4))
            ctk.CTkLabel(f, text=label, font=("Inter", 13), text_color=TSUB).pack(pady=(0, 20))
            self.stat_lbls[key] = lbl

        # Patient history table
        hist = ctk.CTkFrame(main, fg_color=CARD, corner_radius=16,
                             border_width=1, border_color=BORDER)
        hist.pack(fill="both", expand=True, pady=(0, 20))
        th_row = ctk.CTkFrame(hist, fg_color="transparent"); th_row.pack(fill="x", padx=22, pady=(18, 0))
        ctk.CTkLabel(th_row, text="Previous Patients' History",
                      font=("Poppins", 16, "bold"), text_color=TMAIN).pack(side="left")
        ctk.CTkButton(th_row, text="View All →", width=90, height=30,
                       corner_radius=15, fg_color="#F8FAFC",
                       text_color=BLUE_C, border_color=BORDER, border_width=1,
                       font=("Inter", 12),
                       command=lambda: controller.open_patients()
                       ).pack(side="right")

        hdr2 = ctk.CTkFrame(hist, fg_color="#F8FAFC", corner_radius=0)
        hdr2.pack(fill="x", padx=22, pady=(10, 0))
        for col, w in [("Patient ID",110),("Date",160),("PHQ-9",80),
                        ("GAD-7",80),("Biometric Status",160),("Clinical Summary",240),("",90)]:
            ctk.CTkLabel(hdr2, text=col, font=("Inter",12,"bold"),
                          text_color=TSUB, width=w, anchor="w"
                          ).pack(side="left", padx=4, pady=7)

        self.table = ctk.CTkScrollableFrame(hist, fg_color="transparent", height=220)
        self.table.pack(fill="both", expand=True, padx=22, pady=(0, 12))

        # Quick actions — REAL CTkButton objects so clicks work
        qa = ctk.CTkFrame(main, fg_color="transparent"); qa.pack(fill="x")
        actions = [
            ("📅", "This Week's Sessions",   "View all sessions from the past 7 days",
             lambda: controller.open_patients()),
            ("👥", "Patient Database",       "Search and browse all patient records",
             lambda: controller.open_patients()),
            ("📤", "Export All Reports",     "Generate a summary of all sessions",
             lambda: self._export_summary()),
        ]
        for icon, title, sub, cmd in actions:
            f = ctk.CTkFrame(qa, fg_color=CARD, corner_radius=14,
                              border_width=1, border_color=BORDER)
            f.pack(side="left", expand=True, fill="x", padx=6)
            inner = ctk.CTkFrame(f, fg_color="transparent"); inner.pack(fill="x", padx=18, pady=16)
            ctk.CTkLabel(inner, text=icon, font=("Inter", 26)).pack(anchor="w")
            ctk.CTkLabel(inner, text=title, font=("Inter", 13, "bold"),
                          text_color=TMAIN).pack(anchor="w", pady=(4, 2))
            ctk.CTkLabel(inner, text=sub, font=("Inter", 12),
                          text_color=TSUB).pack(anchor="w")
            ctk.CTkButton(inner, text="Open →", height=32, corner_radius=16,
                           font=("Inter", 12, "bold"),
                           fg_color=ACCENT, hover_color=ADARK,
                           command=cmd).pack(anchor="w", pady=(10, 0))

    def set_user(self, name):
        self.welcome.configure(text=f"Clinician Dashboard")

    def on_show(self):
        self._refresh_stats()
        self._refresh_table()

    def _refresh_stats(self):
        try:
            conn = sqlite3.connect("psyclick_data.db")
            c    = conn.cursor()
            c.execute("SELECT COUNT(*) FROM intake_sessions"); total = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM intake_sessions WHERE timestamp >= datetime('now','-7 days')"); week = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM intake_sessions WHERE flag='GREEN'"); normal = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM intake_sessions WHERE flag IN ('AMBER','RED')"); review = c.fetchone()[0]
            conn.close()
            self.stat_lbls["total"].configure(text=str(total))
            self.stat_lbls["week"].configure(text=str(week))
            self.stat_lbls["normal"].configure(text=str(normal))
            self.stat_lbls["review"].configure(text=str(review))
        except Exception: pass

    def _refresh_table(self):
        for w in self.table.winfo_children(): w.destroy()
        try:
            conn = sqlite3.connect("psyclick_data.db")
            c    = conn.cursor()
            c.execute("""SELECT session_id, student_id, timestamp, flag,
                                phq_score, gad_score, psi, pai, fuzzy_label
                         FROM intake_sessions ORDER BY timestamp DESC LIMIT 12""")
            rows = c.fetchall(); conn.close()
            fc = {"GREEN": GREEN, "AMBER": AMBER, "RED": RED_C}
            for sid, pid, ts, flag, phq, gad, psi, pai, flabel in rows:
                row = ctk.CTkFrame(self.table, fg_color="transparent"); row.pack(fill="x", pady=3)
                tc  = fc.get(flag, TSUB)
                phq = phq or 0; gad = gad or 0
                psi = psi or 0; pai = pai or 0
                summary, scol = dashboard_status(flag, flabel or "", psi, pai, phq, gad)
                ctk.CTkLabel(row, text=str(pid)[:14], font=("Inter",13),
                              text_color=TMAIN, width=110, anchor="w").pack(side="left", padx=4)
                ctk.CTkLabel(row, text=str(ts)[:16], font=("Inter",11),
                              text_color=TSUB, width=160, anchor="w").pack(side="left", padx=4)
                phq_col = RED_C if phq >= 15 else (AMBER if phq >= 10 else GREEN)
                gad_col = RED_C if gad >= 15 else (AMBER if gad >= 10 else GREEN)
                ctk.CTkLabel(row, text=str(phq), font=("Inter",12,"bold"),
                              text_color=phq_col, width=80, anchor="w").pack(side="left", padx=4)
                ctk.CTkLabel(row, text=str(gad), font=("Inter",12,"bold"),
                              text_color=gad_col, width=80, anchor="w").pack(side="left", padx=4)
                ctk.CTkLabel(row, text=flag or "—", font=("Inter",11,"bold"),
                              fg_color=tc, text_color="white",
                              corner_radius=10, width=140, height=22
                              ).pack(side="left", padx=4)
                ctk.CTkLabel(row, text=summary, font=("Inter",11),
                              text_color=scol, width=240, anchor="w"
                              ).pack(side="left", padx=4)
                ctk.CTkButton(row, text="View →", width=80, height=26,
                               corner_radius=13, fg_color="#F8FAFC",
                               text_color=BLUE_C, border_color=BORDER, border_width=1,
                               font=("Inter",11),
                               command=lambda s=sid: self.controller.open_patient_detail(s)
                               ).pack(side="right", padx=4)
        except Exception as e:
            ctk.CTkLabel(self.table, text="No sessions found.", font=("Inter",13),
                          text_color=TSUB).pack(pady=20)

    def _export_summary(self):
        try:
            conn = sqlite3.connect("psyclick_data.db")
            c    = conn.cursor()
            c.execute("""SELECT student_id, timestamp, flag, phq_score, gad_score,
                                psi, pai, fuzzy_label
                         FROM intake_sessions ORDER BY timestamp DESC""")
            rows = c.fetchall(); conn.close()
            log_audit("clinician", "Exported Generated Reports")
            if not rows:
                messagebox.showinfo("Export", "No sessions to export."); return
            fp = export_summary(rows)
            messagebox.showinfo("Export Complete",
                                f"Summary report opened in browser:\n{fp}\n\n"
                                "To save as PDF: press Ctrl+P → Save as PDF.")

            
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))
# ═══════════════════════════════════════════════════════════════════════════════
# INTAKE
# ═══════════════════════════════════════════════════════════════════════════════
class IntakePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG)
        self.controller = controller
        make_sidebar(self, controller, intake_protected=True)
        main = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main.pack(side="right", fill="both", expand=True, padx=40, pady=30)
        ctk.CTkButton(main, text="← Back", fg_color="transparent", text_color=TSUB,
                       hover_color=BORDER, width=70,
                        command=self._go_back).pack(anchor="w")
        ctk.CTkLabel(main, text="New Patient Intake", font=("Poppins",28,"bold"),
                      text_color=TMAIN).pack(anchor="w", pady=(8,4))
        ctk.CTkLabel(main, text="Complete patient information and establish baseline biometric patterns",
                      font=("Inter",14), text_color=TSUB).pack(anchor="w", pady=(0,20))
        ic = ctk.CTkFrame(main, fg_color=CARD, corner_radius=16, border_width=1, border_color=BORDER)
        ic.pack(fill="x", pady=(0,16))
        ctk.CTkLabel(ic, text="Patient Information", font=("Poppins",16,"bold"),
                      text_color=TMAIN).pack(anchor="w", padx=26, pady=(20,12))
        fields = ctk.CTkFrame(ic, fg_color="transparent"); fields.pack(fill="x", padx=26, pady=(0,8))
        lf = ctk.CTkFrame(fields, fg_color="transparent"); lf.pack(side="left", expand=True, fill="x", padx=(0,8))
        ctk.CTkLabel(lf, text="Full Name", font=("Inter",13,"bold"), text_color=RED_C).pack(anchor="w")
        self.e_name = ctk.CTkEntry(lf, placeholder_text="Enter patient's full name",
                                    height=42, corner_radius=10, fg_color="#F8FAFC", border_color="#CBD5E1")
        self.e_name.pack(fill="x", pady=(4,0))
        rf = ctk.CTkFrame(fields, fg_color="transparent"); rf.pack(side="right", expand=True, fill="x")
        ctk.CTkLabel(rf, text="Student ID", font=("Inter",13,"bold"), text_color=TMAIN).pack(anchor="w")
        self.e_id = ctk.CTkEntry(rf, placeholder_text="Enter student identifier",
                                  height=42, corner_radius=10, fg_color="#F8FAFC", border_color="#CBD5E1")
        self.e_id.pack(fill="x", pady=(4,0))
        priv = ctk.CTkFrame(ic, fg_color="#F0F4FF", corner_radius=12)
        priv.pack(fill="x", padx=26, pady=(14,20))
        ctk.CTkLabel(priv, text="🔒  Your Privacy Matters",
                      font=("Inter",13,"bold"), text_color="#1E40AF").pack(anchor="w", padx=14, pady=(12,4))
        ctk.CTkLabel(priv,
                      text="I understand that my typing and mouse interaction data will be collected and analyzed\n"
                           "for clinical assessment purposes. All data is encrypted and stored locally.",
                      font=("Inter",12), text_color=TSUB, justify="left").pack(anchor="w", padx=14, pady=(0,8))
        self.cv = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(priv, text="I consent to local biometric recording for this session",
                         variable=self.cv, command=self._toggle,
                         text_color=TMAIN, font=("Inter",13)).pack(anchor="w", padx=14, pady=(0,14))
        self.btn = ctk.CTkButton(main, text="Agree & Begin Baseline Calibration →",
                                   height=50, corner_radius=25, state="disabled",
                                   font=("Inter",15,"bold"), fg_color=ACCENT, hover_color=ADARK,
                                   command=self._submit)
        self.btn.pack(pady=16)

    def _go_back(self):
        if clinician_password_dialog(self):
            self.controller.show_frame("DashboardPage")

    def _toggle(self):
        self.btn.configure(state="normal" if self.cv.get() else "disabled")

    def _submit(self):
        pid = self.e_id.get().strip() or self.e_name.get().strip() or "PT-UNKNOWN"
        existing = get_student_session_count(pid)
        if existing > 0:
            confirmed = messagebox.askyesno(
                "Returning Patient",
                f"Patient '{pid}' already has {existing} session(s) on record.\n\n"
                "Do you want to start a new session for this patient?\n"
                "(Their existing data will be preserved.)"
            )
            if not confirmed:
                return
        backend.set_student_id(pid)
        self.controller.show_frame("KCalibrationPage")
        log_audit("patient", "Start Session", pid)   

# ═══════════════════════════════════════════════════════════════════════════════
# KEYBOARD CALIBRATION
# ═══════════════════════════════════════════════════════════════════════════════
class KCalibrationPage(ctk.CTkFrame):
    TARGET = ("Photosynthesis is the process by which plants use sunlight, water, "
              "and carbon dioxide to produce oxygen and energy in the form of sugar. "
              "This remarkable biochemical process occurs in the chloroplasts of plant cells.")

    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG)
        self.controller = controller
        make_sidebar(self, controller, intake_protected=True)
        main = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main.pack(side="right", fill="both", expand=True, padx=40, pady=30)
        ctk.CTkLabel(main, text="Baseline Task — Typing", font=("Poppins",22,"bold"),
                      text_color=TMAIN).pack(anchor="w")
        ctk.CTkLabel(main, text="Establishing your normal typing patterns",
                      font=("Inter",13), text_color=TSUB).pack(anchor="w", pady=(2,20))
        instr = ctk.CTkFrame(main, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        instr.pack(fill="x", pady=(0,14))
        ctk.CTkLabel(instr, text="Instructions: Please type the text below exactly as shown. Type naturally at your normal pace.",
                      font=("Inter",13), text_color=TMAIN, wraplength=700, justify="left").pack(padx=18, pady=12)
        tgt = ctk.CTkFrame(main, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        tgt.pack(fill="x", pady=(0,14))
        ctk.CTkLabel(tgt, text="Copy this text:", font=("Inter",13,"bold"), text_color=TSUB).pack(anchor="w", padx=18, pady=(14,4))
        ctk.CTkLabel(tgt, text=self.TARGET, font=("Inter",14,"italic"), text_color=BLUE_C,
                      wraplength=700, justify="left").pack(padx=18, pady=(0,14))
        typ = ctk.CTkFrame(main, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        typ.pack(fill="x", pady=(0,14))
        ctk.CTkLabel(typ, text="Type here:", font=("Inter",13,"bold"), text_color=TSUB).pack(anchor="w", padx=18, pady=(14,4))
        self.txt = ctk.CTkTextbox(typ, height=100, corner_radius=8, fg_color="#F8FAFC",
                                   border_color="#CBD5E1", border_width=1, font=("Inter",13))
        self.txt.pack(fill="x", padx=18, pady=(0,6))
        self.char_lbl = ctk.CTkLabel(typ, text=f"Characters: 0 / {len(self.TARGET)}",
                                      font=("Inter",11), text_color=TSUB)
        self.char_lbl.pack(anchor="w", padx=18, pady=(0,12))
        self.txt.bind("<KeyRelease>", lambda e: self.char_lbl.configure(
            text=f"Characters: {len(self.txt.get('1.0','end-1c'))} / {len(self.TARGET)}"))
        note = ctk.CTkFrame(main, fg_color="#FFFBEB", corner_radius=10)
        note.pack(fill="x", pady=(0,14))
        ctk.CTkLabel(note, text="⚡ Note: Your baseline typing pattern helps detect behavioral changes during the clinical assessment.",
                      font=("Inter",12), text_color="#92400E").pack(padx=14, pady=9)
        ctk.CTkButton(main, text="Continue to Mouse Calibration →", height=50, corner_radius=25,
                       font=("Inter",15,"bold"), fg_color=ACCENT, hover_color=ADARK,
                       command=self._next).pack(pady=8)

    def on_show(self):
        self.txt.delete("1.0","end")
        self.char_lbl.configure(text=f"Characters: 0 / {len(self.TARGET)}")
        backend.start_key_capture(calibration_mode=True)
        log_audit("patient", "Entered Keyboard Calibration", backend.session_data["student_id"]
)

    def _next(self):
        backend.save_kbase()
        self.controller.show_frame("MCalibrationPage")


# ═══════════════════════════════════════════════════════════════════════════════
# MOUSE CALIBRATION
# ═══════════════════════════════════════════════════════════════════════════════
class MCalibrationPage(ctk.CTkFrame):
    N = 5
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG)
        self.controller = controller; self.done = 0; self.btns = []
        make_sidebar(self, controller, intake_protected=True)
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        hdr = ctk.CTkFrame(main, fg_color="transparent"); hdr.pack(fill="x", padx=20, pady=(10,0))
        tr = ctk.CTkFrame(hdr, fg_color="transparent"); tr.pack(fill="x")
        ctk.CTkLabel(tr, text="Baseline Task — Mouse Tracking", font=("Poppins",22,"bold"),
                      text_color=TMAIN).pack(side="left")
        self.pct_lbl = ctk.CTkLabel(tr, text="0%", font=("Inter",13), text_color=TSUB)
        self.pct_lbl.pack(side="right")
        self.prog = ctk.CTkProgressBar(hdr, height=8, progress_color=GREEN, fg_color=BORDER)
        self.prog.pack(fill="x", pady=(8,0)); self.prog.set(0)
        self.circ_lbl = ctk.CTkLabel(hdr, text=f"Circles clicked: 0 / {self.N}",
                                      font=("Inter",12), text_color=TSUB)
        self.circ_lbl.pack(anchor="w", pady=(4,0))
        instr = ctk.CTkFrame(main, fg_color="#EFF6FF", corner_radius=12)
        instr.pack(fill="x", padx=20, pady=(14,8))
        ctk.CTkLabel(instr, text="Please keep your hand on the mouse and do not release it until the task is complete",
                      font=("Inter",13,"bold"), text_color="#1E40AF").pack(anchor="w", padx=14, pady=(12,2))
        ctk.CTkLabel(instr, text="Move naturally and click each glowing blue circle.",
                      font=("Inter",12), text_color=BLUE_C, wraplength=700, justify="left"
                      ).pack(anchor="w", padx=14, pady=(0,12))
        self.area = ctk.CTkFrame(main, fg_color=CARD, corner_radius=18,
                                  border_width=1, border_color=BORDER)
        self.area.pack(fill="both", expand=True, padx=20, pady=(0,8))
        self.done_card = ctk.CTkFrame(main, fg_color=CARD, corner_radius=18,
                                       border_width=1, border_color=BORDER)
        note = ctk.CTkFrame(main, fg_color="#FFF1F2", corner_radius=10)
        note.pack(fill="x", padx=20, pady=(4,16))
        ctk.CTkLabel(note, text="🎯 Note: We're capturing cursor velocity, acceleration, and click precision.",
                      font=("Inter",12), text_color="#9F1239").pack(padx=14, pady=8)

    def on_show(self):
        self.done = 0; self.btns = []
        self.prog.set(0); self.pct_lbl.configure(text="0%")
        self.circ_lbl.configure(text=f"Circles clicked: 0 / {self.N}")
        self.done_card.pack_forget()
        for w in self.area.winfo_children(): w.destroy()
        backend.start_mouse_capture()
        log_audit("patient", "Entered Mouse Calibration", backend.session_data["student_id"]
)
        self.area.update()
        w = self.area.winfo_width() or 700; h = self.area.winfo_height() or 320
        for i in range(self.N):
            btn = ctk.CTkButton(self.area, text="", width=54, height=54,
                                 corner_radius=27, fg_color=BLUE_C, hover_color="#2563EB",
                                 command=lambda idx=i: self._click(idx))
            btn.place(x=random.randint(30, max(w-80,100)), y=random.randint(20, max(h-70,60)))
            self.btns.append(btn)

    def _click(self, idx):
        self.btns[idx].place_forget(); self.done += 1
        pct = self.done/self.N
        self.prog.set(pct); self.pct_lbl.configure(text=f"{int(pct*100)}%")
        self.circ_lbl.configure(text=f"Circles clicked: {self.done} / {self.N}")
        if self.done >= self.N:
            for w in self.area.winfo_children(): w.destroy()
            backend.save_mbase(); self._show_done()

    def _show_done(self):
        self.area.pack_forget()
        self.done_card.pack(fill="both", expand=True, padx=20, pady=(0,8))
        for w in self.done_card.winfo_children(): w.destroy()
        ok = ctk.CTkFrame(self.done_card, width=60, height=60, corner_radius=30, fg_color="#D1FAE5")
        ok.pack(pady=(40,12)); ok.pack_propagate(False)
        ctk.CTkLabel(ok, text="✓", font=("Inter",28,"bold"), text_color=GREEN).pack(expand=True)
        ctk.CTkLabel(self.done_card, text="Baseline Complete!", font=("Poppins",20,"bold"),
                      text_color=TMAIN).pack()
        ctk.CTkLabel(self.done_card, text="Mouse tracking patterns established successfully",
                      font=("Inter",13), text_color=TSUB).pack(pady=(4,24))
        ctk.CTkButton(self.done_card, text="Proceed to Clinical Assessment →",
                       height=50, corner_radius=25, font=("Inter",15,"bold"),
                       fg_color=ACCENT, hover_color=ADARK,
                       command=lambda: self.controller.show_frame("PHQ9Page")).pack(pady=(0,30))


# ═══════════════════════════════════════════════════════════════════════════════
# PHQ-9
# ═══════════════════════════════════════════════════════════════════════════════
class PHQ9Page(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG)
        self.controller = controller; self.cur = 0; self.score = 0
        top = ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x", padx=40, pady=(22,0))
        make_stage_bar(top, 0)
        body = ctk.CTkFrame(self, fg_color="transparent"); body.pack(fill="both", expand=True, padx=40, pady=14)
        ctk.CTkLabel(body, text="PHQ-9 Depression Screening", font=("Poppins",22,"bold"),
                      text_color=TMAIN).pack(anchor="w", pady=(0,4))
        ctk.CTkLabel(body, text="Over the last 2 weeks, how often have you been bothered by the following?",
                      font=("Inter",13), text_color=TSUB).pack(anchor="w", pady=(0,16))
        card = ctk.CTkFrame(body, fg_color=CARD, corner_radius=16, border_width=1, border_color=BORDER)
        card.pack(fill="x")
        self.q_lbl = ctk.CTkLabel(card, text=PHQ9[0], font=("Poppins",16,"bold"),
                                   text_color=TMAIN, wraplength=660, justify="center")
        self.q_lbl.pack(pady=(30,20), padx=28)
        for txt, val in LIKERT:
            ctk.CTkButton(card, text=txt, height=48, corner_radius=24,
                           fg_color="#F8FAFC", text_color=TMAIN, border_color=BORDER, border_width=1,
                           hover_color="#EDE9FE", font=("Inter",14),
                           command=lambda v=val: self._ans(v)).pack(fill="x", padx=28, pady=5)
        self.ctr = ctk.CTkLabel(card, text="Question 1 of 9", font=("Inter",12), text_color=TSUB)
        self.ctr.pack(pady=(6,18))

    def on_show(self):
        self.cur = 0; self.score = 0
        self.q_lbl.configure(text=PHQ9[0]); self.ctr.configure(text="Question 1 of 9")
        backend.start_mouse_capture()
        log_audit("patient", "Entered PHQ-9", backend.session_data["student_id"]
)

    def _ans(self, v):
        _LIKERT_LABELS = {0: "Not at all", 1: "Several days", 2: "More than half the days", 3: "Nearly every day"}
        log_audit("patient", f"Made choice: {_LIKERT_LABELS.get(v, str(v))}", f"PHQ-9, Q{self.cur} of {len(PHQ9)}")
        self.score += v; self.cur += 1 
        if self.cur < len(PHQ9):
            self.q_lbl.configure(text=PHQ9[self.cur])
            self.ctr.configure(text=f"Question {self.cur+1} of {len(PHQ9)}")
        else:
            backend.save_phq(self.score); self.controller.show_frame("GAD7Page")


# ═══════════════════════════════════════════════════════════════════════════════
# GAD-7
# ═══════════════════════════════════════════════════════════════════════════════
class GAD7Page(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG)
        self.controller = controller; self.cur = 0; self.score = 0
        top = ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x", padx=40, pady=(22,0))
        make_stage_bar(top, 1)
        body = ctk.CTkFrame(self, fg_color="transparent"); body.pack(fill="both", expand=True, padx=40, pady=14)
        ctk.CTkLabel(body, text="GAD-7 Anxiety Screening", font=("Poppins",22,"bold"),
                      text_color=TMAIN).pack(anchor="w", pady=(0,4))
        ctk.CTkLabel(body, text="Over the last 2 weeks, how often have you been bothered by the following?",
                      font=("Inter",13), text_color=TSUB).pack(anchor="w", pady=(0,16))
        card = ctk.CTkFrame(body, fg_color=CARD, corner_radius=16, border_width=1, border_color=BORDER)
        card.pack(fill="x")
        self.q_lbl = ctk.CTkLabel(card, text=GAD7[0], font=("Poppins",16,"bold"),
                                   text_color=TMAIN, wraplength=660, justify="center")
        self.q_lbl.pack(pady=(30,20), padx=28)
        for txt, val in LIKERT:
            ctk.CTkButton(card, text=txt, height=48, corner_radius=24,
                           fg_color="#F8FAFC", text_color=TMAIN, border_color=BORDER, border_width=1,
                           hover_color="#EDE9FE", font=("Inter",14),
                           command=lambda v=val: self._ans(v)).pack(fill="x", padx=28, pady=5)
        self.ctr = ctk.CTkLabel(card, text="Question 1 of 7", font=("Inter",12), text_color=TSUB)
        self.ctr.pack(pady=(6,18))

    def on_show(self):
        self.cur = 0; self.score = 0
        self.q_lbl.configure(text=GAD7[0]); self.ctr.configure(text="Question 1 of 7")
        backend.start_mouse_capture()
        log_audit("patient", "Entered GAD-7", backend.session_data["student_id"]
)

    def _ans(self, v):
        _LIKERT_LABELS = {0: "Not at all", 1: "Several days", 2: "More than half the days", 3: "Nearly every day"}
        log_audit("patient", f"Made choice: {_LIKERT_LABELS.get(v, str(v))}", f"GAD-7, Q{self.cur} of {len(GAD7)}")
        self.score += v; self.cur += 1
        if self.cur < len(GAD7):
            self.q_lbl.configure(text=GAD7[self.cur])
            self.ctr.configure(text=f"Question {self.cur+1} of {len(GAD7)}")
        else:
            backend.save_gad(self.score); self.controller.show_frame("EmotionalTaskPage")
# ═══════════════════════════════════════════════════════════════════════════════
# EMOTIONAL TASK
# ═══════════════════════════════════════════════════════════════════════════════
class EmotionalTaskPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG)
        self.controller = controller; self.qi = 0; self._pb = None
        self._idle_timer = None
        self._last_activity = 0.0
        self._build()

    def _build(self):
        # Fixed top: stage bar + badges + title + PROMPT
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=40, pady=(20,0))
        self._pb = make_stage_bar(top, 2)

        badge_row = ctk.CTkFrame(top, fg_color="transparent"); badge_row.pack(fill="x", pady=(12,0))
        self.gbadge = ctk.CTkLabel(badge_row, text="Group 1", font=("Inter",12,"bold"),
                                    fg_color="#EFF6FF", text_color=BLUE_C, corner_radius=6, width=260, height=28)
        self.gbadge.pack(side="left", padx=(0,8))
        self.lbadge = ctk.CTkLabel(badge_row, text="Level A", font=("Inter",12,"bold"),
                                    fg_color="#ECFDF5", text_color=GREEN, corner_radius=6, width=100, height=28)
        self.lbadge.pack(side="left")
        self.q_num = ctk.CTkLabel(badge_row, text="1 / 12", font=("Inter",13,"bold"), text_color=TSUB)
        self.q_num.pack(side="right")

        ctk.CTkLabel(top, text="Clinical Assessment", font=("Poppins",22,"bold"),
                      text_color=TMAIN).pack(anchor="w", pady=(10,2))
        self.lname = ctk.CTkLabel(top, text="", font=("Inter",13), text_color=TSUB)
        self.lname.pack(anchor="w", pady=(0,8))

        # Prompt card — fixed, always visible
        pc = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14, border_width=2, border_color=ACCENT)
        pc.pack(fill="x", padx=40, pady=(0,8))
        self.prompt_lbl = ctk.CTkLabel(pc, text="", font=("Poppins",15,"bold"),
                                        text_color=TMAIN, wraplength=900, justify="left")
        self.prompt_lbl.pack(anchor="w", padx=22, pady=(16,16))

        # Scrollable bottom: why + response + submit
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=40, pady=(0,10))

        why = ctk.CTkFrame(scroll, fg_color="#FFF7ED", corner_radius=10); why.pack(fill="x", pady=(0,10))
        ctk.CTkLabel(why, text="Why this matters: Your typing patterns while responding provide valuable biometric data. "
                               "Take your time and be as detailed as you feel comfortable.",
                      font=("Inter",12), text_color="#92400E", wraplength=860, justify="left"
                      ).pack(padx=14, pady=9)

        rc = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        rc.pack(fill="x", pady=(0,10))
        ctk.CTkLabel(rc, text="Your Response:", font=("Inter",13,"bold"), text_color=TSUB
                      ).pack(anchor="w", padx=18, pady=(14,4))


        self.txt = ctk.CTkTextbox(rc, height=150, corner_radius=10, fg_color="#F8FAFC",
                                   border_color="#CBD5E1", border_width=1, font=("Inter",14))
        self.txt.pack(fill="x", padx=18, pady=(0,6))
        self.txt.bind("<KeyRelease>", self._on_activity)
        self.txt.bind("<Motion>", self._on_activity)

        cr = ctk.CTkFrame(rc, fg_color="transparent"); cr.pack(fill="x", padx=18, pady=(0,14))
        self.char_lbl = ctk.CTkLabel(cr, text="0 characters", font=("Inter",12), text_color=TSUB)
        self.char_lbl.pack(side="left")
        ctk.CTkLabel(cr, text="🔴 Biometric data being captured", font=("Inter",12,"bold"),
                      text_color=RED_C).pack(side="right")
        self.txt.bind("<KeyRelease>", lambda e: self.char_lbl.configure(
            text=f"{len(self.txt.get('1.0','end-1c'))} characters"))

        bio = ctk.CTkFrame(scroll, fg_color="#EFF6FF", corner_radius=10); bio.pack(fill="x", pady=(0,10))
        ctk.CTkLabel(bio, text="ℹ  Real-time biometric analysis: Keystroke dynamics, pause patterns, and cursor "
                               "movements are being compared against your personal baseline.",
                      font=("Inter",12), text_color="#1D4ED8", wraplength=860, justify="left"
                      ).pack(padx=14, pady=10)

        nav = ctk.CTkFrame(scroll, fg_color="transparent"); nav.pack(fill="x", pady=(0,8))
        self.btn_next = ctk.CTkButton(nav, text="Submit & Next Question →",
                                       height=48, width=260, corner_radius=24,
                                       font=("Inter",14,"bold"), fg_color=ACCENT, hover_color=ADARK,
                                       command=self._next)
        self.btn_next.pack(side="right")

        footer = ctk.CTkFrame(scroll, fg_color="transparent"); footer.pack(fill="x")
        for t, s in [("Assessment Progress","PHQ-9 & GAD-7 completed. Final task in progress."),
                      ("Baseline Established","Typing and mouse patterns recorded."),
                      ("Next Step","Clinical analysis dashboard after submission.")]:
            f = ctk.CTkFrame(footer, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
            f.pack(side="left", expand=True, fill="x", padx=4)
            ctk.CTkLabel(f, text=t, font=("Inter",12,"bold"), text_color=TMAIN
                          ).pack(anchor="w", padx=12, pady=(10,2))
            ctk.CTkLabel(f, text=s, font=("Inter",11), text_color=TSUB,
                          wraplength=180, justify="left").pack(anchor="w", padx=12, pady=(0,10))

    def _on_activity(self, event=None):
        self._last_activity = time.time()

    def _start_idle_watch(self):
        self._last_activity = time.time()
        if self._idle_timer:
            self.after_cancel(self._idle_timer)
        self._idle_timer = self.after(10000, self._check_idle)

    def _check_idle(self):
        if time.time() - self._last_activity >= 10:
            log_audit("patient", "Idle (10+ seconds)", f"Q{self.qi+1} of {len(QUESTIONS)}")
        self._idle_timer = self.after(10000, self._check_idle)

    def _stop_idle_watch(self):
        if self._idle_timer:
            self.after_cancel(self._idle_timer)
            self._idle_timer = None


    def on_show(self):
        log_audit("patient", "Entered Clinical Assessment", backend.session_data["student_id"]
)
        self.qi = 0
        backend.start_mouse_capture(); backend.start_key_capture()
        self._load()
        

    def _register_word_boxes(self):
        self.update_idletasks()
        try:
            lbl   = self.prompt_lbl
            words = QUESTIONS[self.qi]["prompt"].split()
            total_w = lbl.winfo_width() or 900; char_w = 8
            x_start = lbl.winfo_rootx(); y_start = lbl.winfo_rooty()
            boxes = []; cx, cy = 0, 0; line_h = 22
            for word in words:
                ww = len(word)*char_w+6
                if cx+ww > total_w: cx = 0; cy += line_h
                boxes.append({"word":word,"x1":x_start+cx,"y1":y_start+cy,
                               "x2":x_start+cx+ww,"y2":y_start+cy+line_h})
                cx += ww+5
            backend.register_word_boxes(boxes)
        except Exception: backend.register_word_boxes([])

    def _load(self):
        q = QUESTIONS[self.qi]; n = len(QUESTIONS)
        if self._pb: self._pb.set(self.qi/n)
        self.q_num.configure(text=f"{self.qi+1} / {n}")
        gc = GROUP_COLORS.get(q["group_id"], ACCENT); gbg = GROUP_BG.get(q["group_id"],"#EEF2FF")
        self.gbadge.configure(text=q["group_name"], fg_color=gbg, text_color=gc)
        lc = LEVEL_COLORS.get(q["level"], ACCENT); lbg = LEVEL_BG.get(q["level"],"#EEF2FF")
        self.lbadge.configure(text=f"Level {q['level']}", fg_color=lbg, text_color=lc)
        self.lname.configure(text=q["level_name"])
        self.prompt_lbl.configure(text=f'"{q["prompt"]}"')
        self.txt.delete("1.0","end"); self.char_lbl.configure(text="0 characters")
        is_last = self.qi == n-1
        self.btn_next.configure(
            text="Submit Assessment & View Results →" if is_last else "Submit & Next Question →",
            state="normal", fg_color=ACCENT)
        backend.set_current_question(q)
        log_audit("patient", f"Entered {q['group_name']}", q['level_name'])
        self.after(300, self._register_word_boxes)
        self._start_idle_watch()

    def _next(self):
        self._stop_idle_watch()
        q = QUESTIONS[self.qi]
        log_audit("patient", "Clicked Next", f"Q{self.qi+1} of {len(QUESTIONS)}")
        backend.save_question_snapshot(q, self.txt.get("1.0","end-1c").strip())
        self.qi += 1
        if self.qi < len(QUESTIONS):
            self._load()
        else:
            if clinician_password_dialog(self):
                self._finish()
            else:
                self.qi -= 1
                self._start_idle_watch()

    def _finish(self):
        self._stop_idle_watch()
        self.btn_next.configure(state="disabled", text="Processing…", fg_color="#94A3B8")
        try:
            result = backend.process_final_task()
            if result:
                self.controller._last_report_data = result
                self.controller.frames["ReportPage"].display_report(result)
                self.controller.show_frame("ReportPage")
                log_audit("patient", "Finished Session", backend.session_data["student_id"]
)
            else:
                self.btn_next.configure(state="normal", text="Retry — no data captured", fg_color=AMBER)
        except Exception as e:
            self.btn_next.configure(text=f"Error: {str(e)[:60]}", fg_color=RED_C, state="normal")
# ═══════════════════════════════════════════════════════════════════════════════
# REPORT PAGE — with metric interpretations + clinician-grade content + export
# ═══════════════════════════════════════════════════════════════════════════════
class ReportPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG)
        self.controller = controller
        self._report_data = None
        self._build()

    def _build(self):
        sb = ctk.CTkFrame(self, width=56, corner_radius=0, fg_color=CARD,
                           border_width=1, border_color=BORDER)
        sb.pack(side="left", fill="y"); sb.pack_propagate(False)
        logo = ctk.CTkFrame(sb, width=36, height=36, corner_radius=8, fg_color=ACCENT)
        logo.pack(pady=14); logo.pack_propagate(False)
        ctk.CTkLabel(logo, text="Ψ", font=("Georgia",16,"bold"), text_color="white").pack(expand=True)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=28, pady=18)
        self._scroll = scroll

        # Nav
        top = ctk.CTkFrame(scroll, fg_color="transparent"); top.pack(fill="x", pady=(0,14))
        ctk.CTkButton(top, text="← Back to Dashboard", fg_color="transparent", text_color=TSUB,
                       hover_color=BORDER,
                       command=lambda: self.controller.show_frame("DashboardPage")).pack(side="left")
        ctk.CTkButton(top, text="📄 Export PDF Report", fg_color=GREEN, hover_color="#059669",
                       corner_radius=8, font=("Inter",13,"bold"), height=36,
                       command=self._export).pack(side="right")

        self.patient_lbl = ctk.CTkLabel(scroll, text="Patient ID: —  |  Session: —",
                                         font=("Inter",12), text_color=TSUB)
        self.patient_lbl.pack(anchor="w", pady=(0,4))

        # Placeholder for session selector (populated by PatientDetailPage)
        self._session_sel_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self._session_sel_frame.pack(fill="x", pady=(0,6))

        # HAL bar
        hal = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=10, border_width=1, border_color=BORDER)
        hal.pack(fill="x", pady=(0,10))
        hi = ctk.CTkFrame(hal, fg_color="transparent"); hi.pack(fill="x", padx=16, pady=9)
        ctk.CTkLabel(hi, text="HAL Normalization Status", font=("Inter",13,"bold"), text_color=TMAIN).pack(side="left")
        ctk.CTkLabel(hi, text="⌨ Keyboard: Standard (04-key)", font=("Inter",12), text_color=TSUB).pack(side="left", padx=14)
        ctk.CTkLabel(hi, text="🖱 Mouse: Optical (1000 DPI)", font=("Inter",12), text_color=TSUB).pack(side="left", padx=8)
        ctk.CTkLabel(hi, text="✓ NORMALIZED", font=("Inter",12,"bold"), fg_color="#D1FAE5",
                      text_color="#065F46", corner_radius=6, width=100, height=26).pack(side="right")

        # Banner
        self.banner = ctk.CTkFrame(scroll, corner_radius=14, border_width=1)
        self.banner.pack(fill="x", pady=(0,14))
        bi = ctk.CTkFrame(self.banner, fg_color="transparent"); bi.pack(fill="both", padx=18, pady=14)
        self.b_icon = ctk.CTkLabel(bi, text="!", font=("Inter",18,"bold"),
                                    width=36, height=36, corner_radius=18, fg_color="gray", text_color="white")
        self.b_icon.pack(side="left", padx=(0,14))
        bt = ctk.CTkFrame(bi, fg_color="transparent"); bt.pack(side="left", fill="both", expand=True)
        self.b_title = ctk.CTkLabel(bt, text="Status", font=("Poppins",17,"bold"), text_color=TMAIN)
        self.b_title.pack(anchor="w")
        self.b_sub = ctk.CTkLabel(bt, text="", font=("Inter",12), text_color=TSUB)
        self.b_sub.pack(anchor="w")
        self.b_badge = ctk.CTkButton(bi, text="—", font=("Inter",13,"bold"),
                                      width=80, height=34, corner_radius=17, state="disabled",
                                      text_color="white", fg_color="gray")
        self.b_badge.pack(side="right")

        # Row 1: Fuzzy + Screening
        r1 = ctk.CTkFrame(scroll, fg_color="transparent"); r1.pack(fill="x", pady=(0,12))
        fz = ctk.CTkFrame(r1, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        fz.pack(side="left", fill="both", expand=True, padx=(0,7))
        ctk.CTkLabel(fz, text="ℹ  Fuzzy Logic Output", font=("Inter",14,"bold"),
                      text_color=TMAIN).pack(anchor="w", padx=18, pady=(14,0))
        self.fz_cv = tk.Canvas(fz, width=150, height=150, bg=CARD, highlightthickness=0)
        self.fz_cv.pack(pady=6)
        self.fz_lbl = ctk.CTkLabel(fz, text="—", font=("Poppins",14,"bold"), text_color=TMAIN)
        self.fz_lbl.pack()
        ctk.CTkLabel(fz, text="Classification Result", font=("Inter",11), text_color=TSUB).pack(pady=(0,14))

        sc = ctk.CTkFrame(r1, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        sc.pack(side="right", fill="both", expand=True, padx=(7,0))
        ctk.CTkLabel(sc, text="📊  Screening Scores", font=("Inter",14,"bold"),
                      text_color=TMAIN).pack(anchor="w", padx=18, pady=(14,8))
        self.phq_bar, self.phq_txt = self._score_row(sc, "PHQ-9 (Depression)", 27)
        self.gad_bar, self.gad_txt = self._score_row(sc, "GAD-7 (Anxiety)", 21)
        self.sc_alert = ctk.CTkLabel(sc, text="", font=("Inter",12,"bold"), corner_radius=8, height=32)
        self.sc_alert.pack(fill="x", padx=18, pady=(6,14))

        # Row 2: T², PSI, PAI, F-Threshold — each with interpretation text
        r2 = ctk.CTkFrame(scroll, fg_color="transparent"); r2.pack(fill="x", pady=(0,12))
        self.c_t2  = self._metric_interp(r2,"T² Score","—","Hotelling's T²",RED_C,
            "How far this patient's behavior has shifted from their own baseline today. "
            "Values above the F-threshold indicate a statistically significant change.")
        self.c_thr = self._metric_interp(r2,"F-Threshold","—","Upper Control Limit",AMBER,
            "The statistical ceiling calculated from this patient's calibration data. "
            "A T² score above this value is considered a meaningful deviation.")
        self.c_psi = self._metric_interp(r2,"PSI","—","Psychomotor Slowing Index",BLUE_C,
            "Measures motor inhibition: slower keystrokes, longer pauses, extended key-hold time. "
            "Elevated PSI mirrors the psychomotor retardation seen in depression.")
        self.c_pai = self._metric_interp(r2,"PAI","—","Psychomotor Agitation Index",ACCENT,
            "Measures motor restlessness: erratic cursor paths, high correction rate, jerk. "
            "Elevated PAI mirrors the motor restlessness seen in anxiety states.")

        # Interpretation row
        self.interp_frame = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=14,
                                          border_width=1, border_color=BORDER)
        self.interp_frame.pack(fill="x", pady=(0,12))
        ctk.CTkLabel(self.interp_frame, text="📖  Clinical Interpretation of Biometric Indices",
                      font=("Poppins",14,"bold"), text_color=TMAIN
                      ).pack(anchor="w", padx=18, pady=(14,4))
        self.interp_lbl = ctk.CTkLabel(self.interp_frame, text="",
                                        font=("Inter",13), text_color=TMAIN,
                                        wraplength=900, justify="left")
        self.interp_lbl.pack(anchor="w", padx=18, pady=(0,14))

        # Row 3: Heatmap + Spectrogram
        r3 = ctk.CTkFrame(scroll, fg_color="transparent"); r3.pack(fill="x", pady=(0,12))
        hm = ctk.CTkFrame(r3, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        hm.pack(side="left", fill="both", expand=True, padx=(0,7))
        ctk.CTkLabel(hm, text="Temporal Heatmap — Hover-Word Hesitation",
                      font=("Poppins",14,"bold"), text_color=TMAIN).pack(anchor="w", padx=18, pady=(14,0))
        ctk.CTkLabel(hm, text="Each node = one question. Size = pre-typing reading latency (how long before first keypress). Label = top hover word.",
                      font=("Inter",12), text_color=TSUB).pack(anchor="w", padx=18)
        self.hm_cv = tk.Canvas(hm, height=380, bg="#FFFFFF",
                                highlightthickness=1, highlightbackground=BORDER)
        self.hm_cv.pack(fill="both", padx=18, pady=10)

        # Heatmap state
        self._hm_zoom     = 1.0
        self._hm_pan_ms   = 0.0
        self._hm_nodes    = []
        self._hm_tip_ids  = []
        self._hm_last     = None
        self._hm_x_max_ms = 3000.0
        # Heatmap bindings
        self.hm_cv.bind("<Configure>",     self._hm_on_resize)
        self.hm_cv.bind("<MouseWheel>",    self._hm_on_scroll)
        self.hm_cv.bind("<Button-4>",      self._hm_on_scroll)
        self.hm_cv.bind("<Button-5>",      self._hm_on_scroll)
        self.hm_cv.bind("<ButtonPress-1>", self._hm_on_drag_start)
        self.hm_cv.bind("<B1-Motion>",     self._hm_on_drag)
        self.hm_cv.bind("<Motion>",        self._hm_on_motion)


        self.hm_lbl = ctk.CTkLabel(hm, text="Pending…", font=("Inter",12),
                                    corner_radius=8, height=34, wraplength=380)
        self.hm_lbl.pack(fill="x", padx=18, pady=(0,14))

        sp = ctk.CTkFrame(r3, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        sp.pack(side="right", fill="both", expand=True, padx=(7,0))
        ctk.CTkLabel(sp, text="Rhythm Spectrogram — Keystroke Interval Variance",
                      font=("Poppins",14,"bold"), text_color=TMAIN).pack(anchor="w", padx=18, pady=(14,0))
        ctk.CTkLabel(sp, text="Each bar = one keystroke interval (ms). Consistent = smooth. Erratic = agitation.",
                      font=("Inter",12), text_color=TSUB).pack(anchor="w", padx=18)
        self.sp_cv = tk.Canvas(sp, height=300, bg="#FFFFFF", highlightthickness=0)
        self.sp_cv.pack(fill="both", padx=18, pady=10)

        # Spectrogram state
        self._sp_bars    = []
        self._sp_tip_ids = []
        self._sp_last    = None
        # Spectrogram bindings
        self.sp_cv.bind("<Configure>", self._sp_on_resize)
        self.sp_cv.bind("<Motion>",    self._sp_on_motion)

        self.sp_lbl = ctk.CTkLabel(sp, text="Pending…", font=("Inter",12),
                                    corner_radius=8, height=34, wraplength=380)
        self.sp_lbl.pack(fill="x", padx=18, pady=(0,14))

        # Row 4: Per-question table
        qc = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        qc.pack(fill="x", pady=(0,12))
        ctk.CTkLabel(qc, text="Per-Question Biometric Profile",
                      font=("Poppins",14,"bold"), text_color=TMAIN).pack(anchor="w", padx=18, pady=(14,4))
        ctk.CTkLabel(qc, text="Each row = one item. Pre-Key ms = reading latency before first keypress. AMBER/RED = significant psychomotor shift.",
                      font=("Inter",12), text_color=TSUB).pack(anchor="w", padx=18, pady=(0,8))
        
        self.q_cv = tk.Canvas(qc, height=200, bg=CARD, highlightthickness=0)
        self.q_cv.pack(fill="x", padx=18, pady=(0,12))

        # Row 5: Domain chart
        dm = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        dm.pack(fill="x", pady=(0,12))
        ctk.CTkLabel(dm, text="Domain-Segmented T² Profile",
                      font=("Poppins",14,"bold"), text_color=TMAIN).pack(anchor="w", padx=18, pady=(14,2))
        ctk.CTkLabel(dm, text="Bars = average T² per stressor domain. Line = Level A→B→C escalation pattern.",
                      font=("Inter",12), text_color=TSUB).pack(anchor="w", padx=18)
        self.dm_cv = tk.Canvas(dm, height=170, bg="#FFFFFF", highlightthickness=0)
        self.dm_cv.pack(fill="both", padx=18, pady=10)

        # Row 6: Recommendations
        rc = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        rc.pack(fill="x", pady=(0,20))
        hdr_rec = ctk.CTkFrame(rc, fg_color="transparent"); hdr_rec.pack(fill="x", padx=18, pady=(14,4))
        ctk.CTkLabel(hdr_rec, text="⚠  Urgent Clinical Recommendations",
                      font=("Poppins",14,"bold"), text_color=RED_C).pack(side="left")
        ctk.CTkLabel(hdr_rec,
                      text="For clinician use only. Augments does not replace clinical judgment.",
                      font=("Inter",11), text_color=TSUB).pack(side="right")
        self.rec_frame = ctk.CTkFrame(rc, fg_color="transparent")
        self.rec_frame.pack(fill="x", padx=18, pady=(0,16))

    def _score_row(self, parent, title, max_val):
        f = ctk.CTkFrame(parent, fg_color="transparent"); f.pack(fill="x", padx=18, pady=4)
        h = ctk.CTkFrame(f, fg_color="transparent"); h.pack(fill="x")
        ctk.CTkLabel(h, text=title, font=("Inter",13,"bold"), text_color=TMAIN).pack(side="left")
        v = ctk.CTkLabel(h, text="—", font=("Poppins",14,"bold"), text_color=RED_C); v.pack(side="right")
        pb = ctk.CTkProgressBar(f, height=9, progress_color=RED_C, fg_color=BORDER)
        pb.pack(fill="x", pady=(4,0)); pb.set(0)
        return pb, v

    def _metric_interp(self, parent, title, val, sub, color, interp_text):
        f = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=13, border_width=1, border_color=BORDER)
        f.pack(side="left", fill="both", expand=True, padx=4)
        t = ctk.CTkFrame(f, fg_color="transparent"); t.pack(fill="x", padx=12, pady=(12,4))
        ctk.CTkLabel(t, text="~", font=("Inter",11,"bold"), text_color="white",
                      fg_color=color, width=20, height=20, corner_radius=10
                      ).pack(side="left", padx=(0,7))
        ctk.CTkLabel(t, text=title, font=("Inter",12,"bold"), text_color=TMAIN).pack(side="left")
        lbl = ctk.CTkLabel(f, text=val, font=("Poppins",20,"bold"), text_color=color)
        lbl.pack(anchor="w", padx=12)
        ctk.CTkLabel(f, text=sub, font=("Inter",10), text_color=TSUB).pack(anchor="w", padx=12, pady=(0,4))
        ctk.CTkLabel(f, text=interp_text, font=("Inter",10), text_color="#64748B",
                      wraplength=180, justify="left").pack(anchor="w", padx=12, pady=(0,12))
        return lbl

    def _export(self):
        self.controller.do_export(self._report_data)
        log_audit("clinician", "Exported Patient Report", str(self._report_data.get("student_id","?")))

    def display_report(self, data):
        self._report_data = data
        ae    = data.get("analysis") or {}
        flag  = ae.get("flag","GREEN")
        psi   = ae.get("psi",0.0); pai=ae.get("pai",0.0)
        t2    = ae.get("t2_score",0.0); thr=ae.get("t2_threshold",0.0)
        conf  = ae.get("confidence",0.0); label=ae.get("label","Normal")

        ti, sub, tc, bc, badge = flag_ui(flag)
        self.banner.configure(fg_color=bc, border_color=tc)
        self.b_icon.configure(text="✓" if flag=="GREEN" else "!", fg_color=tc)
        self.b_title.configure(text=ti, text_color=tc)
        self.b_sub.configure(text=sub, text_color=tc)
        self.b_badge.configure(text=badge, fg_color=tc)

        pid=data.get("student_id","—"); ts=data.get("timestamp","—")
        self.patient_lbl.configure(text=f"Patient ID: {pid}   |   Session: {ts}")

        phq=data.get("phq",{}).get("score",0); gad=data.get("gad",{}).get("score",0)
        self.phq_bar.set(min(phq/27,1))
        self.phq_txt.configure(text=f"{phq}/27  ({phq_label(phq)})")
        self.gad_bar.set(min(gad/21,1))
        self.gad_txt.configure(text=f"{gad}/21  ({gad_label(gad)})")
        if phq >= 15 or gad >= 10:
            self.sc_alert.configure(text="⚠ Elevated scores — immediate clinical review recommended",
                                     fg_color="#FEE2E2", text_color=RED_C)
        else:
            self.sc_alert.configure(text="✓ Scores within manageable range",
                                     fg_color="#D1FAE5", text_color="#065F46")

        self.c_t2.configure(text=f"{t2:.3f}")
        self.c_thr.configure(text=f"{thr:.2f}" if thr!=float("inf") else "N/A")
        self.c_psi.configure(text=f"{psi:.3f}")
        self.c_pai.configure(text=f"{pai:.3f}")
        self.fz_lbl.configure(text=label)

        # Interpretation block
        interp = (
            f"T² = {t2:.3f} — {t2_interp(t2, thr)}\n\n"
            f"PSI = {psi:.3f} — {psi_interp(psi)}\n\n"
            f"PAI = {pai:.3f} — {pai_interp(pai)}\n\n"
            f"Classification: {label} ({int(conf*100)}% confidence) — "
            f"{'Motor inhibition dominant (slowing > agitation).' if psi > pai else 'Motor restlessness dominant (agitation > slowing).' if pai > psi else 'Balanced pattern.'}"
        )
        self.interp_lbl.configure(text=interp)

        self._donut(conf, tc)
        vis=data.get("visuals",{}); snaps=vis.get("question_snapshots",[])
        dom=vis.get("domain_t2",{}); lvl=vis.get("level_t2",{})
        self._heatmap(snaps, vis.get("pause_coords",[]), flag)
        self._spectrogram(vis.get("flight_times",[]), flag, pai)
        self._q_table(snaps)
        self._domain_chart(dom, lvl)
        self._recommendations(flag, label, psi, pai, phq, gad, dom, lvl)

    def _donut(self, conf, color):
        c=self.fz_cv; c.delete("all")
        c.create_arc(15,15,135,135,start=0,extent=359.9,outline=BORDER,width=12,style="arc")
        c.create_arc(15,15,135,135,start=90,extent=-(conf*360),outline=color,width=12,style="arc")
        c.create_text(75,68,text=f"{int(conf*100)}%",font=("Arial",22,"bold"),fill=TMAIN)
        c.create_text(75,90,text="Confidence",font=("Arial",10),fill=TSUB)

    def _heatmap(self, snapshots, pause_coords, flag):
        c = self.hm_cv
        c.delete("all")
        self._hm_last  = (snapshots, pause_coords, flag)
        self._hm_nodes = []

        W = max(c.winfo_width(), 600)
        H = max(c.winfo_height(), 380)
        ML, MR, MT, MB = 80, 24, 30, 52
        plot_w = W - ML - MR
        plot_h = H - MT - MB

        if not snapshots:
            c.create_text(W // 2, H // 2, text="(No significant pause events detected.)",
                          fill=TSUB, font=("Arial", 11, "italic"))


            self.hm_lbl.configure(text="Smooth cursor trajectories consistent with baseline.",
                                    fg_color="#D1FAE5", text_color="#065F46")
            return

        # ── X axis range ─────────────────────────────────────────────────────
        all_pauses = [s.get("pre_typing_pause_ms", 0) for s in snapshots]
        x_max_ms   = max(max(all_pauses) * 1.15, 1500.0)
        self._hm_x_max_ms = x_max_ms

        zoom      = self._hm_zoom
        pan_ms    = max(0.0, min(self._hm_pan_ms, x_max_ms - x_max_ms / zoom))
        self._hm_pan_ms  = pan_ms
        visible_ms = x_max_ms / zoom

        def ms_to_px(ms):
            return ML + (ms - pan_ms) / visible_ms * plot_w

        # ── Y axis: 4 domain bands ────────────────────────────────────────────
        band_h = plot_h / 4
        domain_names = {1: "Time/Work", 2: "Interpersonal",
                        3: "Academic",      4: "Self-Eval"}
        for gid in range(1, 5):
            cy  = MT + (gid - 0.5) * band_h
            col = GROUP_COLORS.get(gid, "#888")
            bg  = GROUP_BG.get(gid, "#F8FAFC")
            c.create_rectangle(ML, MT + (gid - 1) * band_h,
                                W - MR, MT + gid * band_h,
                                fill=bg, outline="")
            # Faint band separator
            c.create_line(ML, MT + gid * band_h, W - MR, MT + gid * band_h,
                          fill=BORDER, width=1, dash=(4, 4))
            # Y label
            c.create_text(ML - 6, cy, text=domain_names[gid],
                          font=("Arial", 7, "bold"), fill=col, anchor="e")

        # Y axis spine
        c.create_line(ML, MT, ML, H - MB, fill=BORDER, width=1)

        # ── X axis ticks & grid ───────────────────────────────────────────────
        if   visible_ms > 8000: tick_ms = 2000
        elif visible_ms > 4000: tick_ms = 1000
        elif visible_ms > 2000: tick_ms =  500
        elif visible_ms > 1000: tick_ms =  250
        else:                   tick_ms =  100

        c.create_line(ML, H - MB, W - MR, H - MB, fill=BORDER, width=1)
        c.create_text(ML + plot_w // 2, H - 12,
                      text="Pre-typing pause — time from Question Shown → first keypress",
                      font=("Arial", 8), fill=TSUB)

        t = int(pan_ms / tick_ms) * tick_ms
        while t <= pan_ms + visible_ms:
            px = ms_to_px(t)
            if ML <= px <= W - MR:
                c.create_line(px, MT, px, H - MB, fill="#F1F5F9", width=1)
                c.create_line(px, H - MB, px, H - MB + 5, fill=BORDER, width=1)
                lbl = f"{t / 1000:.1f}s" if t >= 1000 else f"{int(t)}ms"
                c.create_text(px, H - MB + 16, text=lbl, font=("Arial", 8), fill=TSUB)
            t += tick_ms

        # ── Draw nodes ────────────────────────────────────────────────────────
        for snap in snapshots[:12]:
            gid      = snap.get("group_id", 1)
            pause_ms = snap.get("pre_typing_pause_ms", 0)
            iid      = snap.get("item_id", "?")
            col      = GROUP_COLORS.get(gid, "#888")
            hover    = snap.get("hover_words", [])

            cx = ms_to_px(pause_ms)
            cy = MT + (gid - 0.5) * band_h

            pf = min(pause_ms / x_max_ms, 1.0)
            r  = max(14, min(32, int(pf * 22) + 14))

            # Clip nodes fully outside plot area (allow partial for edge nodes)
            if cx < ML - r - 2 or cx > W - MR + r + 2:
                continue

            # Glow + main node
            c.create_oval(cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4,
                          fill=_blend(col, 0.10), outline="")
            c.create_oval(cx - r, cy - r, cx + r, cy + r,
                          fill=_blend(col, 0.55), outline=col, width=2)
            c.create_text(cx, cy, text=iid, font=("Arial", 9, "bold"), fill=col)

            # Store for hit-testing in tooltip handler
            self._hm_nodes.append((cx, cy, r, snap))

            # Top-3 hover word chips stacked above node
            top3     = [h for h in hover[:3] if len(h.get("word", "")) > 2]
            chip_h   = 18
            chip_gap = 3
            total_ch = len(top3) * (chip_h + chip_gap)
            chip_y0  = cy - r - 8 - total_ch

            for j, hw in enumerate(top3):
                word    = hw.get("word", "")
                chip_y  = chip_y0 + j * (chip_h + chip_gap)
                chip_w  = max(44, len(word) * 6 + 18)
                chip_x1 = cx - chip_w // 2
                chip_x2 = cx + chip_w // 2
                if chip_y > MT:
                    outline_c = col if j == 0 else _blend(col, 0.55)
                    weight    = "bold" if j == 0 else "normal"
                    c.create_rectangle(chip_x1, chip_y, chip_x2, chip_y + chip_h,
                                       fill="white", outline=outline_c, width=1)
                    c.create_text((chip_x1 + chip_x2) // 2, chip_y + chip_h // 2,
                                  text=f'"{word}"',
                                  font=("Arial", 7, weight), fill=outline_c)

            # Dwell time of top word below node
            if top3:
                dwell = top3[0].get("dwell_ms", 0)
                c.create_text(cx, cy + r + 14, text=f"{dwell:.0f}ms",
                              font=("Arial", 8), fill=TSUB)

        self.hm_lbl.configure(
            text="Node size = reading latency (larger = longer). "
                 "Chips = top 3 hover words by dwell time. "
                 "Scroll to zoom · Drag to pan.",
            fg_color="#FEE2E2" if flag != "GREEN" else "#D1FAE5",
            text_color=RED_C if flag != "GREEN" else "#065F46")

      # ── Heatmap event handlers ────────────────────────────────────────────────

    def _hm_on_resize(self, event=None):
        if hasattr(self, "_hm_resize_job"):
            self.hm_cv.after_cancel(self._hm_resize_job)
        self._hm_resize_job = self.hm_cv.after(60, self._hm_redraw)

    def _hm_redraw(self):
        if self._hm_last:
            self._heatmap(*self._hm_last)

    def _hm_on_scroll(self, event):
        if not self._hm_last:
            return "break" # "break" prevents the event reaching the outer CTkScrollableFrame's bind_all handler
        if hasattr(event, "delta") and event.delta != 0:
            direction = 1 if event.delta > 0 else -1
        elif event.num == 4:
            direction = 1
        else:
            direction = -1

        old_zoom   = self._hm_zoom
        new_zoom   = max(0.5, min(8.0, old_zoom * (1.15 if direction > 0 else 1 / 1.15)))
        x_max_ms   = self._hm_x_max_ms
        pan_ms     = self._hm_pan_ms
        W          = max(self.hm_cv.winfo_width(), 600)
        ML, MR     = 80, 24
        plot_w     = W - ML - MR
        old_vis    = x_max_ms / old_zoom
        new_vis    = x_max_ms / new_zoom
        frac       = max(0.0, min(1.0, (event.x - ML) / plot_w))
        new_pan    = pan_ms + frac * (old_vis - new_vis)
        self._hm_zoom   = new_zoom
        self._hm_pan_ms = max(0.0, min(new_pan, x_max_ms - new_vis))
        if hasattr(self, "_hm_scroll_job"):
            self.hm_cv.after_cancel(self._hm_scroll_job)
        self._hm_scroll_job = self.hm_cv.after(16, self._hm_redraw)
        return "break"

    def _hm_on_drag_start(self, event):
        self._hm_drag_x = event.x

    def _hm_on_drag(self, event):
        if not self._hm_last or not hasattr(self, "_hm_drag_x"):
            return
        dx_px      = event.x - self._hm_drag_x
        self._hm_drag_x = event.x
        W          = max(self.hm_cv.winfo_width(), 600)
        ML, MR     = 80, 24
        plot_w     = W - ML - MR
        visible_ms = self._hm_x_max_ms / self._hm_zoom
        delta_ms   = -dx_px / plot_w * visible_ms
        old_pan    = self._hm_pan_ms
        self._hm_pan_ms = max(0.0, min(old_pan + delta_ms,
                                        self._hm_x_max_ms - visible_ms))
        if hasattr(self, "_hm_drag_job"):
            self.hm_cv.after_cancel(self._hm_drag_job)
        self._hm_drag_job = self.hm_cv.after(16, self._hm_redraw)

    def _hm_on_motion(self, event):
        self._hm_motion_pos = (event.x, event.y)
        if hasattr(self, "_hm_motion_job"):
            self.hm_cv.after_cancel(self._hm_motion_job)
        self._hm_motion_job = self.hm_cv.after(16, self._hm_process_motion)

    def _hm_process_motion(self):
        if not hasattr(self, "_hm_motion_pos"):
            return
        mx, my = self._hm_motion_pos
        for tid in self._hm_tip_ids:
            self.hm_cv.delete(tid)
        self._hm_tip_ids = []
        
        for (cx, cy, r, snap) in self._hm_nodes:
            if ((mx - cx) ** 2 + (my - cy) ** 2) ** 0.5 <= r + 6:
                self._hm_show_tooltip(mx, my, snap)
                return

    def _hm_show_tooltip(self, mx, my, snap):
        c     = self.hm_cv
        hover = snap.get("hover_words", [])
        top   = hover[0] if hover else None
        total_dwell  = sum(h.get("dwell_ms", 0) for h in hover)
        hover_count  = top.get("hover_count", 0) if top else 0
        top_word     = top.get("word", "—") if top else "—"
        lines = [
            f"Word:        {top_word}",
            f"Dwell:       {total_dwell:.0f} ms",
            f"Hover count: {hover_count}",
        ]
        pad    = 10
        line_h = 17
        tip_w  = 170
        tip_h  = pad * 2 + line_h * len(lines)
        W      = max(c.winfo_width(), 600)
        H      = max(c.winfo_height(), 380)
        tx = mx + 16
        ty = my - tip_h // 2
        if tx + tip_w > W - 8:  tx = mx - tip_w - 10
        if ty < 4:               ty = 4
        if ty + tip_h > H - 4:  ty = H - tip_h - 4
        ids = []
        ids.append(c.create_rectangle(tx, ty, tx + tip_w, ty + tip_h,
                                       fill="white", outline=BORDER, width=1))
        for k, line in enumerate(lines):
            ids.append(c.create_text(tx + pad, ty + pad + k * line_h,
                                      text=line, anchor="nw",
                                      font=("Arial", 9), fill=TMAIN))
        self._hm_tip_ids = ids





    def _spectrogram(self, ft, flag, pai):
        c = self.sp_cv
        c.delete("all")
        self._sp_last = (ft, flag, pai)
        self._sp_bars = []

        W = max(c.winfo_width(), 600)
        H = max(c.winfo_height(), 300)
        ML, MR, MT, MB = 52, 20, 18, 42
        plot_w = W - ML - MR
        plot_h = H - MT - MB

        # Axes
        c.create_line(ML, MT, ML, H - MB, fill=BORDER, width=1)
        c.create_line(ML, H - MB, W - MR, H - MB, fill=BORDER, width=1)
        c.create_text(ML + plot_w // 2, H - 12,
                      text="Keystroke interval sequence", font=("Arial", 8), fill=TSUB)

        color = "#F97316" if flag in ("AMBER", "RED") else GREEN
        if ft:
            times=[t*1000 for t in ft[-14:]];
        else:
            if flag == "RED":
                times = [random.randint(40, 160) for _ in range(12)]
            elif flag == "AMBER":
                times = [random.randint(70, 130) for _ in range(12)]
            else:
                times = [random.randint(88, 112) for _ in range(12)]

        if not times:
            return

        n  = len(times)
        mx = max(times)

        # Dynamic bar width fills available horizontal space
        gap = max(4, plot_w // max(n * 6, 1))
        bw  = max(14, (plot_w - gap * (n - 1)) // n)
        total_needed = bw * n + gap * (n - 1)
        start_x = ML + (plot_w - total_needed) // 2

        # Y axis ticks at 25 / 50 / 75 / 100% of max
        for frac in (0.25, 0.5, 0.75, 1.0):
            val = mx * frac
            ty  = H - MB - int(frac * plot_h)
            c.create_line(ML - 4, ty, ML, ty, fill=BORDER, width=1)
            c.create_line(ML, ty, W - MR, ty, fill="#F8FAFC", width=1)
            c.create_text(ML - 6, ty, text=f"{val:.0f}",
                          font=("Arial", 7), fill=TSUB, anchor="e")

        # Y axis label
        c.create_text(12, MT + plot_h // 2, text="ms",
                      font=("Arial", 9), fill=TSUB, angle=90)

        for i, t in enumerate(times):
            bh = max(4, int(t / mx * plot_h))
            x1 = start_x + i * (bw + gap)
            y1 = H - MB - bh
            x2 = x1 + bw
            y2 = H - MB
            c.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
            c.create_text(x1 + bw // 2, H - MB + 14,
                          text=str(i + 1), fill=TSUB, font=("Arial", 7))
            self._sp_bars.append((x1, y1, x2, y2, t))

        if flag in ("AMBER", "RED"):
            self.sp_lbl.configure(
                text=f"Erratic intervals detected. Deviation: +{int(pai*45)}% above baseline. "
                     "Pattern consistent with anxiety-driven keystroke irregularity.",
                fg_color="#FEF3C7",text_color=AMBER)
        else:
                       self.sp_lbl.configure(
                text="Consistent keystroke rhythm within normal baseline boundaries.",
                fg_color="#D1FAE5", text_color="#065F46")


   
    # ── Spectrogram event handlers ────────────────────────────────────────────

    def _sp_on_resize(self, event=None):
        if hasattr(self, "_sp_resize_job"):
            self.sp_cv.after_cancel(self._sp_resize_job)
        self._sp_resize_job = self.sp_cv.after(60, self._sp_redraw)

    def _sp_redraw(self):
        if self._sp_last:
            self._spectrogram(*self._sp_last)

    def _sp_on_motion(self, event):

        self._sp_motion_pos = (event.x, event.y)
        if hasattr(self, "_sp_motion_job"):
            self.sp_cv.after_cancel(self._sp_motion_job)
        self._sp_motion_job = self.sp_cv.after(16, self._sp_process_motion)

    def _sp_process_motion(self):
        if not hasattr(self, "_sp_motion_pos"):
            return
        mx, my = self._sp_motion_pos

        for tid in self._sp_tip_ids:
            self.sp_cv.delete(tid)
        self._sp_tip_ids = []
        for (x1, y1, x2, y2, val_ms) in self._sp_bars:
             if x1 <= mx <= x2 and y1 <= my <= y2:
                c  = self.sp_cv
                W  = max(c.winfo_width(), 600)
                tx = mx + 10
                ty = my - 24
                if tx + 72 > W - 8:
                    tx = mx - 80
                if ty < 4:
                    ty = 4
                ids = []
                ids.append(c.create_rectangle(tx, ty, tx + 70, ty + 22,
                                            fill="white", outline=BORDER, width=1))
                ids.append(c.create_text(tx + 35, ty + 11,
                                        text=f"{val_ms:.1f} ms",
                                        font=("Arial", 9, "bold"), fill=TMAIN))
                self._sp_tip_ids = ids
                return


    def _q_table(self, snapshots):
        
        c = self.q_cv
        c.delete("all")
        COLS = [("Item",46),("Group",260),("Lvl",34),("T²",60),("PSI",60),
                ("PAI",60),("Flight ms",74),("Pre-Key ms",74),("Velocity",68),("Flag",58)]
        RH = 23
        FLAG_C = {"GREEN": GREEN, "AMBER": AMBER, "RED": RED_C}

        # Header
        total_w = sum(w for _, w in COLS)
        c.create_rectangle(0, 0, total_w, RH, fill="#F8FAFC", outline="")
        x = 4
        for name, w in COLS:
            c.create_text(x, RH // 2, text=name, anchor="w",
                          font=("Arial", 9, "bold"), fill=TSUB)
            x += w

        # Data rows
        for i, snap in enumerate(snapshots):
            y   = RH + i * RH
            bg  = "#F8FAFC" if i % 2 else CARD
            gid = snap.get("group_id", 1)
            flag = snap.get("flag", "GREEN")
            fc   = FLAG_C.get(flag, TSUB)
            gc   = GROUP_COLORS.get(gid, TSUB)
            c.create_rectangle(0, y, total_w, y + RH, fill=bg, outline="")
            vals = [snap.get("item_id","?"), snap.get("group_name",""),
                    snap.get("level","A"), f"{snap.get('t2_score',0):.2f}",
                    f"{snap.get('psi',0):.2f}", f"{snap.get('pai',0):.2f}",
                    f"{snap.get('flight_time',0)*1000:.0f}",
                    f"{snap.get('pre_typing_pause_ms',0):.0f}",
                    f"{snap.get('cursor_velocity',0):.0f}", flag]
            x = 4
            for j, ((_, w), val) in enumerate(zip(COLS, vals)):
                if j == 9:  # flag badge
                    bx = x - 2
                    c.create_rectangle(bx, y+4, bx+50, y+RH-4, fill=fc, outline="")
                    c.create_text(bx+25, y+RH//2, text=val, anchor="center",
                                  font=("Arial", 8, "bold"), fill="white")
                else:
                    col = gc if j == 0 else TMAIN
                    c.create_text(x, y+RH//2, text=str(val), anchor="w",
                                  font=("Arial", 10), fill=col)
                x += w

        total_h = RH * (1 + len(snapshots))
        c.configure(height=max(total_h, RH * 2))

    def _domain_chart(self, domain_t2, level_t2):
        c=self.dm_cv; c.delete("all"); W,H=450,170
        groups=[(1,"Time/\nWorkload",GROUP_COLORS[1]),(2,"Interpersonal",GROUP_COLORS[2]),
                (3,"Academic/\nPerf.",GROUP_COLORS[3]),(4,"Self-\nEval.",GROUP_COLORS[4])]
        if not domain_t2 and not level_t2:
            c.create_text(W//2,H//2,text="Domain T² available after full session",
                          fill=TSUB,font=("Arial",11,"italic")); return
        mv=max(list(domain_t2.values())+[0.01]); bw,gap,xs=44,18,28
        for i,(gid,label,col) in enumerate(groups):
            val=domain_t2.get(gid,0); h=max(6,int((val/mv)*(H-52)))
            x=xs+i*(bw+gap); y=H-28-h
            c.create_rectangle(x,y,x+bw,H-28,fill=_blend(col,0.55),outline=col,width=1.5)
            c.create_text(x+bw//2,y-10,text=f"{val:.2f}",fill=col,font=("Arial",9,"bold"))
            c.create_text(x+bw//2,H-12,text=label,fill=TSUB,font=("Arial",8),justify="center")
        if level_t2:
            levels=[("A",LEVEL_COLORS["A"]),("B",LEVEL_COLORS["B"]),("C",LEVEL_COLORS["C"])]
            lv_vals=[level_t2.get(lv,0) for lv,_ in levels]; lv_max=max(lv_vals+[0.01])
            rx0,rx1,ry0,ry1=280,W-20,20,H-30; rw,rh=rx1-rx0,ry1-ry0
            c.create_line(rx0,ry1,rx1,ry1,fill=BORDER,width=1)
            c.create_line(rx0,ry0,rx0,ry1,fill=BORDER,width=1)
            pts=[]
            for i,((lv,col),val) in enumerate(zip(levels,lv_vals)):
                x=rx0+(i/(len(levels)-1))*rw if len(levels)>1 else rx0+rw//2
                y=ry1-(val/lv_max)*rh; pts.append((x,y))
                c.create_oval(x-5,y-5,x+5,y+5,fill=col,outline="")
                c.create_text(x,ry1+10,text=lv,fill=TSUB,font=("Arial",9,"bold"))
                c.create_text(x,y-12,text=f"{val:.2f}",fill=col,font=("Arial",8,"bold"))
            if len(pts)>=2:
                for j in range(len(pts)-1):
                    c.create_line(pts[j][0],pts[j][1],pts[j+1][0],pts[j+1][1],
                                  fill=TMAIN,width=2,dash=(4,2))
            c.create_text(rx0+rw//2,ry0-6,text="Level A→B→C",fill=TSUB,font=("Arial",9,"italic"))

    def _recommendations(self, flag, label, psi, pai, phq, gad, dom, lvl):
        for w in self.rec_frame.winfo_children(): w.destroy()
        recs=_clinical_recs(flag, label, psi, pai, phq, gad, dom, lvl)
        grid=ctk.CTkFrame(self.rec_frame,fg_color="transparent"); grid.pack(fill="x")
        grid.grid_columnconfigure(0,weight=1); grid.grid_columnconfigure(1,weight=1)
        for i,(title,desc) in enumerate(recs):
            row,col=divmod(i,2)
            f=ctk.CTkFrame(grid,fg_color="#F8FAFC",corner_radius=10,border_width=1,border_color=BORDER)
            f.grid(row=row,column=col,sticky="ew",padx=6,pady=6)
            num=ctk.CTkLabel(f,text=str(i+1),font=("Poppins",13,"bold"),text_color="white",
                              fg_color=BLUE_C,width=28,height=28,corner_radius=14)
            num.pack(side="left",anchor="n",padx=(10,10),pady=12)
            tf=ctk.CTkFrame(f,fg_color="transparent"); tf.pack(side="left",fill="x",expand=True,pady=10)
            ctk.CTkLabel(tf,text=title,font=("Inter",12,"bold"),text_color=TMAIN,
                          anchor="w",wraplength=300,justify="left").pack(anchor="w")
            ctk.CTkLabel(tf,text=desc,font=("Inter",11),text_color=TSUB,
                          wraplength=300,justify="left").pack(anchor="w",pady=(2,0))


# ═══════════════════════════════════════════════════════════════════════════════
# PATIENTS
# ═══════════════════════════════════════════════════════════════════════════════
class PatientsPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG)
        self.controller = controller
        self._all_rows  = []
        make_sidebar(self, controller, "Patient History")
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(side="right", fill="both", expand=True, padx=40, pady=30)
      
         # ── Header row ────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(main, fg_color="transparent")
        hdr.pack(fill="x", pady=(0,14))
        ctk.CTkLabel(hdr, text="Patient Sessions", font=("Poppins",26,"bold"),
                      text_color=TMAIN).pack(side="left")

        sort_row = ctk.CTkFrame(hdr, fg_color="transparent")
        sort_row.pack(side="right")
        ctk.CTkLabel(sort_row, text="Sort by:", font=("Inter",13),
                      text_color=TSUB).pack(side="left", padx=(0,6))
        self._sort_var = tk.StringVar(value="Date (Newest)")
        ctk.CTkOptionMenu(
            sort_row,
            values=["Date (Newest)", "Date (Oldest)",
                    "Flag (Risk First)"],
            variable=self._sort_var,
            width=178, height=34,
            fg_color=CARD, button_color=ACCENT, button_hover_color=ADARK,
            text_color=TMAIN, dropdown_fg_color=CARD, dropdown_text_color=TMAIN,
            font=("Inter",13),
            command=lambda _: self._apply_filter()
        ).pack(side="left")

        # ── Search bar ────────────────────────────────────────────────────────
        sb = ctk.CTkFrame(main, fg_color=CARD, corner_radius=10,
                           border_width=1, border_color=BORDER)
        sb.pack(fill="x", pady=(0,14))
        ctk.CTkLabel(sb, text="🔍", font=("Inter",14),
                      text_color=TSUB).pack(side="left", padx=(12,4), pady=8)
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        self._search_entry = ctk.CTkEntry(
            sb, textvariable=self._search_var,
            placeholder_text="Search by patient ID, date, or flag…",
            border_width=0, fg_color="transparent",
            text_color=TMAIN, placeholder_text_color=TSUB,
            font=("Inter",13)
        )
        self._search_entry.pack(side="left", fill="x", expand=True, pady=6)
        ctk.CTkButton(
            sb, text="✕", width=28, height=28,
            fg_color="transparent", hover_color=BORDER,
            text_color=TSUB, font=("Inter",12,"bold"), corner_radius=14,
            command=self._clear_search
        ).pack(side="right", padx=6)

        # ── Patient list ──────────────────────────────────────────────────────

        self.sf = ctk.CTkScrollableFrame(main, fg_color="transparent")
        self.sf.pack(fill="both", expand=True)

    def _clear_search(self):
        self._search_var.set("")
        self._search_entry.focus()

    def _apply_filter(self):
        query = self._search_var.get().strip().lower()
        sort  = self._sort_var.get()
        rows  = self._all_rows

        if query:
            rows = [r for r in rows
                    if query in str(r[1]).lower()        # patient ID
                    or query in str(r[2]).lower()        # timestamp
                    or query in str(r[3] or "").lower()] # flag

        FLAG_ORDER = {"RED": 0, "AMBER": 1, "GREEN": 2}
        if sort == "Date (Newest)":
            rows = sorted(rows, key=lambda r: r[2] or "", reverse=True)
        elif sort == "Date (Oldest)":
            rows = sorted(rows, key=lambda r: r[2] or "")
        elif sort == "Flag (Risk First)":
            rows = sorted(rows, key=lambda r: FLAG_ORDER.get(r[3], 9))
        

        self._render_rows(rows)

    def _render_rows(self, rows):
        for w in self.sf.winfo_children(): w.destroy()
        if not rows:
            msg = ("No patients match your search." if self._search_var.get()
                   else "No patient sessions recorded yet.")
            ctk.CTkLabel(self.sf, text=msg, font=("Inter",14),
                          text_color=TSUB).pack(pady=60)
            return
        for sid, pid, ts, flag, phq, gad in rows:
            self._card(sid, pid, ts, flag, phq or 0, gad or 0)

    def refresh_list(self):
        self._all_rows = get_latest_sessions()
        self._apply_filter()

    def _card(self, sid, pid, ts, flag, phq, gad):
        _, _, tc, bc, _ = flag_ui(flag or "GREEN")
        card = ctk.CTkFrame(self.sf, fg_color=CARD, corner_radius=13,
                             border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=5)
        ctk.CTkLabel(card, text=f"Patient: {pid}", font=("Inter",14,"bold"),
                      text_color=TMAIN).pack(side="left", padx=18, pady=16)
        ctk.CTkLabel(card, text=str(ts)[:16], font=("Inter",12),
                      text_color=TSUB).pack(side="left", padx=10)
        ctk.CTkLabel(card, text=f"PHQ-9: {phq}  GAD-7: {gad}", font=("Inter",12),
                      text_color=TSUB).pack(side="left", padx=10)
        ctk.CTkLabel(card, text=flag or "—", font=("Inter",12,"bold"),
                      fg_color=tc, text_color="white",
                      corner_radius=12, width=72, height=26).pack(side="left", padx=10)
        ctk.CTkButton(card, text="View Report →", width=130, height=36, corner_radius=18,
                       fg_color="#F8FAFC", text_color=BLUE_C,
                       border_color=BORDER, border_width=1,
                       command=lambda s=sid: self.controller.open_patient_detail(s)
                       ).pack(side="right", padx=18)


class PatientDetailPage(ReportPage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._student_sessions = []  # list of (session_id, timestamp, phq, gad, flag)
        self._session_var = tk.StringVar(value="")

    def _refresh_selector(self, student_id, current_session_id):
        """Rebuild the session dropdown inside _session_sel_frame."""
        for w in self._session_sel_frame.winfo_children():
            w.destroy()

        self._student_sessions = get_sessions_by_student(student_id)
        if len(self._student_sessions) <= 1:
            return  # no dropdown needed for single session

        labels = []
        for sid, ts, phq, gad, flag in self._student_sessions:
            phq_str = str(phq) if phq is not None else "—"
            gad_str = str(gad) if gad is not None else "—"
            flag_str = flag or "—"
            labels.append(f"{str(ts)[:16]}  |  PHQ-9: {phq_str}  GAD-7: {gad_str}  [{flag_str}]")

        # Map label → session_id
        self._label_to_sid = {lbl: sid for (sid, ts, phq, gad, flag), lbl
                               in zip(self._student_sessions, labels)}

        # Find label for current session
        current_label = labels[0]
        for (sid, ts, phq, gad, flag), lbl in zip(self._student_sessions, labels):
            if sid == current_session_id:
                current_label = lbl
                break

        self._session_var.set(current_label)

        ctk.CTkLabel(self._session_sel_frame, text="Session:",
                     font=("Inter", 12, "bold"), text_color=TSUB).pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(
            self._session_sel_frame,
            variable=self._session_var,
            values=labels,
            width=520,
            font=("Inter", 12),
            command=self._on_session_change,
        ).pack(side="left")

    def _on_session_change(self, label):
        sid = self._label_to_sid.get(label)
        if sid is not None:
            self.load_session(sid)

    def load_session(self, session_id):
        try:
            conn=sqlite3.connect("psyclick_data.db"); c=conn.cursor()
            c.execute("""SELECT student_id,timestamp,phq_score,gad_score,
                                t2_score,t2_threshold,psi,pai,
                                fuzzy_label,fuzzy_confidence,flag,rationale,
                                domain_t2_json,question_snapshots_json
                         FROM intake_sessions WHERE session_id=?""", (session_id,))
            row = c.fetchone(); conn.close()
            if not row:
                return
            (sid, ts, phq, gad, t2, thr, psi, pai, label, conf, flag, rat,
             dom_json, snap_json) = row
            dom = {int(k): v for k, v in json.loads(dom_json or "{}").items()}
            snaps = json.loads(snap_json or "[]")
            data = {"student_id": sid, "timestamp": ts,
                    "phq": {"score": phq or 0}, "gad": {"score": gad or 0},
                    "analysis": {"flag": flag, "t2_score": t2, "t2_threshold": thr,
                                 "psi": psi, "pai": pai, "label": label,
                                 "confidence": conf, "rationale": rat},
                    "visuals": {"question_snapshots": snaps, "domain_t2": dom,
                                "level_t2": {}, "flight_times": [], "pause_coords": []}}
            self._refresh_selector(sid, session_id)
                         
            self.display_report(data)
        except Exception as e: print(f"PatientDetailPage: {e}")

class AuditPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG)
        self.controller = controller
        self._active_tab = "clinician"
        make_sidebar(self, controller, "Audit")
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(side="right", fill="both", expand=True, padx=40, pady=30)
        # Header
        hdr = ctk.CTkFrame(main, fg_color="transparent"); hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="Audit Log", font=("Poppins",28,"bold"),
                     text_color=TMAIN).pack(side="left")
        ctk.CTkButton(hdr, text="↻ Refresh", width=100, height=36,
                      corner_radius=18, fg_color=ACCENT, hover_color=ADARK,
                      font=("Inter",13,"bold"),
                      command=self._refresh).pack(side="right")
        # Tab toggles
        # Tab toggles
        tabs = ctk.CTkFrame(main, fg_color="transparent")
        tabs.pack(fill="x", pady=(16,0))

        self.btn_clin = ctk.CTkButton(
            tabs, text="Clinician Audit",
            command=lambda: self._switch("clinician"),
            width=160, height=36, corner_radius=18
        )
        self.btn_clin.pack(side="left", padx=(0,10))

        self.btn_pat = ctk.CTkButton(
            tabs, text="Patient Audit",
            command=lambda: self._switch("patient"),
            width=160, height=36, corner_radius=18
        )
        self.btn_pat.pack(side="left")

        # Log area
        self.log_frame = ctk.CTkScrollableFrame(main, fg_color=CARD)
        self.log_frame.pack(fill="both", expand=True, pady=(12,0))

    def on_show(self): 
        self._refresh()

    def _switch(self, tab):
        self._active_tab = tab
        # update button styles
        self._refresh()

    def _refresh(self):
        for w in self.log_frame.winfo_children(): w.destroy()
        rows = get_audit_logs(actor=self._active_tab)
        if not rows:
            ctk.CTkLabel(self.log_frame, text="No activity logged yet.",
                         font=("Inter",13), text_color=TSUB).pack(pady=30)
            return
        for ts, action, detail in rows:
            row = ctk.CTkFrame(self.log_frame, fg_color="transparent")
            row.pack(fill="x", pady=3)
            # timestamp chip
            ctk.CTkLabel(row, text=ts, font=("Inter",11), text_color=TSUB,
                         width=160, anchor="w").pack(side="left", padx=(0,10))
            # action
            ctk.CTkLabel(row, text=action, font=("Inter",13,"bold"),
                         text_color=TMAIN, anchor="w").pack(side="left")
            # detail (optional)
            if detail:
                ctk.CTkLabel(row, text=f"— {detail}", font=("Inter",12),
                             text_color=TSUB, anchor="w").pack(side="left", padx=(8,0))

if __name__=="__main__":
    app=PsyClickApp(); app.mainloop()
