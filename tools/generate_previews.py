import os
from moviepy.editor import VideoFileClip, vfx

ASSETS_DIR = r"f:\!Deeo\AI Project\Youtube-Ai-Brainrot-Automation\assets"
LAYOUT_DIR = os.path.join(ASSETS_DIR, "Layout")

def generate_preview(base_name, output_name, force_green_key=False):
    # Force use of original MP4 files to ensure 1080x1920 resolution and correct aspect ratio
    # mov_path = os.path.join(ASSETS_DIR, "overlays", f"{base_name}_alpha_scaled.mov")
    mp4_path = os.path.join(ASSETS_DIR, "overlays", f"{base_name}.mp4")
    
    video_path = None
    has_mask = False
    
    if os.path.exists(mp4_path):
        video_path = mp4_path
        has_mask = False # MP4 usually needs keying
    
    if not video_path:
        # Fallback to MOV if MP4 doesn't exist
        mov_path = os.path.join(ASSETS_DIR, "overlays", f"{base_name}_alpha_scaled.mov")
        if os.path.exists(mov_path):
            video_path = mov_path
            has_mask = True
    
    if not video_path:
        print(f"❌ Could not find video for {base_name}")
        return
    
    if not video_path:
        print(f"❌ Could not find video for {base_name}")
        return

    print(f"Processing {video_path}...")
    
    try:
        clip = VideoFileClip(video_path, has_mask=has_mask)
        
        # Apply green screen keying if needed (MP4 or forced)
        if not has_mask or force_green_key:
            print("   Applying Green Screen Keying ([0,255,0])...")
            clip = clip.fx(vfx.mask_color, color=[0, 255, 0], thr=100, s=10)
        
        # Capture frame from middle of video to ensure element is visible
        t = clip.duration / 2
        output_path = os.path.join(LAYOUT_DIR, output_name)
        
        print(f"   Saving frame at {t:.2f}s to {output_path}...")
        clip.save_frame(output_path, t=t, withmask=True)
        print("   ✅ Done.")
        
        clip.close()
        
    except Exception as e:
        print(f"❌ Error processing {video_path}: {e}")

if __name__ == "__main__":
    # Generate Timer Preview
    # Note: 'timer' base name matches 'timer_alpha_scaled.mov' / 'timer.mp4'
    generate_preview("timer", "Timer_preview.png")
    
    # Generate CTA Preview
    # Note: 'subscribe_cta' base name matches 'subscribe_cta_alpha_scaled.mov' / 'subscribe_cta.mp4'
    generate_preview("subscribe_cta", "CTA_preview.png")
