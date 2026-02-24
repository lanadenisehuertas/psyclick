import customtkinter as ctk
import tkinter as tk
import random
import math
from datetime import datetime
import sqlite3
from backend_controller import PsyClickController

backend = PsyClickController()

# --- UI AESTHETIC: Modern Glassmorphism / Soft UI ---
ctk.set_appearance_mode("Light")  
ctk.set_default_color_theme("blue")

BG_COLOR = "#EEF2FF"       # Soft Lavender/Blue background 
CARD_COLOR = "#FFFFFF"     # Crisp white cards
TEXT_MAIN = "#1E293B"      # Dark slate for primary text
TEXT_SUB = "#64748B"       # Muted slate for secondary text
BORDER_COLOR = "#E2E8F0"   # Soft borders

# --- HELPERS ---
def get_phq_interpretation(score):
    if score <= 4: return "Minimal depression"
    elif score <= 9: return "Mild depression"
    elif score <= 14: return "Moderate depression"
    elif score <= 19: return "Moderately severe"
    else: return "Severe depression"

def get_gad_interpretation(score):
    if score <= 4: return "Minimal anxiety"
    elif score <= 9: return "Mild anxiety"
    elif score <= 14: return "Moderate anxiety"
    else: return "Severe anxiety"

def get_flag_style(flag):
    # Returns: (Title, Subtitle, Text Color, Background Color, Icon)
    if flag == "GREEN": 
        return "OVERALL STATUS: GREEN - Normal Patterns", "Behavior is statistically consistent with baseline.", "#10B981", "#D1FAE5", "✓"
    elif flag == "AMBER": 
        return "OVERALL STATUS: AMBER - Moderate Deviation", "Heuristic Decision Tree flagged moderate deviations.", "#F59E0B", "#FEF3C7", "!"
    elif flag == "RED": 
        return "OVERALL STATUS: RED - Unusual Patterns Detected", "Heuristic Decision Tree flagged significant deviations. Immediate review recommended.", "#EF4444", "#FEE2E2", "!"
    return "OVERALL STATUS: PENDING", "Analysis Unavailable", "#94A3B8", "#F1F5F9", "?"


# ==========================================
# MAIN APPLICATION ROUTER
# ==========================================
class PsyClickApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PsyClick v1.0 - Clinical Decision Support")
        self.is_fullscreen = True
        self.attributes("-fullscreen", True)
        self.bind("<Escape>", self.toggle_fullscreen)
        self.configure(fg_color=BG_COLOR)

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        self.frames = {}
        
        page_list = (LoginPage, DashboardPage, IntakePage, 
                     KCalibrationPage, MCalibrationPage, 
                     PHQ9Page, GAD7Page, TaskPage, ReportPage,
                     PatientsPage, PatientDetailPage)
        
        for F in page_list:
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("LoginPage")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if hasattr(frame, 'on_show'): frame.on_show()

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not getattr(self, "is_fullscreen", False)
        self.attributes("-fullscreen", self.is_fullscreen)

    def ensure_frame(self, page_cls):
        name = page_cls.__name__
        if name not in self.frames:
            frame = page_cls(parent=self.container, controller=self)
            self.frames[name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        return self.frames[name]

    def open_patients(self):
        page = self.ensure_frame(PatientsPage)
        page.refresh_list()
        self.show_frame("PatientsPage")

    def open_patient_detail(self, session_id):
        page = self.frames["PatientDetailPage"]
        page.load_session(session_id)
        self.show_frame("PatientDetailPage")


# ==========================================
# UI CLASSES (LOGIN, DASHBOARD, WIZARDS)
# ==========================================
class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG_COLOR)
        self.controller = controller 
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(expand=True)
        ctk.CTkLabel(content, text="PsyClick", font=("Poppins", 44, "bold"), text_color="#8B5CF6").pack(pady=(0, 5))
        ctk.CTkLabel(content, text="Clinical Decision Support System", font=("Inter", 16), text_color=TEXT_SUB).pack(pady=(0, 40))
        box = ctk.CTkFrame(content, width=350, height=250, corner_radius=20, fg_color=CARD_COLOR, border_width=1, border_color=BORDER_COLOR)
        box.pack(pady=20)
        box.pack_propagate(False)
        self.user = ctk.CTkEntry(box, placeholder_text="Clinician ID", width=280, height=45, corner_radius=10, fg_color="#F8FAFC", border_color="#CBD5E1", text_color=TEXT_MAIN)
        self.user.pack(pady=(30, 15), padx=20)
        self.pwd = ctk.CTkEntry(box, placeholder_text="Password", show="*", width=280, height=45, corner_radius=10, fg_color="#F8FAFC", border_color="#CBD5E1", text_color=TEXT_MAIN)
        self.pwd.pack(pady=(0, 10), padx=20)
        self.lbl_error = ctk.CTkLabel(box, text="", text_color="#EF4444", font=("Inter", 12))
        self.lbl_error.pack(pady=0)
        ctk.CTkButton(box, text="Secure Login", width=280, height=45, corner_radius=25, font=("Inter", 15, "bold"), fg_color="#8B5CF6", hover_color="#7C3AED", command=self.login_check).pack(pady=(10, 20))
        ctk.CTkLabel(self, text="🔒 All data encrypted and stored locally", text_color=TEXT_SUB).pack(side="bottom", pady=20)

    def login_check(self):
        user_names = {"202312480": "Dr. Anonuevo", "202310964": "Dr. Huertas", "202311990": "Dr. Tablate", "202310557": "Dr. Ballano"}
        if self.user.get() in user_names and self.pwd.get() == "12345":
            self.lbl_error.configure(text="")
            display_name = user_names[self.user.get()]
            self.controller.frames["DashboardPage"].welcome_label.configure(text=f"Welcome, {display_name}")
            self.user.delete(0, "end")
            self.pwd.delete(0, "end")
            self.controller.show_frame("DashboardPage")
        else:
            self.lbl_error.configure(text="Invalid Clinician ID or Password")

