import customtkinter as ctk
import threading
import os
import sys
import json

# Import core logic
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# We will import auto_poster later when it exists

class PosterTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Status & Controls
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        self.label_status = ctk.CTkLabel(self.top_frame, text="Auto-Poster Status: STOPPED", text_color="red", font=("Arial", 16, "bold"))
        self.label_status.pack(side="left", padx=20, pady=20)
        
        self.btn_toggle = ctk.CTkButton(self.top_frame, text="ENABLE AUTO-POSTER", fg_color="green", command=self.toggle_poster)
        self.btn_toggle.pack(side="right", padx=20, pady=20)

        self.btn_auth = ctk.CTkButton(self.top_frame, text="Authenticate YouTube", command=self.auth_youtube)
        self.btn_auth.pack(side="right", padx=10, pady=20)

        # 2. Schedule / Log
        self.log_frame = ctk.CTkScrollableFrame(self, label_text="Scheduler Log")
        self.log_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        self.log_label = ctk.CTkLabel(self.log_frame, text="Waiting for logs...", anchor="w", justify="left")
        self.log_label.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.poster_thread = None
        self.is_running = False

    def log(self, text):
        current = self.log_label.cget("text")
        new_text = current + "\n" + text
        # Keep last 50 lines
        lines = new_text.split("\n")[-50:]
        self.log_label.configure(text="\n".join(lines))

    def auth_youtube(self):
        self.log("🔹 Starting YouTube Authentication...")
        # Run in thread to avoid freezing
        threading.Thread(target=self._run_auth).start()

    def _run_auth(self):
        try:
            from core.auto_poster import YouTubeUploader
            uploader = YouTubeUploader()
            if uploader.authenticate():
                self.log("✅ YouTube Authenticated Successfully!")
            else:
                self.log("❌ Authentication Failed. Check client_secrets.json")
        except Exception as e:
            self.log(f"❌ Error: {e}")

    def toggle_poster(self):
        if self.is_running:
            self.is_running = False
            self.label_status.configure(text="Auto-Poster Status: STOPPED", text_color="red")
            self.btn_toggle.configure(text="ENABLE AUTO-POSTER", fg_color="green")
            self.log("🛑 Auto-Poster Stopped.")
        else:
            self.is_running = True
            self.label_status.configure(text="Auto-Poster Status: RUNNING", text_color="green")
            self.btn_toggle.configure(text="DISABLE AUTO-POSTER", fg_color="red")
            self.log("🚀 Auto-Poster Started. Monitoring schedule...")
            
            self.poster_thread = threading.Thread(target=self.run_scheduler_loop)
            self.poster_thread.start()

    def run_scheduler_loop(self):
        import time
        import schedule
        from core.auto_poster import Scheduler
        
        scheduler = Scheduler()
        
        # Setup schedule
        scheduler.setup_schedule()
        
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
