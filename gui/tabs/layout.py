import customtkinter as ctk
import json
import os
import sys

# Configuration Paths
CORE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LAYOUT_FILE = os.path.join(CORE_DIR, "layout_config.json")

class LayoutTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Layout Configuration")
        self.scrollable_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(1, weight=1)

        self.config_data = self.load_config()
        self.entries = {}

        row = 0
        for section, settings in self.config_data.items():
            # Section Header
            header = ctk.CTkLabel(self.scrollable_frame, text=section.upper(), font=ctk.CTkFont(size=16, weight="bold"))
            header.grid(row=row, column=0, columnspan=2, pady=(20, 10), sticky="w")
            row += 1
            
            for key, value in settings.items():
                label = ctk.CTkLabel(self.scrollable_frame, text=key)
                label.grid(row=row, column=0, padx=10, pady=5, sticky="w")
                
                entry = ctk.CTkEntry(self.scrollable_frame)
                entry.insert(0, str(value))
                entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
                
                # Store reference to entry to save later
                # Key format: "section.key"
                self.entries[f"{section}.{key}"] = entry
                
                # Add trace or bind to save on change? 
                # For safety, let's add a "Save" button, but maybe auto-save on focus out could work.
                # Let's stick to a Save button for now.
                
                row += 1

        # Save Button
        self.save_button = ctk.CTkButton(self, text="SAVE CONFIGURATION", fg_color="blue", command=self.save_config)
        self.save_button.grid(row=1, column=0, padx=20, pady=20, sticky="ew")

    def load_config(self):
        if os.path.exists(LAYOUT_FILE):
            try:
                with open(LAYOUT_FILE, "r") as f:
                    return json.load(f)
            except:
                pass
        return {} # Should load default if missing, but for now empty

    def save_config(self):
        new_config = self.config_data.copy()
        
        try:
            for key_path, entry in self.entries.items():
                section, key = key_path.split(".")
                value = entry.get()
                
                # Try to convert to number if possible
                try:
                    if "." in value:
                        val_num = float(value)
                    else:
                        val_num = int(value)
                    new_config[section][key] = val_num
                except ValueError:
                    new_config[section][key] = value

            with open(LAYOUT_FILE, "w") as f:
                json.dump(new_config, f, indent=2)
            
            print("✅ Layout Configuration Saved!")
            
        except Exception as e:
            print(f"❌ Error saving config: {e}")