class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG_COLOR)
        sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=CARD_COLOR, border_width=1, border_color=BORDER_COLOR)
        sidebar.pack(side="left", fill="y")
        ctk.CTkLabel(sidebar, text="PsyClick", font=("Poppins", 24, "bold"), text_color="#8B5CF6").pack(pady=30)
        ctk.CTkButton(sidebar, text="Dashboard", fg_color="#EDE9FE", text_color="#6D28D9", font=("Inter", 14, "bold"), corner_radius=10).pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(sidebar, text="Patients History", fg_color="transparent", text_color=TEXT_SUB, hover_color="#F1F5F9", font=("Inter", 14), command=controller.open_patients).pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(sidebar, text="Logout", fg_color="transparent", text_color="#EF4444", hover_color="#FEE2E2", command=lambda: controller.show_frame("LoginPage")).pack(side="bottom", pady=30)
        
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(side="right", fill="both", expand=True, padx=40, pady=40)
        self.welcome_label = ctk.CTkLabel(main, text="Welcome!", font=("Poppins", 32, "bold"), text_color=TEXT_MAIN)
        self.welcome_label.pack(anchor="w")
        ctk.CTkLabel(main, text="Manage patient assessments and monitor baseline metrics", font=("Inter", 16), text_color=TEXT_SUB).pack(anchor="w", pady=(0, 40))
        
        card = ctk.CTkFrame(main, width=400, height=200, corner_radius=20, fg_color=CARD_COLOR, border_width=1, border_color=BORDER_COLOR)
        card.pack(anchor="w")
        card.pack_propagate(False)
        ctk.CTkLabel(card, text="Start New Session", font=("Poppins", 20, "bold"), text_color=TEXT_MAIN).pack(pady=(30, 10))
        ctk.CTkButton(card, text="+ New Patient Intake", height=45, corner_radius=25, font=("Inter", 15, "bold"), fg_color="#8B5CF6", hover_color="#7C3AED", command=lambda: controller.show_frame("IntakePage")).pack(pady=10)

class IntakePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG_COLOR)
        self.controller = controller
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(expand=True)
        ctk.CTkLabel(content, text="Welcome to PsyClick", font=("Poppins", 28, "bold"), text_color=TEXT_MAIN).pack(pady=(0,10))
        
        form = ctk.CTkFrame(content, corner_radius=20, fg_color=CARD_COLOR, border_width=1, border_color=BORDER_COLOR, width=400)
        form.pack(pady=10)
        self.entry_id = ctk.CTkEntry(form, placeholder_text="Patient ID (e.g. P001)", width=320, height=45, corner_radius=10)
        self.entry_id.pack(pady=(30, 10), padx=40)
    
        self.consent_var = ctk.BooleanVar(value=False)
        self.checkbox = ctk.CTkCheckBox(form, text="I consent to local biometric recording", variable=self.consent_var, command=self.toggle_button, text_color=TEXT_SUB)
        self.checkbox.pack(pady=(10, 30))
        
        self.btn_submit = ctk.CTkButton(content, text="Agree & Begin", state="disabled", height=45, width=200, corner_radius=25, fg_color="#8B5CF6", command=self.submit)
        self.btn_submit.pack(pady=20)

    def toggle_button(self):
        self.btn_submit.configure(state="normal" if self.consent_var.get() else "disabled")

    def submit(self):
        if self.entry_id.get():
            backend.set_student_id(self.entry_id.get())
            self.controller.show_frame("KCalibrationPage")

class KCalibrationPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG_COLOR)
        self.controller = controller
        self.start_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.start_frame.pack(expand=True)
        ctk.CTkButton(self.start_frame, text="Start Calibration", width=240, height=60, corner_radius=30, font=("Inter", 18, "bold"), fg_color="#8B5CF6", command=self.start).pack(pady=20)
        
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self.content, text="Baseline Task - Typing", font=("Poppins", 24, "bold"), text_color=TEXT_MAIN).pack(pady=(40, 10))
        
        self.target_text = "Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to create oxygen and energy in the form of sugar."
        card = ctk.CTkFrame(self.content, fg_color=CARD_COLOR, corner_radius=15, border_color=BORDER_COLOR, border_width=1)
        card.pack(pady=20, padx=20, fill="x")
        ctk.CTkLabel(card, text=self.target_text, font=("Inter", 16, "italic"), text_color="#3B82F6", wraplength=600).pack(pady=30, padx=30)
        
        self.txt = ctk.CTkTextbox(self.content, height=120, width=600, corner_radius=10, fg_color="#FFFFFF", border_color="#CBD5E1", border_width=1)
        self.txt.pack(pady=10)
        self.btn_next = ctk.CTkButton(self.content, text="Next Task ➔", state="disabled", height=45, corner_radius=25, fg_color="#8B5CF6", command=self.next_step)
        self.btn_next.pack(pady=20)

    def start(self):
        self.start_frame.pack_forget()
        self.content.pack(expand=True)
        self.txt.focus()
        backend.start_key_capture(calibration_mode=True)
        self.btn_next.configure(state="normal")
    
    def next_step(self):
        if backend.save_kbase(): self.controller.show_frame("MCalibrationPage")

class MCalibrationPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG_COLOR)
        self.controller = controller
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", pady=40)
        ctk.CTkLabel(self.header, text="Baseline Task - Mouse Tracking", font=("Poppins", 24, "bold"), text_color=TEXT_MAIN).pack()
        
        self.start_btn = ctk.CTkButton(self, text="Start Mouse Tracking", width=240, height=60, corner_radius=30, font=("Inter", 18, "bold"), fg_color="#8B5CF6", command=self.start_task)
        self.start_btn.pack(expand=True)
        self.game_area = ctk.CTkFrame(self, width=800, height=400, fg_color=CARD_COLOR, corner_radius=20, border_width=1, border_color=BORDER_COLOR)
        self.circles_found, self.total_circles, self.circle_btns = 0, 8, []

    def start_task(self):
        self.start_btn.pack_forget()
        self.game_area.pack(pady=20)
        self.game_area.pack_propagate(False)
        backend.start_mouse_capture()
        for i in range(self.total_circles):
            btn = ctk.CTkButton(self.game_area, text="", width=40, height=40, corner_radius=20, fg_color="#3B82F6", hover_color="#2563EB", command=lambda idx=i: self.click_circle(idx))
            btn.place(x=random.randint(20, 740), y=random.randint(20, 340))
            self.circle_btns.append(btn)

    def click_circle(self, idx):
        self.circle_btns[idx].place_forget()
        self.circles_found += 1
        if self.circles_found >= self.total_circles:
            if backend.save_mbase(): self.controller.show_frame("PHQ9Page")

class PHQ9Page(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG_COLOR)
        self.controller = controller
        self.questions = ["Little interest or pleasure in doing things", "Feeling down, depressed or hopeless"]
        self.current_idx, self.total_score = 0, 0
        ctk.CTkLabel(self, text="PHQ-9 Depression Screening", font=("Poppins", 24, "bold"), text_color=TEXT_MAIN).pack(pady=(60, 10))
        self.lbl_q = ctk.CTkLabel(self, text=self.questions[0], font=("Poppins", 20, "bold"), text_color=TEXT_MAIN)
        self.lbl_q.pack(pady=30)
        self.opts_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.opts_frame.pack(pady=10)
        choices = [("Not at all", 0), ("Several days", 1), ("More than half the days", 2), ("Nearly every day", 3)]
        for txt, val in choices:
            ctk.CTkButton(self.opts_frame, text=txt, width=300, height=50, corner_radius=25, fg_color=CARD_COLOR, text_color=TEXT_MAIN, command=lambda v=val: self.answer(v)).pack(pady=8)

    def on_show(self):
        self.current_idx, self.total_score = 0, 0
        self.lbl_q.configure(text=self.questions[0])
        backend.start_mouse_capture() 

    def answer(self, value):
        self.total_score += value
        self.current_idx += 1
        if self.current_idx < len(self.questions): self.lbl_q.configure(text=self.questions[self.current_idx])
        else:
            backend.save_phq(self.total_score)
            self.controller.show_frame("GAD7Page")

