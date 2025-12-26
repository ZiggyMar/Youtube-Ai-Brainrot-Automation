import sys
import os
sys.path.append(os.getcwd())
from core.video_factory import preprocess_assets, ASSETS_DIR
import subprocess

def get_resolution(file_path):
    cmd = [
        r"tools\ffmpeg\ffprobe.exe", 
        "-v", "error", 
        "-select_streams", "v:0", 
        "-show_entries", "stream=width,height", 
        "-of", "csv=s=x:p=0", 
        file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    print("🚀 Running Pre-processing...")
    preprocess_assets()
    
    print("\n🔍 Verifying Dimensions...")
    
    timer_path = os.path.join(ASSETS_DIR, "overlays", "timer_alpha_scaled.mov")
    cta_path = os.path.join(ASSETS_DIR, "overlays", "subscribe_cta_alpha_scaled.mov")
    
    if os.path.exists(timer_path):
        print(f"✅ Timer Scaled Exists: {get_resolution(timer_path)}")
    else:
        print("❌ Timer Scaled MISSING")
        
    if os.path.exists(cta_path):
        print(f"✅ CTA Scaled Exists: {get_resolution(cta_path)}")
    else:
        print("❌ CTA Scaled MISSING")
