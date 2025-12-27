import customtkinter as ctk
import threading
import sys
import os
import queue
from tkinter import END

# Import core logic
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.main import main as run_generation_sequence

class GeneratorTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Console log expands

        # 1. Controls Area
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.controls_frame.grid_columnconfigure(2, weight=1)

        self.label_count = ctk.CTkLabel(self.controls_frame, text="Videos to Generate:")
        self.label_count.grid(row=0, column=0, padx=10, pady=10)

        self.entry_count = ctk.CTkEntry(self.controls_frame, width=60)
        self.entry_count.grid(row=0, column=1, padx=10, pady=10)
        self.entry_count.insert(0, "5")

        self.infinite_switch = ctk.CTkSwitch(self.controls_frame, text="Infinite Mode (Until Stopped)", command=self.toggle_infinite)
        self.infinite_switch.grid(row=0, column=2, padx=10, pady=10, sticky="w")

        self.start_button = ctk.CTkButton(self.controls_frame, text="START GENERATION", fg_color="green", hover_color="darkgreen", command=self.start_generation)
        self.start_button.grid(row=0, column=3, padx=10, pady=10)
        
        self.stop_button = ctk.CTkButton(self.controls_frame, text="STOP", fg_color="red", hover_color="darkred", state="disabled", command=self.stop_generation)
        self.stop_button.grid(row=0, column=4, padx=10, pady=10)

        # 2. Progress Area
        self.progress_frame = ctk.CTkFrame(self)
        self.progress_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(self.progress_frame, text="Ready", anchor="w")
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.progressbar = ctk.CTkProgressBar(self.progress_frame)
        self.progressbar.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.progressbar.set(0)

        # 3. Console Log
        self.log_textbox = ctk.CTkTextbox(self, width=800, height=300, font=("Consolas", 12))
        self.log_textbox.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        self.is_running = False
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        
        # Redirect stdout/stderr to our log
        # Note: This is a bit hacky for a GUI, but effective for capturing print statements
        # We will poll the queue to update the textbox
        self.after(100, self.update_log_from_queue)

    def toggle_infinite(self):
        if self.infinite_switch.get():
            self.entry_count.configure(state="disabled")
        else:
            self.entry_count.configure(state="normal")

    def log_write(self, text):
        self.log_queue.put(text)

    def update_log_from_queue(self):
        try:
            while True:
                text = self.log_queue.get_nowait()
                self.log_textbox.insert(END, text)
                self.log_textbox.see(END)
        except queue.Empty:
            pass
        self.after(100, self.update_log_from_queue)

    def start_generation(self):
        if self.is_running: return
        
        try:
            if self.infinite_switch.get():
                count = 999999
            else:
                count = int(self.entry_count.get())
        except ValueError:
            self.log_write("❌ Invalid number of videos.\n")
            return

        self.is_running = True
        self.stop_event.clear()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.progressbar.set(0)
        self.status_label.configure(text="Starting Generation...")
        
        # Start background thread
        self.thread = threading.Thread(target=self.run_process, args=(count,))
        self.thread.start()

    def stop_generation(self):
        if not self.is_running: return
        self.log_write("\n🛑 Stopping after current step completes...\n")
        self.stop_event.set()
        # We can't easily kill the thread, but we can check the flag in the loop

    def run_process(self, count):
        # Redirect stdout temporarily
        original_stdout = sys.stdout
        sys.stdout = ConsoleRedirector(self.log_queue)
        
        try:
            # We need to modify main.py to accept a stop_event or check it
            # For now, we will assume main.py runs one video at a time in a loop
            # We will implement a custom loop here calling the steps from main.py
            
            # Import steps from main.py
            from core.main import run_step, archive_completed_videos, SCRIPTS_FILE
            
            for i in range(count):
                if self.stop_event.is_set():
                    print("🛑 Generation Stopped by User.")
                    break
                
                print(f"\n🎬 === STARTING VIDEO GENERATION SEQUENCE {i+1} ===")
                self.update_status(f"Generating Script ({i+1}/{count})...", (i / count))
                
                # Step 1
                run_step("director.py", "STAGE 1: WRITING SCRIPTS")
                if self.stop_event.is_set(): break
                
                # Step 2
                self.update_status(f"Generating Audio ({i+1}/{count})...", (i / count) + (0.2/count))
                run_step("voicebox.py", "STAGE 2: GENERATING AUDIO")
                if self.stop_event.is_set(): break
                
                # Step 3
                self.update_status(f"Rendering Video ({i+1}/{count})...", (i / count) + (0.5/count))
                run_step("video_factory.py", "STAGE 3: RENDERING VIDEOS")
                if self.stop_event.is_set(): break
                
                # Step 4
                self.update_status(f"Archiving ({i+1}/{count})...", (i / count) + (0.9/count))
                archive_completed_videos()
                
                print(f"✅ Sequence {i+1} Complete.\n")
                self.progressbar.set((i + 1) / count)
                
        except Exception as e:
            print(f"❌ Error in thread: {e}")
            import traceback
            traceback.print_exc()
        finally:
            sys.stdout = original_stdout
            self.is_running = False
            # Schedule UI update on main thread
            self.after(0, self.on_process_finished)

    def update_status(self, text, progress):
        # Helper to update UI from thread safely? 
        # Tkinter is not thread safe, but setting vars usually works or use after
        self.after(0, lambda: self.status_label.configure(text=text))
        self.after(0, lambda: self.progressbar.set(progress))

    def on_process_finished(self):
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.status_label.configure(text="Generation Complete (or Stopped).")
        self.progressbar.set(1)

class ConsoleRedirector:
    def __init__(self, queue):
        self.queue = queue
    def write(self, text):
        self.queue.put(text)
    def flush(self):
        pass
