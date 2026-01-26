import customtkinter as ctk
from backend_controller import PsyClickController
import threading

# Initialize Controller
backend = PsyClickController()

# Configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class PsyClickApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PsyClick v1.0 - Clinical Decision Support")
        self.geometry("1100x700")

        # Container
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        self.frames = {}

        # Define all pages from Wireframe
        for F in (LoginPage, DashboardPage, IntakePage, CalibrationPage, TaskPage, ReportPage):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("LoginPage")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()

# --- PAGE 1: LOGIN ---
class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        
        # Logo Area
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(pady=80)
        ctk.CTkLabel(logo_frame, text="PsyClick", font=("Roboto", 40, "bold")).pack()
        ctk.CTkLabel(logo_frame, text="Clinical Decision Support System", font=("Arial", 14)).pack()

        # Login Box
        box = ctk.CTkFrame(self, width=300)
        box.pack(pady=20)
        
        self.user = ctk.CTkEntry(box, placeholder_text="Clinician ID", width=250)
        self.user.pack(pady=15, padx=20)
        
        self.pwd = ctk.CTkEntry(box, placeholder_text="Password", show="*", width=250)
        self.pwd.pack(pady=10, padx=20)

        ctk.CTkButton(box, text="Sign In", width=250, command=lambda: controller.show_frame("DashboardPage")).pack(pady=20)
        ctk.CTkLabel(self, text="v1.0.0-Beta | Local Mode (Secure)", text_color="gray").pack(side="bottom", pady=10)

# --- PAGE 2: DASHBOARD ---
class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        
        # Sidebar
        sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        ctk.CTkLabel(sidebar, text="PsyClick", font=("Roboto", 20, "bold")).pack(pady=20)
        ctk.CTkButton(sidebar, text="Dashboard", fg_color="#1f538d").pack(pady=10, padx=10)
        ctk.CTkButton(sidebar, text="Patients", fg_color="transparent").pack(pady=10, padx=10)
        ctk.CTkButton(sidebar, text="Logout", fg_color="transparent", text_color="red", command=lambda: controller.show_frame("LoginPage")).pack(side="bottom", pady=20)

        # Main Content
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(side="right", fill="both", expand=True, padx=30, pady=30)
        
        ctk.CTkLabel(main, text="Welcome, Dr. Dela Cruz!", font=("Arial", 28)).pack(anchor="w")
        
        # Action Card
        card = ctk.CTkFrame(main, height=150)
        card.pack(fill="x", pady=30)
        ctk.CTkLabel(card, text="Start New Session", font=("Arial", 18, "bold")).pack(pady=10)
        ctk.CTkButton(card, text="+ New Patient Intake", height=40, command=lambda: controller.show_frame("IntakePage")).pack(pady=10)

# --- PAGE 3: INTAKE FORM ---
class IntakePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        ctk.CTkLabel(self, text="New Patient Intake", font=("Arial", 24)).pack(pady=40)
        
        form = ctk.CTkFrame(self)
        form.pack(pady=10)
        
        self.entry_id = ctk.CTkEntry(form, placeholder_text="Patient ID (e.g. 2026-001)", width=300)
        self.entry_id.pack(pady=10, padx=20)
        
        ctk.CTkCheckBox(form, text="Digital Consent Signed").pack(pady=10)
        
        ctk.CTkButton(self, text="Start Calibration", command=self.submit).pack(pady=20)
        ctk.CTkButton(self, text="Cancel", fg_color="gray", command=lambda: controller.show_frame("DashboardPage")).pack()

    def submit(self):
        pid = self.entry_id.get()
        if pid:
            backend.set_student_id(pid)
            self.controller.show_frame("CalibrationPage")

# --- PAGE 6: CALIBRATION ---
class CalibrationPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        ctk.CTkLabel(self, text="Calibration Phase", font=("Arial", 20)).pack(pady=20)
        ctk.CTkLabel(self, text="Please type the following standard text:", font=("Arial", 14)).pack(pady=5)
        
        self.target_text = "The quick brown fox jumps over the lazy dog..."
        ctk.CTkLabel(self, text=self.target_text, font=("Courier", 18), text_color="#4a90e2").pack(pady=10)
        
        self.txt_input = ctk.CTkTextbox(self, height=100, width=500)
        self.txt_input.pack(pady=20)
        
        self.btn_start = ctk.CTkButton(self, text="Start Recording", command=self.start_rec)
        self.btn_start.pack(pady=5)
        
        self.btn_next = ctk.CTkButton(self, text="Next >", state="disabled", command=self.stop_rec)
        self.btn_next.pack(pady=5)

    def start_rec(self):
        self.txt_input.focus()
        backend.start_capture()
        self.btn_start.configure(state="disabled")
        self.btn_next.configure(state="normal")

    def stop_rec(self):
        success, msg = backend.stop_capture_and_save_baseline()
        if success:
            self.controller.show_frame("TaskPage")
        else:
            print(msg) # Handle error

# --- PAGE 8: EMOTIONAL TASK ---
class TaskPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        ctk.CTkLabel(self, text="Emotional Recall Task", font=("Arial", 20)).pack(pady=20)
        ctk.CTkLabel(self, text="Describe a recent time when you felt overwhelmed or anxious.", font=("Arial", 14)).pack(pady=5)
        
        self.txt_input = ctk.CTkTextbox(self, height=200, width=500)
        self.txt_input.pack(pady=20)
        
        self.btn_start = ctk.CTkButton(self, text="Start Typing", command=self.start_rec)
        self.btn_start.pack(pady=5)
        
        self.btn_finish = ctk.CTkButton(self, text="Finish & Analyze", state="disabled", command=self.finish)
        self.btn_finish.pack(pady=5)

    def start_rec(self):
        self.txt_input.focus()
        backend.start_capture()
        self.btn_start.configure(state="disabled")
        self.btn_finish.configure(state="normal")

    def finish(self):
        result = backend.stop_capture_and_analyze()
        if result:
            # Pass data to Report Page
            self.controller.frames["ReportPage"].update_report(result)
            self.controller.show_frame("ReportPage")

# --- PAGE 9: REPORT ---
class ReportPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        ctk.CTkLabel(self, text="Clinical Report", font=("Arial", 24, "bold")).pack(pady=30)
        
        # Result Card
        self.card = ctk.CTkFrame(self, width=400, height=200)
        self.card.pack(pady=20)
        
        self.lbl_status = ctk.CTkLabel(self.card, text="Analyzing...", font=("Arial", 22))
        self.lbl_status.pack(pady=20)
        
        self.lbl_z = ctk.CTkLabel(self.card, text="Z-Score: --", font=("Arial", 16))
        self.lbl_z.pack(pady=10)
        
        ctk.CTkButton(self, text="Return to Dashboard", command=lambda: controller.show_frame("DashboardPage")).pack(pady=30)

    def update_report(self, data):
        z = data['z_score']
        
        if data['is_anomaly']:
            if z > 2.0:
                self.lbl_status.configure(text="⚠ Psychomotor SLOWING", text_color="red")
            elif z < -2.0:
                self.lbl_status.configure(text="⚠ Psychomotor AGITATION", text_color="orange")
        else:
            self.lbl_status.configure(text="✅ Normal Range", text_color="green")
            
        self.lbl_z.configure(text=f"Z-Score: {z:.2f} σ")

if __name__ == "__main__":
    app = PsyClickApp()
    app.mainloop()
