import customtkinter as ctk
from backend_controller import PsyClickController
import math
import sqlite3
from datetime import datetime

backend = PsyClickController()
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- HELPER: Score Interpretation Logic ---
def get_phq_interpretation(score):
    if 0 <= score <= 4: return "None to minimal depression"
    elif 5 <= score <= 9: return "Mild depression"
    elif 10 <= score <= 14: return "Moderate depression"
    elif 15 <= score <= 19: return "Moderately severe depression"
    elif 20 <= score <= 27: return "Severe depression"
    return "Invalid Score"

def get_gad_interpretation(score):
    if 0 <= score <= 4: return "No to Minimal symptoms"
    elif 5 <= score <= 9: return "Mild symptoms"
    elif 10 <= score <= 14: return "Moderate symptoms"
    elif 15 <= score <= 21: return "Severe symptoms"
    return "Invalid Score"

def get_z_interpretation(z_score):
    """Returns (Status Text, Color Code)"""
    abs_z = abs(z_score)
    if abs_z <= 2.0:
        return "✅ Within Normal Range", "#00ff00"  # Green
    elif abs_z <= 3.0:
        return "⚠ Elevated Psychomotor Change", "#ffbf00"  # Amber
    else:
        return "⛔ Critical Psychomotor Change", "#ff4d4d"  # Red


class PsyClickApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PsyClick v1.0 - Clinical Decision Support")
        self.is_fullscreen = True
        self.attributes("-fullscreen", True)
        self.bind("<Escape>", self.toggle_fullscreen)

        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        self.frames = {}
        
        # Register all pages 
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
        # Trigger page specific load methods if they exist
        if hasattr(frame, 'on_show'):
            frame.on_show()

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
        # Pass the session_id to load specific data
        page = self.frames["PatientDetailPage"]
        page.load_session(session_id)
        self.show_frame("PatientDetailPage")

# --- LOGIN & DASHBOARD (Standard) ---
class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller 


        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(expand=True)
        logo_frame = ctk.CTkFrame(content, fg_color="transparent")
        logo_frame.pack(pady=80)
        ctk.CTkLabel(logo_frame, text="PsyClick", font=("Roboto", 40, "bold")).pack()
        ctk.CTkLabel(logo_frame, text="Clinical Decision Support System", font=("Arial", 14)).pack()
        box = ctk.CTkFrame(content, width=300, height=200, corner_radius=15, border_width=2, border_color="#3b3b3b")
        box.pack(pady=20)
        self.user = ctk.CTkEntry(box, placeholder_text="Clinician ID", width=250)
        self.user.pack(pady=15, padx=20)
        self.pwd = ctk.CTkEntry(box, placeholder_text="Password", show="*", width=250)
        self.pwd.pack(pady=10, padx=20)

        # Error message for invalid credentials
        self.lbl_error = ctk.CTkLabel(box, text="", text_color="red", font=("Arial", 12))
        self.lbl_error.pack(pady=0)

        # Sign in button
        ctk.CTkButton(box, text="Sign In", width=250, command=self.login_check).pack(pady=20)
        ctk.CTkLabel(self, text="v1.0.0-Beta | Local Mode (Secure)", text_color="gray").pack(side="bottom", pady=10)

    def login_check(self):
        """Validates credentials before transitioning."""
        user_names = {
        "202312480": "Dr. Anonuevo",
        "202310964": "Dr. Huertas",
        "202311990": "Dr. Tablate",
        "202310557": "Dr. Ballano"
    }
        if self.user.get() in user_names and self.pwd.get() == "12345":
            self.lbl_error.configure(text="") # Clear errors

            display_name = user_names[self.user.get()]
            self.controller.frames["DashboardPage"].welcome_label.configure(text=f"Welcome, {display_name}!")

            # Clear the entry fields
            self.user.delete(0, "end")
            self.pwd.delete(0, "end")

            self.controller.show_frame("DashboardPage")
        else:
            self.lbl_error.configure(text="Invalid Clinician ID or Password")



