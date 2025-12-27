import os
from moviepy.editor import VideoFileClip, vfx

ASSETS_DIR = r"f:\!Deeo\AI Project\Youtube-Ai-Brainrot-Automation\assets"
INPUT_FILE = os.path.join(ASSETS_DIR, "overlays", "subscribe_cta.mp4")
OUTPUT_FILE = os.path.join(ASSETS_DIR, "overlays", "subscribe_cta_alpha.mov")

def convert_cta():
    print(f"🔄 Converting {INPUT_FILE} to {OUTPUT_FILE}...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Input file not found: {INPUT_FILE}")
        return

    try:
        # Load clip
        clip = VideoFileClip(INPUT_FILE)
        
        # Apply Green Screen Keying
        # Green is [0, 255, 0]
        print("   Applying Green Screen Mask...")
        clip = clip.fx(vfx.mask_color, color=[0, 255, 0], thr=100, s=10)
        
        # Write to MOV with Alpha
        # codec='png' is good for alpha in MOV
        print("   Writing video file (this may take a moment)...")
        clip.write_videofile(OUTPUT_FILE, codec='png', audio_codec='aac')
        
        print("✅ Conversion Complete!")
        
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
    finally:
        try: clip.close()
        except: pass

if __name__ == "__main__":
    convert_cta()
