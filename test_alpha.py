from moviepy.editor import VideoFileClip
import os

ASSETS_DIR = r"f:\!Deeo\AI Project\Youtube-Ai-Brainrot-Automation\assets\overlays"
timer_mov = os.path.join(ASSETS_DIR, "timer_alpha.mov")

print(f"Testing {timer_mov}...")
if os.path.exists(timer_mov):
    try:
        clip = VideoFileClip(timer_mov, has_mask=True)
        print(f"✅ Duration: {clip.duration}")
        print(f"✅ Size: {clip.size}")
        print(f"✅ Mask: {clip.mask}")
        clip.close()
    except Exception as e:
        print(f"❌ Error reading MOV: {e}")
else:
    print("❌ File not found")