class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        ctk.CTkLabel(sidebar, text="PsyClick", font=("Roboto", 20, "bold")).pack(pady=20)
        ctk.CTkButton(sidebar, text="Dashboard", fg_color="#1f538d").pack(pady=10, padx=10)
        ctk.CTkButton(sidebar, text="Patients", fg_color="transparent", command=controller.open_patients).pack(pady=10, padx=10)

        def do_logout(controller):
                controller.show_frame("LoginPage") 
                login_page = controller.frames["LoginPage"] 
                login_page.focus_set()

        ctk.CTkButton(sidebar, text="Logout", fg_color="transparent", text_color="red", command=lambda: do_logout(controller)).pack(side="bottom", pady=20)
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(side="right", fill="both", expand=True, padx=30, pady=30)
        center = ctk.CTkFrame(main, fg_color="transparent")
        center.pack(expand=True)
        self.welcome_label = ctk.CTkLabel(center, text="Welcome!", font=("Arial", 28))
        self.welcome_label.pack(pady=10)
        
        #  
        card = ctk.CTkFrame(center, width=350, height=200, corner_radius=15, border_width=2, border_color="#3b3b3b")
        #Increase the height of the card
        card.pack(pady=30)#
        
        card.pack_propagate(False)
        ctk.CTkLabel(card, text="Start New Session", font=("Arial", 18, "bold")).pack(pady=20)
        ctk.CTkButton(card, text="+ New Patient Intake", height=40, command=lambda: controller.show_frame("IntakePage")).pack(pady=20)

    def do_logout(controller):
        controller.show_frame("LoginPage") 
        login_page = controller.frames["LoginPage"] 
        login_page.focus_set()

class IntakePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(expand=True)
        ctk.CTkLabel(self, text="New Patient Intake", font=("Arial", 24)).pack(pady=40)
        form = ctk.CTkFrame(content)
        form.pack(pady=10)
        self.entry_id = ctk.CTkEntry(form, placeholder_text="Patient ID (e.g. 2026-001)", width=300)
        self.entry_id.pack(pady=10, padx=20)
    
        # 1. Create a variable to track the checkbox state
        self.consent_var = ctk.BooleanVar(value=False)
        self.checkbox = ctk.CTkCheckBox(form, text="Digital Consent Signed", 
                                        variable=self.consent_var, 
                                        command=self.toggle_button)
        self.checkbox.pack(pady=10)
        
        # 2. Initialize button in "disabled" state
        self.btn_submit = ctk.CTkButton(content, text="Start Calibration", 
                                        state="disabled", 
                                        command=self.submit)
        self.btn_submit.pack(pady=20)
        
        ctk.CTkButton(content, text="Cancel", fg_color="gray", 
                      command=lambda: controller.show_frame("DashboardPage")).pack()

    # Toggle button state based on consent checkbox
    def toggle_button(self):
        """Enables the button only if consent is checked."""
        if self.consent_var.get():
            self.btn_submit.configure(state="normal")
        else:
            self.btn_submit.configure(state="disabled")

    def submit(self):
        pid = self.entry_id.get()
        if pid:
            backend.set_student_id(pid)
            self.controller.show_frame("KCalibrationPage")



# START HERE JON
# --- 1. KEYBOARD CALIBRATION ---
class KCalibrationPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.start_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.start_frame.pack(expand=True)
        ctk.CTkButton(
            self.start_frame, 
            text="Start Calibration", 
            width=240, height=80, 
            font=("Arial", 26, "bold"), 
            command=self.start
            ).pack(expand=True)
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self.content, text="Calibration Phase", font=("Arial", 20)).pack(pady=20)
        ctk.CTkLabel(self.content, text="Please type the following standard text:", font=("Arial", 14)).pack(pady=5)
        self.target_text = "The quick brown fox jumps over the lazy dog..."
        ctk.CTkLabel(self.content, text=self.target_text, font=("Courier", 18), text_color="#4a90e2").pack(pady=10)
        self.txt = ctk.CTkTextbox(self.content, height=100, width=500)
        self.txt.pack(pady=20)
        self.btn_next = ctk.CTkButton(self.content, text="Next >", state="disabled", command=self.next_step)
        self.btn_next.pack(pady=5)

    def start(self):
        self.start_frame.pack_forget()
        self.content.pack(expand=True)
        self.txt.focus()
        backend.start_key_capture()
        self.btn_next.configure(state="normal")
    
    def next_step(self):
        success = backend.save_kbase()
        if success:
            self.controller.show_frame("MCalibrationPage")