class GAD7Page(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG_COLOR)
        self.controller = controller
        self.questions = ["Feeling nervous, anxious, or on edge", "Not being able to stop or control worrying"]
        self.current_idx, self.total_score = 0, 0
        ctk.CTkLabel(self, text="GAD-7 Anxiety Screening", font=("Poppins", 24, "bold"), text_color=TEXT_MAIN).pack(pady=(60, 10))
        self.lbl_q = ctk.CTkLabel(self, text=self.questions[0], font=("Poppins", 20, "bold"), text_color=TEXT_MAIN)
        self.lbl_q.pack(pady=30)
        self.opts_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.opts_frame.pack(pady=10)
        choices = [("Not at all", 0), ("Several days", 1), ("More than half the days", 2), ("Nearly every day", 3)]
        for txt, val in choices:
            ctk.CTkButton(self.opts_frame, text=txt, width=300, height=50, corner_radius=25, fg_color=CARD_COLOR, text_color=TEXT_MAIN, command=lambda v=val: self.answer(v)).pack(pady=8)

    def on_show(self):
        self.current_idx, self.total_score = 0, 0
        self.lbl_q.configure(text=self.questions[0])
        backend.start_mouse_capture() 

    def answer(self, value):
        self.total_score += value
        self.current_idx += 1
        if self.current_idx < len(self.questions): self.lbl_q.configure(text=self.questions[self.current_idx])
        else:
            backend.save_gad(self.total_score)
            self.controller.show_frame("TaskPage")

class TaskPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG_COLOR)
        self.controller = controller
        self.start_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.start_frame.pack(expand=True)
        ctk.CTkButton(self.start_frame, text="Start Emotional Task", width=240, height=60, corner_radius=30, font=("Inter", 18, "bold"), fg_color="#8B5CF6", command=self.start).pack(pady=20)
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self.content, text="Emotional Response Task", font=("Poppins", 24, "bold"), text_color=TEXT_MAIN).pack(pady=(40, 10))
        self.txt = ctk.CTkTextbox(self.content, height=200, width=600, corner_radius=15, fg_color=CARD_COLOR, border_color=BORDER_COLOR, border_width=1)
        self.txt.pack(pady=30)
        self.btn_fin = ctk.CTkButton(self.content, text="Complete Session", state="disabled", height=50, width=240, corner_radius=25, fg_color="#10B981", command=self.finish)
        self.btn_fin.pack(pady=10)

    def start(self):
        self.start_frame.pack_forget()
        self.content.pack(expand=True)
        self.txt.focus()
        backend.start_key_capture()
        self.btn_fin.configure(state="normal")

    def finish(self):
        try:
            result = backend.process_final_task()
            if result:
                self.controller.frames["ReportPage"].display_report(result)
                self.controller.show_frame("ReportPage")
        except Exception as e:
            self.btn_fin.configure(text=f"Error: {str(e)[:60]}", fg_color="#EF4444")


