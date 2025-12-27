import PyInstaller.__main__
import os
import shutil

# Configuration
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
GUI_SCRIPT = os.path.join(PROJECT_ROOT, "gui", "main_window.py")
ICON_PATH = os.path.join(PROJECT_ROOT, "assets", "icon.ico") # Optional, if exists

def build():
    print("🚀 Starting Build Process...")
    
    # Clean previous builds
    if os.path.exists("build"): shutil.rmtree("build")
    if os.path.exists("dist"): shutil.rmtree("dist")

    args = [
        GUI_SCRIPT,
        '--name=BrainrotDirector',
        '--onefile',
        '--windowed',
        '--clean',
        f'--add-data={os.path.join(PROJECT_ROOT, "core")}{os.pathsep}core',
        f'--add-data={os.path.join(PROJECT_ROOT, "gui")}{os.pathsep}gui',
        f'--add-data={os.path.join(PROJECT_ROOT, "data")}{os.pathsep}data',
        # We don't bundle assets/output usually as they are large/dynamic, 
        # but the app expects them relative to CWD or executable.
        # For --onefile, sys._MEIPASS is used, but we want to use external folders for assets.
        # So we won't bundle assets inside the exe, but ensure the exe looks next to it.
    ]
    
    if os.path.exists(ICON_PATH):
        args.append(f'--icon={ICON_PATH}')

    PyInstaller.__main__.run(args)
    
    print("✅ Build Complete. Check 'dist/BrainrotDirector.exe'")

if __name__ == "__main__":
    build()