# --- 2. MOUSE CALIBRATION ---
class MCalibrationPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ctk.CTkLabel(self, text="Step 2: Mouse Calibration", font=("Arial", 20)).pack(pady=20)
        ctk.CTkLabel(self, text="Please answer the following question:", font=("Arial", 16)).pack(pady=10)
        
        self.lbl_q = ctk.CTkLabel(self, text="What colour are your shoes?", font=("Arial", 18, "bold"))
        self.lbl_q.pack(pady=20)
        
        # Container for buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=10)
        
        # We need to start capture BEFORE they click answers.
        self.start_btn = ctk.CTkButton(self, text="Start Calibration", command=self.enable_options)
        self.start_btn.pack(pady=30)

        # Sign-off instruction at the bottom
        ctk.CTkLabel(self, text="*Please do not let go of the mouse until instructed*", text_color="red", font=("Arial", 12, "italic")).pack(side="bottom", pady=10)


    def enable_options(self):
        self.start_btn.pack_forget()
        backend.start_mouse_capture()
        
        options = ["Black", "White", "Brown", "Others"]
        for opt in options:
            ctk.CTkButton(self.btn_frame, text=opt, width=150, height=40,
                          command=self.record_and_next).pack(pady=10)

    def record_and_next(self):
        if backend.save_mbase():
            self.controller.show_frame("PHQ9Page")

