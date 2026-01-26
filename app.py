import customtkinter as ctk
import threading
from tkinter import messagebox

# IMPORT YOUR BACKEND MODULES
import database_manager as db
import dynamics_logger as dl
import feature_extractor as fe
import anomaly_engine as ae

# Configuration
ctk.set_appearance_mode("Dark")  # Matches your wireframe dark theme
ctk.set_default_color_theme("blue")

class PsyClickApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("PsyClick - Clinical Decision Support")
        self.geometry("1000x700")

        # Initialize Database
        db.init_db()
        
        # State Variables
        self.current_student_id = None
        self.logger = dl.KeyLogger()

        # container to stack frames (pages)
        self.container = ctk.CTkFrame(self)
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Dictionary to hold pages
        self.frames = {}

        # Initialize all pages defined below
        for F in (LoginPage, DashboardPage, PatientIntakePage, CalibrationPage, EmotionalTaskPage):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("LoginPage")

    def show_frame(self, page_name):
        """Bring a specific frame to the front"""
        frame = self.frames[page_name]
        frame.tkraise()
        
    def get_logger(self):
        return self.logger

# =========================================================
# PAGE 1: LOGIN SCREEN (Wireframe Pg 1)
# =========================================================
class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Layout based on Wireframe Page 1
        label = ctk.CTkLabel(self, text="PsyClick", font=("Roboto", 40, "bold"))
        label.pack(pady=40)

        entry_user = ctk.CTkEntry(self, placeholder_text="Clinician ID")
        entry_user.pack(pady=10)

        entry_pass = ctk.CTkEntry(self, placeholder_text="Password", show="*")
        entry_pass.pack(pady=10)

        btn_login = ctk.CTkButton(self, text="Sign In", command=lambda: controller.show_frame("DashboardPage"))
        btn_login.pack(pady=20)
        
        lbl_version = ctk.CTkLabel(self, text="v1.0.0-Beta | Local Mode (Secure)")
        lbl_version.pack(side="bottom", pady=20)

# =========================================================
# PAGE 2: DASHBOARD (Wireframe Pg 2)
# =========================================================
class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Sidebar
        sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        
        btn_dash = ctk.CTkButton(sidebar, text="Dashboard", fg_color="transparent", border_width=2)
        btn_dash.pack(pady=10, padx=10)
        
        btn_logout = ctk.CTkButton(sidebar, text="Logout", fg_color="red", 
                                   command=lambda: controller.show_frame("LoginPage"))
        btn_logout.pack(side="bottom", pady=20, padx=10)

        # Main Content
        content = ctk.CTkFrame(self)
        content.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        welcome_lbl = ctk.CTkLabel(content, text="Welcome, Dr. Dela Cruz!", font=("Arial", 24))
        welcome_lbl.pack(anchor="w")

        # "New Session" Button
        btn_new_patient = ctk.CTkButton(content, text="+ New Session", height=50,
                                        command=lambda: controller.show_frame("PatientIntakePage"))
        btn_new_patient.pack(pady=50)

# =========================================================
# PAGE 3: PATIENT INTAKE (Wireframe Pg 3)
# =========================================================
class PatientIntakePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ctk.CTkLabel(self, text="New Patient Intake", font=("Arial", 24)).pack(pady=20)

        self.entry_id = ctk.CTkEntry(self, placeholder_text="Patient ID (e.g., 2026-001)")
        self.entry_id.pack(pady=10)

        self.btn_start = ctk.CTkButton(self, text="Start Calibration", command=self.start_calibration)
        self.btn_start.pack(pady=20)
        
        ctk.CTkButton(self, text="Cancel", fg_color="gray", 
                      command=lambda: controller.show_frame("DashboardPage")).pack()

    def start_calibration(self):
        patient_id = self.entry_id.get()
        if not patient_id:
            return
        self.controller.current_student_id = patient_id
        self.controller.show_frame("CalibrationPage")