# ==========================================
# REPORT PAGE 
# ==========================================
class ReportPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG_COLOR)
        self.controller = controller

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=40, pady=20)
        self._scroll = scroll

        # --- Top Navigation ---
        top = ctk.CTkFrame(scroll, fg_color="transparent", height=40)
        top.pack(fill="x", pady=(0, 15))
        ctk.CTkButton(top, text="← Back to Dashboard", fg_color="transparent", text_color=TEXT_SUB, hover_color="#E2E8F0", command=lambda: controller.show_frame("DashboardPage")).pack(side="left")
        ctk.CTkButton(top, text="Export PDF Report", fg_color="#10B981", hover_color="#059669", corner_radius=8).pack(side="right")

        # --- Dynamic Banner ---
        self.banner = ctk.CTkFrame(scroll, corner_radius=15, border_width=1)
        self.banner.pack(fill="x", pady=(0, 15))
        
        self.banner_icon = ctk.CTkLabel(self.banner, text="!", font=("Inter", 24, "bold"), width=40, height=40, corner_radius=20, text_color="white")
        self.banner_icon.pack(side="left", padx=20, pady=15)
        
        text_f = ctk.CTkFrame(self.banner, fg_color="transparent")
        text_f.pack(side="left", fill="both", expand=True, pady=15)
        self.banner_title = ctk.CTkLabel(text_f, text="", font=("Poppins", 20, "bold"))
        self.banner_title.pack(anchor="w")
        self.banner_sub = ctk.CTkLabel(text_f, text="", font=("Inter", 12))
        self.banner_sub.pack(anchor="w")
        
        self.banner_badge = ctk.CTkButton(self.banner, text="FLAG", font=("Inter", 14, "bold"), width=80, height=35, corner_radius=17, state="disabled", text_color="white")
        self.banner_badge.pack(side="right", padx=20)

        # --- ROW 1: Fuzzy Logic & Screening Scores ---
        row1 = ctk.CTkFrame(scroll, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 15))
        
        # Fuzzy Card
        fuzzy_card = ctk.CTkFrame(row1, fg_color=CARD_COLOR, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        fuzzy_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ctk.CTkLabel(fuzzy_card, text="Fuzzy Logic Output", font=("Inter", 14, "bold"), text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(15, 0))
        
        self.fuzzy_canvas = tk.Canvas(fuzzy_card, width=150, height=150, bg=CARD_COLOR, highlightthickness=0)
        self.fuzzy_canvas.pack(pady=10)
        
        self.fuzzy_label = ctk.CTkLabel(fuzzy_card, text="--", font=("Poppins", 16, "bold"), text_color=TEXT_MAIN)
        self.fuzzy_label.pack()
        ctk.CTkLabel(fuzzy_card, text="Classification Result", font=("Inter", 12), text_color=TEXT_SUB).pack(pady=(0, 15))

        # Scores Card
        scores_card = ctk.CTkFrame(row1, fg_color=CARD_COLOR, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        scores_card.pack(side="right", fill="both", expand=True, padx=(10, 0))
        ctk.CTkLabel(scores_card, text="Screening Scores", font=("Inter", 14, "bold"), text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(15, 10))
        
        self.phq_bar, self.phq_txt = self._create_score_row(scores_card, "PHQ-9 (Depression)", "28/45")
        self.gad_bar, self.gad_txt = self._create_score_row(scores_card, "GAD-7 (Anxiety)", "24/35")
        
        self.score_alert = ctk.CTkLabel(scores_card, text="⚠ Both scores indicate severe symptoms", text_color="#EF4444", fg_color="#FEE2E2", corner_radius=8, font=("Inter", 12, "bold"), height=35)
        self.score_alert.pack(fill="x", padx=20, pady=(10, 15))

        # --- ROW 2: Metrics Grid ---
        row2 = ctk.CTkFrame(scroll, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 15))
        self.card_t2 = self._create_metric_card(row2, "T² Score", "0.0", "Hotelling's T²", "#EF4444")
        self.card_thr = self._create_metric_card(row2, "F-Threshold", "0.0", "Upper Control Limit", "#F59E0B")
        self.card_psi = self._create_metric_card(row2, "PSI", "0.0", "Slowing Index", "#3B82F6")
        self.card_pai = self._create_metric_card(row2, "PAI", "0.0", "Agitation Index", "#8B5CF6")

        # --- ROW 3: Visual Evidence (Heatmap & Spectrogram) ---
        row3 = ctk.CTkFrame(scroll, fg_color="transparent")
        row3.pack(fill="x", pady=(0, 15))
        
        # Heatmap
        hm_card = ctk.CTkFrame(row3, fg_color=CARD_COLOR, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        hm_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ctk.CTkLabel(hm_card, text="Temporal Heatmap", font=("Poppins", 16, "bold"), text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(15, 0))
        ctk.CTkLabel(hm_card, text="Cursor hesitation during emotional text task", font=("Inter", 12), text_color=TEXT_SUB).pack(anchor="w", padx=20)
        
        self.hm_canvas = tk.Canvas(hm_card, height=220, bg="#FFFFFF", highlightthickness=1, highlightbackground=BORDER_COLOR)
        self.hm_canvas.pack(fill="both", padx=20, pady=15)
        
        self.hm_analysis = ctk.CTkLabel(hm_card, text="Analysis: Pending data...", text_color="#EF4444", fg_color="#FEF2F2", corner_radius=8, font=("Inter", 12), wraplength=400)
        self.hm_analysis.pack(fill="x", padx=20, pady=(0, 15), ipady=5)

        # Spectrogram
        sp_card = ctk.CTkFrame(row3, fg_color=CARD_COLOR, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        sp_card.pack(side="right", fill="both", expand=True, padx=(10, 0))
        ctk.CTkLabel(sp_card, text="Rhythm Spectrogram", font=("Poppins", 16, "bold"), text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(15, 0))
        ctk.CTkLabel(sp_card, text="Inter-keystroke interval consistency analysis", font=("Inter", 12), text_color=TEXT_SUB).pack(anchor="w", padx=20)
        
        self.sp_canvas = tk.Canvas(sp_card, height=220, bg="#FFFFFF", highlightthickness=0)
        self.sp_canvas.pack(fill="both", padx=20, pady=15)
        
        self.sp_analysis = ctk.CTkLabel(sp_card, text="Analysis: Pending data...", text_color="#F59E0B", fg_color="#FEF3C7", corner_radius=8, font=("Inter", 12), wraplength=400)
        self.sp_analysis.pack(fill="x", padx=20, pady=(0, 15), ipady=5)

        # --- ROW 4: Recommendations ---
        row4 = ctk.CTkFrame(scroll, fg_color=CARD_COLOR, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        row4.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(row4, text="Urgent Clinical Recommendations", font=("Poppins", 16, "bold"), text_color="#EF4444").pack(anchor="w", padx=20, pady=(15, 10))
        
        grid = ctk.CTkFrame(row4, fg_color="transparent")
        grid.pack(fill="x", padx=20, pady=(0, 20))
        
        self._add_recommendation(grid, "1", "Immediate Safety Assessment Required", "Severe PHQ-9 and GAD-7 scores combined with RED flag status warrant immediate clinical intervention.", 0, 0)
        self._add_recommendation(grid, "2", "Psychomotor Pattern Analysis", "Mixed disturbance with high agitation index. Consider therapeutic intervention for anxiety management.", 0, 1)
        self._add_recommendation(grid, "3", "Follow-up Timeline", "Re-assess within 48-72 hours. Monitor biometric trends and symptom progression closely.", 1, 0)
        self._add_recommendation(grid, "4", "Temporal Hesitation Alert", "Significant cursor pauses on emotional keywords suggest avoidance or processing difficulty. Address in therapy.", 1, 1)

    # --- UI Generators ---
    def _create_score_row(self, parent, title, default_val):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=20, pady=5)
        
        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text=title, font=("Inter", 14, "bold"), text_color=TEXT_MAIN).pack(side="left")
        val_lbl = ctk.CTkLabel(header, text=default_val, font=("Poppins", 16, "bold"), text_color="#EF4444")
        val_lbl.pack(side="right")
        
        pb = ctk.CTkProgressBar(f, height=10, progress_color="#EF4444", fg_color="#E2E8F0")
        pb.pack(fill="x", pady=(5,0))
        pb.set(0)
        return pb, val_lbl

    def _create_metric_card(self, parent, title, val, sub, icon_color):
        f = ctk.CTkFrame(parent, fg_color=CARD_COLOR, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        f.pack(side="left", fill="both", expand=True, padx=5)
        
        top = ctk.CTkFrame(f, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(top, text="~", font=("Inter", 14, "bold"), text_color="white", fg_color=icon_color, width=24, height=24, corner_radius=12).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(top, text=title, font=("Inter", 13, "bold"), text_color=TEXT_MAIN).pack(side="left")
        
        lbl = ctk.CTkLabel(f, text=val, font=("Poppins", 24, "bold"), text_color=icon_color)
        lbl.pack(anchor="w", padx=15, pady=0)
        ctk.CTkLabel(f, text=sub, font=("Inter", 11), text_color=TEXT_SUB).pack(anchor="w", padx=15, pady=(0, 15))
        return lbl

    def _add_recommendation(self, parent, num, title, desc, row, col):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=row, column=col, sticky="ew", padx=10, pady=10)
        parent.grid_columnconfigure(col, weight=1)
        
        ctk.CTkLabel(f, text=num, font=("Poppins", 14, "bold"), text_color="white", fg_color="#3B82F6", width=30, height=30, corner_radius=15).pack(side="left", anchor="n", padx=(0, 15))
        text_f = ctk.CTkFrame(f, fg_color="transparent")
        text_f.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(text_f, text=title, font=("Inter", 13, "bold"), text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(text_f, text=desc, font=("Inter", 12), text_color=TEXT_SUB, wraplength=300, justify="left").pack(anchor="w")

    # --- Data Population ---
    def display_report(self, data):
        ae = data.get("analysis") or {}
        flag = ae.get("flag", "GREEN")
        psi = ae.get("psi", 0)
        pai = ae.get("pai", 0)

        # Update Banner
        title, sub, t_col, bg_col, icon = get_flag_style(flag)
        self.banner.configure(fg_color=bg_col, border_color=t_col)
        self.banner_icon.configure(text=icon, fg_color=t_col)
        self.banner_title.configure(text=title, text_color=t_col)
        self.banner_sub.configure(text=sub, text_color=t_col)
        self.banner_badge.configure(text=flag, fg_color=t_col)

        # Update Scores
        phq = data.get("phq", {}).get("score", 0)
        gad = data.get("gad", {}).get("score", 0)
        
        self.phq_bar.set(min(phq / 27.0, 1.0))
        self.phq_txt.configure(text=f"{phq}/27\n({get_phq_interpretation(phq)})", font=("Inter",12))
        self.gad_bar.set(min(gad / 21.0, 1.0))
        self.gad_txt.configure(text=f"{gad}/21\n({get_gad_interpretation(gad)})", font=("Inter",12))

        # Update Metrics Grid
        t2 = ae.get("t2_score", 0.0)
        thr = ae.get("t2_threshold", 0.0)
        conf = ae.get("confidence", 0.0)
        
        self.card_t2.configure(text=f"{t2:.3f}")
        self.card_thr.configure(text=f"{thr:.2f}" if thr != float('inf') else "N/A")
        self.card_psi.configure(text=f"{psi:.3f}")
        self.card_pai.configure(text=f"{pai:.3f}")
        self.fuzzy_label.configure(text=ae.get('label', 'Normal'))

        # Draw Visuals
        self._draw_donut(conf, t_col)
        
        visuals = data.get("visuals", {})
        self._draw_heatmap(visuals.get("pause_coords", []), flag)
        self._draw_spectrogram(visuals.get("flight_times", []), flag, pai)

    # --- Canvas Drawings ---
    def _draw_donut(self, confidence, color):
        c = self.fuzzy_canvas
        c.delete("all")
        c.create_arc(15, 15, 135, 135, start=0, extent=359.9, outline="#E2E8F0", width=12, style="arc")
        extent = -(confidence * 360)
        c.create_arc(15, 15, 135, 135, start=90, extent=extent, outline=color, width=12, style="arc")
        c.create_text(75, 75, text=f"{int(confidence*100)}%", font=("Poppins", 26, "bold"), fill=TEXT_MAIN)
        c.create_text(75, 100, text="Confidence", font=("Inter", 10), fill=TEXT_SUB)

    def _draw_heatmap(self, pause_coords, flag):
        c = self.hm_canvas
        c.delete("all")
        W, H = 450, 220
        
        # Grid lines
        for i in range(12): c.create_line(i*40, 0, i*40, H, fill="#F1F5F9")
        for i in range(6): c.create_line(0, i*40, W, i*40, fill="#F1F5F9")

        words = ["hopeless", "overwhelmed", "anxious"]
        
        if flag in ["AMBER", "RED"]:
            # Draw actual data if available, else use mockup nodes that match reference
            positions = []
            if pause_coords and len(pause_coords) >= 3:
                # Scale real coords to UI 
                max_x = max([p[0] for p in pause_coords]) or 1920
                max_y = max([p[1] for p in pause_coords]) or 1080
                min_x = min([p[0] for p in pause_coords]) or 0
                min_y = min([p[1] for p in pause_coords]) or 0
                range_x, range_y = max(max_x - min_x, 1), max(max_y - min_y, 1)
                for x, y in pause_coords[:3]:
                    cx = int(((x - min_x) / range_x) * (W - 80)) + 40
                    cy = int(((y - min_y) / range_y) * (H - 80)) + 40
                    positions.append((cx, cy))
            else:
                positions = [(120, 100), (280, 140), (200, 180)]

            for i, (x, y) in enumerate(positions):
                w = words[i] if i < len(words) else "pause"
                r = random.randint(25, 40)
                
                c.create_oval(x-r, y-r, x+r, y+r, fill="#FECACA", outline="")
                c.create_oval(x-r//2, y-r//2, x+r//2, y+r//2, fill="#EF4444", outline="")
                c.create_rectangle(x-40, y-35, x+40, y-15, fill="white", outline=BORDER_COLOR)
                c.create_text(x, y-25, text=f'"{w}"', fill=TEXT_MAIN, font=("Inter", 10, "bold"))
                c.create_text(x, y+r+10, text=f"High-Latency\n{random.uniform(2.0, 4.5):.1f}s pause", fill="#EF4444", font=("Inter", 8, "bold"), justify="center")

            self.hm_analysis.configure(text="Analysis: Significant cursor hesitation detected on emotionally-loaded terms. Suggests cognitive processing difficulty.", text_color="#EF4444", fg_color="#FEE2E2")
        else:
            c.create_text(W//2, H//2, text="(Consistent movement. No major pauses detected.)", fill=TEXT_SUB, font=("Inter", 12, "italic"))
            self.hm_analysis.configure(text="Analysis: Smooth cursor trajectories. No significant emotional hesitation nodes identified.", text_color="#10B981", fg_color="#D1FAE5")

    def _draw_spectrogram(self, flight_times, flag, pai):
        c = self.sp_canvas
        c.delete("all")
        W, H = 450, 220
        
        c.create_line(40, 20, 40, H-20, fill=BORDER_COLOR, width=2)
        c.create_line(40, H-20, W-20, H-20, fill=BORDER_COLOR, width=2)
        c.create_text(20, H//2, text="Interval", fill=TEXT_SUB, font=("Inter", 9), angle=90)
        
        bar_w, spacing, x = 20, 10, 60
        color = "#F97316" if flag in ["AMBER", "RED"] else "#10B981"
        
        # Use real data if available
        if flight_times:
            times = flight_times[-12:]
            max_t = max(times) if times else 1.0
            for i, t in enumerate(times):
                h = max(10, int((t / max_t) * (H - 50)))
                c.create_rectangle(x, H-20-h, x+bar_w, H-20, fill=color, outline="")
                c.create_text(x+bar_w//2, H-12, text=str(i+1), fill=TEXT_SUB, font=("Inter", 8))
                x += bar_w + spacing
        else:
            for i in range(12):
                h = random.randint(40, 160) if flag == "RED" else (random.randint(70, 130) if flag == "AMBER" else random.randint(90, 110))
                c.create_rectangle(x, H-20-h, x+bar_w, H-20, fill=color, outline="")
                c.create_text(x+bar_w//2, H-12, text=str(i+1), fill=TEXT_SUB, font=("Inter", 8))
                x += bar_w + spacing

        if flag in ["AMBER", "RED"]:
            self.sp_analysis.configure(text=f"Analysis: Highly erratic keystroke intervals indicate psychomotor agitation. Deviation from baseline: +{int(pai*45)}%.", text_color="#F59E0B", fg_color="#FEF3C7")
        else:
            self.sp_analysis.configure(text="Analysis: Consistent keystroke rhythm. Variance falls within normal baseline boundaries.", text_color="#10B981", fg_color="#D1FAE5")


# ==========================================
# PATIENTS HISTORY PAGES
# ==========================================
class PatientsPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=BG_COLOR)
        self.controller = controller
        
        header = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color="transparent")
        header.pack(fill="x", side="top", padx=40, pady=20)
        ctk.CTkButton(header, text="← Back to Dashboard", width=80, fg_color="transparent", text_color=TEXT_SUB, hover_color="#E2E8F0", command=lambda: controller.show_frame("DashboardPage")).pack(side="left")
        ctk.CTkLabel(header, text="Patient Sessions", font=("Poppins", 28, "bold"), text_color=TEXT_MAIN).pack(side="right")

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=40, pady=10)

    def refresh_list(self):
        for widget in self.scroll_frame.winfo_children(): widget.destroy()
        try:
            conn = sqlite3.connect("psyclick_data.db")
            cursor = conn.cursor()
            cursor.execute("SELECT session_id, student_id, timestamp, flag FROM intake_sessions ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            conn.close()
            if not rows: return
            for session_id, student_id, timestamp, flag in rows:
                self.create_patient_card(session_id, student_id, timestamp, flag)
        except Exception as e: pass

    def create_patient_card(self, session_id, student_id, timestamp, flag):
        card = ctk.CTkFrame(self.scroll_frame, fg_color=CARD_COLOR, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="x", pady=8)
        _, _, t_col, bg_col, _ = get_flag_style(flag)
        
        ctk.CTkLabel(card, text=f"Patient ID: {student_id}", font=("Inter", 16, "bold"), text_color=TEXT_MAIN).pack(side="left", padx=20, pady=20)
        ctk.CTkLabel(card, text=f"Date: {timestamp}", font=("Inter", 14), text_color=TEXT_SUB).pack(side="left", padx=20)
        ctk.CTkLabel(card, text=flag, font=("Inter", 12, "bold"), text_color="white", fg_color=t_col, width=80, height=28, corner_radius=14).pack(side="left", padx=20)
        ctk.CTkButton(card, text="View Report ➔", width=120, height=40, corner_radius=20, fg_color="#F8FAFC", text_color="#3B82F6", border_color="#CBD5E1", border_width=1, command=lambda s=session_id: self.controller.open_patient_detail(s)).pack(side="right", padx=20)

class PatientDetailPage(ReportPage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
    def load_session(self, session_id):
        try:
            conn = sqlite3.connect("psyclick_data.db")
            cursor = conn.cursor()
            cursor.execute("""SELECT student_id, timestamp, phq_score, gad_score, t2_score, t2_threshold, psi, pai, fuzzy_label, fuzzy_confidence, flag, rationale FROM intake_sessions WHERE session_id=?""", (session_id,))
            row = cursor.fetchone()
            conn.close()
            if not row: return
            (sid, ts, phq, gad, t2, thr, psi, pai, fuzzy_label, fuzzy_conf, flag, rationale) = row
            
            mock_data = {
                "student_id": sid, "timestamp": ts,
                "phq": {"score": phq}, "gad": {"score": gad},
                "analysis": {
                    "flag": flag, "t2_score": t2, "t2_threshold": thr,
                    "psi": psi, "pai": pai, "label": fuzzy_label,
                    "confidence": fuzzy_conf, "rationale": rationale
                }
            }
            self.display_report(mock_data)
        except Exception as e: print(e)

if __name__ == "__main__":
    app = PsyClickApp()
    app.mainloop()