# --- 3. PHQ-9 WIZARD ---
class PHQ9Page(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.questions = [
            "Little interest or pleasure in doing things",
            "Feeling down, depressed or hopeless",
            "Trouble falling asleep or staying asleep or sleeping too much",
            "Feeling tired or having little energy",
            "Poor appetite or overeating",
            "Feeling bad about yourself, or that you are a failure",
            "Difficulty concentrating on things",
            "Moving or speaking so slowly that other people could have noticed",
            "Thoughts that you would be better off dead"
        ]
        self.current_idx = 0
        self.total_score = 0
        
        ctk.CTkLabel(self, text="PHQ-9 Assessment", font=("Arial", 20, "bold")).pack(pady=20)
        ctk.CTkLabel(self, text="Over the last two weeks, how often have you been bothered by:", font=("Arial", 14, "bold")).pack(pady=5)
        
        self.lbl_q = ctk.CTkLabel(self, text=self.questions[0], font=("Arial", 18), wraplength=600)
        self.lbl_q.pack(pady=30)
        
        self.opts_frame = ctk.CTkFrame(self)
        self.opts_frame.pack(pady=20)
        
        choices = [("Not at all", 0), ("Several days", 1), ("More than half", 2), ("Nearly every day", 3)]
        for txt, val in choices:
            ctk.CTkButton(self.opts_frame, text=txt, width=200, height=40,
                          command=lambda v=val: self.answer(v)).pack(pady=5)

    def on_show(self):
        self.current_idx = 0
        self.total_score = 0
        self.lbl_q.configure(text=self.questions[0])
        backend.start_mouse_capture() # Capture mouse dynamics for whole test

    def answer(self, value):
        self.total_score += value
        self.current_idx += 1
        if self.current_idx < len(self.questions):
            self.lbl_q.configure(text=self.questions[self.current_idx])
        else:
            backend.save_phq(self.total_score)
            self.controller.show_frame("GAD7Page")

# --- 4. GAD-7 WIZARD ---
class GAD7Page(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.questions = [
            "Feeling nervous, anxious, or on edge",
            "Not being able to stop or control worrying",
            "Worrying too much about different things",
            "Trouble relaxing",
            "Being so restless that it is hard to sit still",
            "Becoming easily annoyed or irritable",
            "Feeling afraid, as if something awful might happen"
        ]
        self.current_idx = 0
        self.total_score = 0
        
        ctk.CTkLabel(self, text="GAD-7 Assessment", font=("Arial", 20, "bold")).pack(pady=20)
        ctk.CTkLabel(self, text="Over the last two weeks, how often have you been bothered by:", font=("Arial", 14, "bold")).pack(pady=5)
        
        self.lbl_q = ctk.CTkLabel(self, text=self.questions[0], font=("Arial", 18), wraplength=600)
        self.lbl_q.pack(pady=30)
        
        self.opts_frame = ctk.CTkFrame(self)
        self.opts_frame.pack(pady=20)
        
        choices = [("Not at all", 0), ("Several days", 1), ("More than half", 2), ("Nearly every day", 3)]
        for txt, val in choices:
            ctk.CTkButton(self.opts_frame, text=txt, width=200, height=40,
                          command=lambda v=val: self.answer(v)).pack(pady=5)

    def on_show(self):
        self.current_idx = 0
        self.total_score = 0
        self.lbl_q.configure(text=self.questions[0])
        backend.start_mouse_capture() 

    def answer(self, value):
        self.total_score += value
        self.current_idx += 1
        if self.current_idx < len(self.questions):
            self.lbl_q.configure(text=self.questions[self.current_idx])
        else:
            backend.save_gad(self.total_score)
            self.controller.show_frame("TaskPage")

# --- 5. EMOTIONAL TASK ---
class TaskPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

         # Start Overlay (Same as Calibration)
        self.start_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.start_frame.pack(expand=True)
        ctk.CTkButton(
            self.start_frame, 
            text="Start Emotional Task", 
            width=240, height=80, 
            font=("Arial", 26, "bold"),
            command=self.start
        ).pack(expand=True)

        # Active Task Content
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self.content, text="Emotional Recall Task", font=("Arial", 20)).pack(pady=20)
        ctk.CTkLabel(self.content, text="Describe a recent time when you felt overwhelmed or anxious.", font=("Arial", 14)).pack(pady=5)
        
        self.txt = ctk.CTkTextbox(self.content, height=200, width=500)
        self.txt.pack(pady=20)
        
        self.btn_fin = ctk.CTkButton(self.content, text="Finish & Analyze", state="disabled", command=self.finish)
        self.btn_fin.pack(pady=5)

    def start(self):
        self.start_frame.pack_forget()
        self.content.pack(expand=True)
        self.txt.focus()
        backend.start_key_capture()
        self.btn_fin.configure(state="normal")

    def finish(self):
        result = backend.process_final_task()
        if result:
            self.controller.frames["ReportPage"].display_report(result)
            self.controller.show_frame("ReportPage")

# --- 6. REPORT PAGE ---

class ReportPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(expand=True)
        ctk.CTkLabel(self, text="Clinical Report", font=("Arial", 24, "bold")).pack(pady=30)
        
        self.stats_frame = ctk.CTkFrame(self)
        self.stats_frame.pack(pady=10, fill="x", padx=50)
        
        # We will populate this dynamically in display_report
        self.phq_label = ctk.CTkLabel(self.stats_frame, text="", font=("Arial", 16))
        self.phq_label.pack(pady=5)
        
        self.gad_label = ctk.CTkLabel(self.stats_frame, text="", font=("Arial", 16))
        self.gad_label.pack(pady=5)

        self.z_frame = ctk.CTkFrame(self)
        self.z_frame.pack(pady=10)

        # Canvas for Bell Curves
        self.canvas = ctk.CTkCanvas(self, width=900, height=600, bg="#2b2b2b", highlightthickness=2)
        self.canvas.pack(pady=20)
        
        ctk.CTkButton(self, text="Return to Dashboard", command=lambda: controller.show_frame("DashboardPage") ).pack(anchor="nw", padx=20, pady=20)

    def display_report(self, data):
        # 1. PHQ & GAD Scores and Interpretation
        phq_val = data.get('phq', {}).get('score', 0)
        gad_val = data.get('gad', {}).get('score', 0)
        
        phq_text = get_phq_interpretation(phq_val)
        gad_text = get_gad_interpretation(gad_val)
        
        self.phq_label.configure(text=f"PHQ-9: {phq_val} - {phq_text}")
        self.gad_label.configure(text=f"GAD-7: {gad_val} - {gad_text}")
        
        # 2. Extract Z-Scores and Interpret
        kz = data.get('k_z_score', 0)
        mz = data.get('m_z_score', 0)
        
        # Clear previous Z-info
        for widget in self.z_frame.winfo_children():
            widget.destroy()
            
        kz_txt, kz_col = get_z_interpretation(kz)
        mz_txt, mz_col = get_z_interpretation(mz)
        
        ctk.CTkLabel(self.z_frame, text=f"Keyboard Motor Z={kz:.2f}: {kz_txt}", text_color=kz_col, font=("Arial", 14, "bold")).pack(pady=2)
        ctk.CTkLabel(self.z_frame, text=f"Mouse Cognitive Z={mz:.2f}: {mz_txt}", text_color=mz_col, font=("Arial", 14, "bold")).pack(pady=2)
        
        # 3. Draw Visualizations
        self.draw_bell_curves(kz, mz)

    def draw_bell_curves(self, kz, mz):
        self.canvas.delete("all")
        w, h = 900, 600   # larger canvas
        margin = 100      # more breathing room
        center_y = h - margin

        def draw_curve(color, z_val, label, y_offset, buffer=40):
            baseline_y = center_y - y_offset
            scale = 80     # pixels per Z-score (was 50)

            # --- Grid lines ---
            for x in range(margin, w - margin + 1, scale):
                self.canvas.create_line(x, baseline_y - 180, x, baseline_y + 30, fill="#444", dash=(2, 2))
            for y in range(baseline_y - 180, baseline_y + 31, 60):
                self.canvas.create_line(margin, y, w - margin, y, fill="#444", dash=(2, 2))

            # --- Axis lines ---
            self.canvas.create_line(margin, baseline_y, w - margin, baseline_y, fill="white", width=2)
            self.canvas.create_line(margin, baseline_y - 180, margin, baseline_y + 30, fill="white", width=2)

            # --- Axis labels ---
            self.canvas.create_text(w/2, baseline_y + 50, text=f"{label} Z-Score", fill="white", font=("Arial", 16))
            self.canvas.create_text(margin - 70, baseline_y - 90, text="Density", fill="white", font=("Arial", 16), angle=90)

            # --- Tick marks (X-axis) ---
            for z in range(-5, 6):
                x = 450 + (z * scale)   # center shifted to 450
                self.canvas.create_line(x, baseline_y - 8, x, baseline_y + 8, fill="white")
                self.canvas.create_text(x, baseline_y + 30, text=str(z), fill="white", font=("Arial", 12))

            # --- Tick marks (Y-axis) ---
            for val in range(0, 121, 20):
                y = baseline_y - val
                self.canvas.create_line(margin - 8, y, margin + 8, y, fill="white")
                self.canvas.create_text(margin - 40, y, text=str(val), fill="white", font=("Arial", 12))

            # --- Normal distribution curve ---
            points = []
            for i in range(margin, w - margin + 1, 5):
                sigma = (i - 450) / scale
                y = 150 * math.exp(-0.5 * sigma**2)   # scaled taller
                points.extend([i, baseline_y - y])
            self.canvas.create_line(points, fill="gray", smooth=True)

            # --- User’s Z-score dot ---
            user_x = 450 + (z_val * scale)
            sigma = z_val
            y = 150 * math.exp(-0.5 * sigma**2)
            user_y = baseline_y - y

            self.canvas.create_oval(user_x - 8, user_y - 8, user_x + 8, user_y + 8, fill=color, outline="white")
            self.canvas.create_text(user_x, user_y - 20, text=f"{label}\nZ={z_val:.2f}", fill=color, anchor="s", font=("Arial", 12))

        
        # Keyboard Curve
        abs_kz = abs(kz)
        if abs_kz <= 2.0:
           draw_curve("#00ff00", kz, "Keyboard (Motor)", 250, buffer=40)  # Green
        elif abs_kz <= 3.0:
            draw_curve("#ffbf00", kz, "Keyboard (Motor)", 250, buffer=40) # Amber
        else:
            draw_curve("#ff4d4d", kz, "Keyboard (Motor)", 250, buffer=40) # Red

        # Mouse Curve
        abs_mz = abs(mz)
        if abs_mz <= 2.0:
           draw_curve("#00ff00", mz, "Mouse (Cognitive)", -30, buffer=40)  # Green
        elif abs_mz <= 3.0:
            draw_curve("#ffbf00", mz, "Mouse (Cognitive)", -30, buffer=40) # Amber
        else:
            draw_curve("#ff4d4d", mz, "Mouse (Cognitive)", -30, buffer=40) # Red



# --- PATIENTS PAGE (History) ---
class PatientsPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Header
        header = ctk.CTkFrame(self, height=60, corner_radius=0)
        header.pack(fill="x", side="top")
        ctk.CTkButton(header, text="< Back", width=80, fg_color="transparent", 
                      command=lambda: controller.show_frame("DashboardPage")).pack(side="left", padx=20)
        ctk.CTkLabel(header, text="Patient Sessions", font=("Arial", 22, "bold")).pack(side="left", padx=20)

        # List Area
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=30, pady=30)

    def refresh_list(self):
        # Clear existing items
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        # Connect to DB and fetch sessions
        try:
            conn = sqlite3.connect("psyclick_data.db")
            cursor = conn.cursor()
            cursor.execute("SELECT session_id, student_id, timestamp FROM intake_sessions ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                ctk.CTkLabel(self.scroll_frame, text="No patient sessions found.").pack(pady=20)
                return

            for session_id, student_id, timestamp in rows:
                self.create_patient_card(session_id, student_id, timestamp)
        except Exception as e:
            ctk.CTkLabel(self.scroll_frame, text=f"Error loading database: {e}").pack()

    def create_patient_card(self, session_id, student_id, timestamp):
        card = ctk.CTkFrame(self.scroll_frame, fg_color="#2b2b2b", corner_radius=10)
        card.pack(fill="x", pady=5)
        
        info_text = f"Patient ID: {student_id}  |  Date: {timestamp}"
        ctk.CTkLabel(card, text=info_text, font=("Arial", 14)).pack(side="left", padx=20, pady=15)
        
        ctk.CTkButton(card, text="View Report", width=100, 
                      command=lambda s=session_id: self.controller.open_patient_detail(s)).pack(side="right", padx=20)

# --- PATIENT DETAIL PAGE (Historical Report) ---
class PatientDetailPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # 1. Scrollable Container for the whole page
        self.main_scroll = ctk.CTkScrollableFrame(self)
        self.main_scroll.pack(fill="both", expand=True)

        # Header
        self.header_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=20, padx=20)
        ctk.CTkButton(self.header_frame, text="< Back to List", width=100, fg_color="#444", 
                      command=self.go_back).pack(side="left")
        
        self.title_lbl = ctk.CTkLabel(self.header_frame, text="Clinical Report", font=("Arial", 24, "bold"))
        self.title_lbl.pack(side="left", padx=20)

        # Info Box
        self.info_box = ctk.CTkFrame(self.main_scroll)
        self.info_box.pack(fill="x", padx=40, pady=10)
        self.lbl_details = ctk.CTkLabel(self.info_box, text="", font=("Courier", 16))
        self.lbl_details.pack(pady=10, padx=10)

        # Scores Area
        self.scores_frame = ctk.CTkFrame(self.main_scroll)
        self.scores_frame.pack(fill="x", padx=40, pady=10)

        # Canvas for Graphs
        self.canvas = ctk.CTkCanvas(self.main_scroll, width=900, height=600, bg="#2b2b2b", highlightthickness=2)
        self.canvas.pack(pady=20)

    def go_back(self):
        self.controller.open_patients()

    def load_session(self, session_id):
        # 1. Fetch Data
        try:
            conn = sqlite3.connect("psyclick_data.db")
            cursor = conn.cursor()
            # Fetch all needed columns
            cursor.execute('''
                SELECT student_id, timestamp, 
                       phq_score, gad_score, 
                       k_z_score, m_z_score 
                FROM intake_sessions WHERE session_id=?
            ''', (session_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                self.lbl_details.configure(text="Error: Session not found.")
                return

            sid, ts, phq, gad, kz, mz = row

            # 2. Update Info
            self.lbl_details.configure(text=f"Student ID: {sid}\nSession Date: {ts}")

            # 3. Update Scores & Interpretations
            # Clear previous widgets in scores_frame
            for widget in self.scores_frame.winfo_children():
                widget.destroy()

            # PHQ Interpretation
            phq_interp = get_phq_interpretation(phq)
            self.create_score_row("PHQ-9 (Depression)", phq, phq_interp)

            # GAD Interpretation
            gad_interp = get_gad_interpretation(gad)
            self.create_score_row("GAD-7 (Anxiety)", gad, gad_interp)

            # Z-Score Interpretations
            kz_txt, kz_col = get_z_interpretation(kz)
            mz_txt, mz_col = get_z_interpretation(mz)
            
            self.create_z_row("Motor Speed (Keyboard)", kz, kz_txt, kz_col)
            self.create_z_row("Cognitive Agitation (Mouse)", mz, mz_txt, mz_col)

            # 4. Draw Graphs
            self.draw_bell_curves(kz, mz)

        except Exception as e:
            self.lbl_details.configure(text=f"Database Error: {e}")

    def create_score_row(self, title, score, interp):
        row = ctk.CTkFrame(self.scores_frame, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text=f"{title}:", font=("Arial", 14, "bold"), width=200, anchor="w").pack(side="left")
        ctk.CTkLabel(row, text=f"{score}", font=("Arial", 14, "bold"), width=50).pack(side="left")
        ctk.CTkLabel(row, text=f"({interp})", font=("Arial", 14), text_color="cyan").pack(side="left", padx=10)

    def create_z_row(self, title, z_val, status_text, color):
        row = ctk.CTkFrame(self.scores_frame, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text=f"{title}:", font=("Arial", 14, "bold"), width=200, anchor="w").pack(side="left")
        ctk.CTkLabel(row, text=f"Z={z_val:.2f}", font=("Arial", 14), width=80).pack(side="left")
        ctk.CTkLabel(row, text=status_text, font=("Arial", 14, "bold"), text_color=color).pack(side="left", padx=10)




    def draw_bell_curves(self, kz, mz):
        self.canvas.delete("all")
        w, h = 900, 600   # larger canvas
        margin = 100      # more breathing room
        center_y = h - margin

        def draw_curve(color, z_val, label, y_offset, buffer=40):
            baseline_y = center_y - y_offset
            scale = 80     # pixels per Z-score (was 50)

            # --- Grid lines ---
            for x in range(margin, w - margin + 1, scale):
                self.canvas.create_line(x, baseline_y - 180, x, baseline_y + 30, fill="#444", dash=(2, 2))
            for y in range(baseline_y - 180, baseline_y + 31, 60):
                self.canvas.create_line(margin, y, w - margin, y, fill="#444", dash=(2, 2))

            # --- Axis lines ---
            self.canvas.create_line(margin, baseline_y, w - margin, baseline_y, fill="white", width=2)
            self.canvas.create_line(margin, baseline_y - 180, margin, baseline_y + 30, fill="white", width=2)

            # --- Axis labels ---
            self.canvas.create_text(w/2, baseline_y + 50, text=f"{label} Z-Score", fill="white", font=("Arial", 16))
            self.canvas.create_text(margin - 70, baseline_y - 90, text="Density", fill="white", font=("Arial", 16), angle=90)

            # --- Tick marks (X-axis) ---
            for z in range(-5, 6):
                x = 450 + (z * scale)   # center shifted to 450
                self.canvas.create_line(x, baseline_y - 8, x, baseline_y + 8, fill="white")
                self.canvas.create_text(x, baseline_y + 30, text=str(z), fill="white", font=("Arial", 12))

            # --- Tick marks (Y-axis) ---
            for val in range(0, 121, 20):
                y = baseline_y - val
                self.canvas.create_line(margin - 8, y, margin + 8, y, fill="white")
                self.canvas.create_text(margin - 40, y, text=str(val), fill="white", font=("Arial", 12))

            # --- Normal distribution curve ---
            points = []
            for i in range(margin, w - margin + 1, 5):
                sigma = (i - 450) / scale
                y = 150 * math.exp(-0.5 * sigma**2)   # scaled taller
                points.extend([i, baseline_y - y])
            self.canvas.create_line(points, fill="gray", smooth=True)

            # --- User’s Z-score dot ---
            user_x = 450 + (z_val * scale)
            sigma = z_val
            y = 150 * math.exp(-0.5 * sigma**2)
            user_y = baseline_y - y

            self.canvas.create_oval(user_x - 8, user_y - 8, user_x + 8, user_y + 8, fill=color, outline="white")
            self.canvas.create_text(user_x, user_y - 20, text=f"{label}\nZ={z_val:.2f}", fill=color, anchor="s", font=("Arial", 12))

        
        # Keyboard Curve
        abs_kz = abs(kz)
        if abs_kz <= 2.0:
           draw_curve("#00ff00", kz, "Keyboard (Motor)", 250, buffer=40)  # Green
        elif abs_kz <= 3.0:
            draw_curve("#ffbf00", kz, "Keyboard (Motor)", 250, buffer=40) # Amber
        else:
            draw_curve("#ff4d4d", kz, "Keyboard (Motor)", 250, buffer=40) # Red

        # Mouse Curve
        abs_mz = abs(mz)
        if abs_mz <= 2.0:
           draw_curve("#00ff00", mz, "Mouse (Cognitive)", -30, buffer=40)  # Green
        elif abs_mz <= 3.0:
            draw_curve("#ffbf00", mz, "Mouse (Cognitive)", -30, buffer=40) # Amber
        else:
            draw_curve("#ff4d4d", mz, "Mouse (Cognitive)", -30, buffer=40) # Red



if __name__ == "__main__":
    app = PsyClickApp()
    app.mainloop()