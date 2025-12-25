import os
import sys
from moviepy.editor import VideoFileClip, CompositeVideoClip

# Setup paths
PROJECT_ROOT = os.getcwd()
FFMPEG_PATH = os.path.join(PROJECT_ROOT, "tools", "ffmpeg", "ffmpeg.exe")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
OVERLAY_PATH = os.path.join(ASSETS_DIR, "overlays", "subscribe_cta_alpha.mov")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "debug_output.mp4")

# Configure FFmpeg
if os.path.exists(FFMPEG_PATH):
    os.environ["IMAGEIO_FFMPEG_EXE"] = FFMPEG_PATH
    print(f"✅ Using Custom FFmpeg: {FFMPEG_PATH}")
else:
    print(f"❌ Custom FFmpeg not found at {FFMPEG_PATH}")

def test_read_overlay():
    print(f"Testing overlay: {OVERLAY_PATH}")
    if not os.path.exists(OVERLAY_PATH):
        print("❌ Overlay file does not exist!")
        return

    try:
        # Try loading with has_mask=True
        print("Attempting to load VideoFileClip(has_mask=True)...")
        clip = VideoFileClip(OVERLAY_PATH, has_mask=True)
        print(f"✅ Loaded clip. Duration: {clip.duration}, Size: {clip.size}")
        
        # Try reading the first frame
        print("Reading frame 0...")
        frame = clip.get_frame(0)
        print(f"✅ Frame 0 shape: {frame.shape}")
        
        # Try compositing and writing
        print("Creating composite...")
        comp = CompositeVideoClip([clip], size=clip.size).set_duration(2)
        
        print("Writing video file...")
        comp.write_videofile(OUTPUT_PATH, fps=24, codec="libx264")
        print("✅ Write successful!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_read_overlay()
