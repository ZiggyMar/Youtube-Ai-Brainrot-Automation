import customtkinter as ctk
import os
import sys
import threading
from PIL import Image

# Add project root to path so we can import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.tabs.generator import GeneratorTab
from gui.tabs.layout import LayoutTab
from gui.tabs.assets import AssetsTab
from gui.tabs.poster import PosterTab

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Brainrot Automation Director")
        self.geometry("1100x700")

        # Configure grid layout (1x2)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Navigation Frame
        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self.navigation_frame, text="Brainrot\nDirector",
                                       font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=20)

        self.home_button = ctk.CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10, text="Generator",
                                         fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                         anchor="w", command=self.home_button_event)
        self.home_button.grid(row=1, column=0, sticky="ew")

        self.layout_button = ctk.CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10, text="Layout Editor",
                                           fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                           anchor="w", command=self.layout_button_event)
        self.layout_button.grid(row=2, column=0, sticky="ew")

        self.assets_button = ctk.CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10, text="Asset Manager",
                                           fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                           anchor="w", command=self.assets_button_event)
        self.assets_button.grid(row=3, column=0, sticky="ew")
        
        self.poster_button = ctk.CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10, text="Auto Poster",
                                           fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                           anchor="w", command=self.poster_button_event)
        self.poster_button.grid(row=4, column=0, sticky="ew")

        # Main Content Frames
        self.home_frame = GeneratorTab(self)
        self.layout_frame = LayoutTab(self)
        self.assets_frame = AssetsTab(self)
        self.poster_frame = PosterTab(self)

        # Select default frame
        self.select_frame_by_name("home")

    def select_frame_by_name(self, name):
        # set button color for selected button
        self.home_button.configure(fg_color=("gray75", "gray25") if name == "home" else "transparent")
        self.layout_button.configure(fg_color=("gray75", "gray25") if name == "layout" else "transparent")
        self.assets_button.configure(fg_color=("gray75", "gray25") if name == "assets" else "transparent")
        self.poster_button.configure(fg_color=("gray75", "gray25") if name == "poster" else "transparent")

        # show selected frame
        if name == "home":
            self.home_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.home_frame.grid_forget()
            
        if name == "layout":
            self.layout_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.layout_frame.grid_forget()
            
        if name == "assets":
            self.assets_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.assets_frame.grid_forget()

        if name == "poster":
            self.poster_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.poster_frame.grid_forget()

    def home_button_event(self):
        self.select_frame_by_name("home")

    def layout_button_event(self):
        self.select_frame_by_name("layout")

    def assets_button_event(self):
        self.select_frame_by_name("assets")
        
    def poster_button_event(self):
        self.select_frame_by_name("poster")

if __name__ == "__main__":
    app = App()
    app.mainloop()
