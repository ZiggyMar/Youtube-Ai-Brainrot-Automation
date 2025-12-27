import customtkinter as ctk
import os
import shutil
import tkinter.filedialog as filedialog

# Configuration Paths
CORE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS_DIR = os.path.join(CORE_DIR, "assets")

class AssetsTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Tabview for different asset types
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.tabs = {
            "Characters": os.path.join(ASSETS_DIR, "characters"),
            "Music": os.path.join(ASSETS_DIR, "music"),
            "Backgrounds": os.path.join(ASSETS_DIR, "backgrounds"),
            "Sounds": os.path.join(ASSETS_DIR, "Sounds")
        }
        
        for name, path in self.tabs.items():
            self.tabview.add(name)
            self.build_asset_list(name, path)

    def build_asset_list(self, tab_name, path):
        frame = self.tabview.tab(tab_name)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Controls
        controls = ctk.CTkFrame(frame, fg_color="transparent")
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        add_btn = ctk.CTkButton(controls, text=f"Add New {tab_name[:-1]}", command=lambda t=tab_name, p=path: self.add_asset(t, p))
        add_btn.pack(side="left", padx=5)
        
        refresh_btn = ctk.CTkButton(controls, text="Refresh", width=60, command=lambda t=tab_name, p=path: self.refresh_list(t, p))
        refresh_btn.pack(side="left", padx=5)
        
        # List
        list_frame = ctk.CTkScrollableFrame(frame)
        list_frame.grid(row=1, column=0, sticky="nsew")
        
        # Store list frame reference to refresh later
        setattr(self, f"{tab_name}_list_frame", list_frame)
        
        self.populate_list(list_frame, path)

    def populate_list(self, list_frame, path):
        # Clear existing
        for widget in list_frame.winfo_children():
            widget.destroy()
            
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            
        items = os.listdir(path)
        row = 0
        for item in items:
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                # For characters, we might want to go deeper or just list folders
                # Let's list folders for characters
                label = ctk.CTkLabel(list_frame, text=f"📁 {item}", anchor="w")
                label.grid(row=row, column=0, sticky="w", padx=5, pady=2)
                
                # If it's a character folder, maybe show count of emotions?
                try:
                    count = len([f for f in os.listdir(item_path) if f.endswith('.png')])
                    info = ctk.CTkLabel(list_frame, text=f"({count} emotions)", text_color="gray")
                    info.grid(row=row, column=1, sticky="w", padx=5)
                except: pass
                
            else:
                label = ctk.CTkLabel(list_frame, text=f"📄 {item}", anchor="w")
                label.grid(row=row, column=0, sticky="w", padx=5, pady=2)
            
            row += 1

    def refresh_list(self, tab_name, path):
        list_frame = getattr(self, f"{tab_name}_list_frame")
        self.populate_list(list_frame, path)

    def add_asset(self, tab_name, target_path):
        file_paths = filedialog.askopenfilenames(title=f"Select {tab_name}")
        if not file_paths: return
        
        for fp in file_paths:
            try:
                filename = os.path.basename(fp)
                
                # Special handling for Characters (needs subfolder)
                if tab_name == "Characters":
                    # Ask for character name or assume folder?
                    # For simplicity, let's just dump into a "New_Character" folder or ask user.
                    # Since we can't easily pop up a dialog for text input in CTk without a custom class,
                    # We will just copy to root of characters for now, or maybe prompt user to organize manually?
                    # Better: Just copy to target_path. If user wants specific character, they should have selected that folder.
                    # Wait, the target_path for Characters is `assets/characters`.
                    # We should probably ask which character it belongs to.
                    # For now, let's just copy to `assets/characters/Unsorted` if it's an image.
                    pass
                
                dest = os.path.join(target_path, filename)
                shutil.copy2(fp, dest)
                print(f"✅ Added {filename}")
            except Exception as e:
                print(f"❌ Error adding {filename}: {e}")
        
        self.refresh_list(tab_name, target_path)