# =========================================================
# PAGE 6: CALIBRATION TASK (Wireframe Pg 6)
# =========================================================
class CalibrationPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.header = ctk.CTkLabel(self, text="Calibration Phase", font=("Arial", 20))
        self.header.pack(pady=20)

        instruction = "Please type the following standard text:\n\n'The quick brown fox jumps over the lazy dog...'"
        ctk.CTkLabel(self, text=instruction, font=("Arial", 16)).pack(pady=20)

        # Text Area for Typing
        self.txt_input = ctk.CTkTextbox(self, height=100, width=400)
        self.txt_input.pack(pady=10)
        
        # Start/Next Buttons
        self.btn_start = ctk.CTkButton(self, text="Start Recording", command=self.start_recording)
        self.btn_start.pack(pady=5)
        
        self.btn_next = ctk.CTkButton(self, text="Next >", state="disabled", command=self.finish_calibration)
        self.btn_next.pack(pady=5)

    def start_recording(self):
        self.txt_input.focus()
        self.controller.get_logger().start_logging() # CALLS YOUR BACKEND
        self.btn_start.configure(state="disabled")
        self.btn_next.configure(state="normal")

    def finish_calibration(self):
        # 1. Stop Logger
        raw_data = self.controller.get_logger().stop_logging() # CALLS YOUR BACKEND
        
        # 2. Extract Features
        features = fe.extract_features(raw_data)
        
        if features:
            # 3. Save Baseline to DB
            db.save_user_baseline(self.controller.current_student_id, 
                                  features['mean_flight'], 
                                  features['std_flight'])
            print(f"Baseline Saved: {features}")
            self.controller.show_frame("EmotionalTaskPage")
        else:
            print("Not enough data")
            # Reset UI
            self.btn_start.configure(state="normal")
            self.btn_next.configure(state="disabled")

# =========================================================
# PAGE 8: EMOTIONAL TASK (Wireframe Pg 8)
# =========================================================
class EmotionalTaskPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        ctk.CTkLabel(self, text="Emotional Recall Task", font=("Arial", 20)).pack(pady=20)
        ctk.CTkLabel(self, text="Describe a recent time when you felt overwhelmed.", font=("Arial", 14)).pack(pady=10)

        self.txt_input = ctk.CTkTextbox(self, height=200, width=500)
        self.txt_input.pack(pady=10)

        self.btn_start = ctk.CTkButton(self, text="Start Typing", command=self.start_analysis)
        self.btn_start.pack(pady=5)
        
        self.btn_finish = ctk.CTkButton(self, text="Finish & Analyze", state="disabled", command=self.finish_analysis)
        self.btn_finish.pack(pady=5)
        
        self.lbl_result = ctk.CTkLabel(self, text="", font=("Arial", 16, "bold"))
        self.lbl_result.pack(pady=20)

    def start_analysis(self):
        self.txt_input.focus()
        self.controller.get_logger().start_logging()
        self.btn_start.configure(state="disabled")
        self.btn_finish.configure(state="normal")

    def finish_analysis(self):
        # 1. Stop Logger
        raw_data = self.controller.get_logger().stop_logging()
        
        # 2. Extract Features
        features = fe.extract_features(raw_data)
        
        if features:
            # 3. Compare with Baseline (Anomaly Engine)
            z_score, is_anomaly = ae.analyze_session(self.controller.current_student_id, features)
            
            # 4. Save Session
            db.save_session(self.controller.current_student_id, features['mean_flight'], z_score, is_anomaly)
            
            # 5. Display Result on UI (Wireframe Page 9 concept)
            status = "NORMAL"
            color = "green"
            
            if is_anomaly:
                if z_score > 2.0:
                    status = "PSYCHOMOTOR SLOWING (Depression Risk)"
                    color = "red"
                elif z_score < -2.0:
                    status = "PSYCHOMOTOR AGITATION (Anxiety Risk)"
                    color = "orange"
            
            self.lbl_result.configure(text=f"Result: {status} (Z: {z_score:.2f})", text_color=color)
        
        # Reset
        self.btn_start.configure(state="normal")
        self.btn_finish.configure(state="disabled")

# Run App
if __name__ == "__main__":
    app = PsyClickApp()
    app.mainloop()