import json
import os
import random
import glob
import numpy as np
from moviepy.config import change_settings
from moviepy.editor import (
    VideoFileClip, ImageClip, TextClip, CompositeVideoClip, 
    AudioFileClip, concatenate_videoclips, vfx, ColorClip,
    CompositeAudioClip, afx
)

# ==========================================
# CONFIGURATION
# ==========================================
IMAGEMAGICK_PATH = os.path.abspath(os.path.join("tools", "imagemagick", "magick.exe"))
change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_PATH})

ASSETS_DIR = "assets"
OUTPUT_DIR = "output"
SCRIPTS_FILE = "video_scripts.json"
AUDIO_CACHE_DIR = "audio_cache"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Asset Loading: Font
def get_custom_font():
    font_dir = os.path.join(ASSETS_DIR, "font")
    fonts = glob.glob(os.path.join(font_dir, "*.ttf")) + glob.glob(os.path.join(font_dir, "*.otf"))
    return fonts[0] if fonts else "Arial"

CUSTOM_FONT = get_custom_font()

# Difficulty List Config
DIFFICULTY_LEVELS = [
    {"label": "1. EASY", "color": "#2ecc71"},
    {"label": "2. MEDIUM", "color": "#f1c40f"},
    {"label": "3. HARD", "color": "#e67e22"},
    {"label": "4. IMPOSSIBLE", "color": "#e74c3c"}
]

# 2. The Subtitle Engine (The 'Word-by-Word' Fix)
def create_word_subtitles(text, duration, color, font_path):
    words = text.split()
    if not words: return []
    
    # Split into chunks of 2 words max
    chunks = [" ".join(words[i:i+2]) for i in range(0, len(words), 2)]
    num_chunks = len(chunks)
    chunk_duration = duration / num_chunks
    
    clips = []
    for i, chunk in enumerate(chunks):
        start_t = i * chunk_duration
        # Style: All Caps, Size 90, Stroke White Width 4
        txt = (TextClip(chunk.upper(), font=font_path, fontsize=90, color=color,
                        stroke_color="white", stroke_width=4)
               .set_start(start_t)
               .set_duration(chunk_duration)
               .set_position(("center", 1100)))
        clips.append(txt)
    return clips

# 3. Visual Stack Helpers
def find_character_image(speaker, character_field):
    """
    Safety Check: If speaker is SpongeBob but image says Patrick, FORCE load a SpongeBob image.
    """
    # Normalize speaker name to folder name
    speaker_map = {
        "SpongeBob": "SpongeBob",
        "Patrick": "Patrick",
        "Squidward": "Squidward",
        "Plankton": "Plankton",
        "MrKrabs": "Mr. Krabs",
        "Mr. Krabs": "Mr. Krabs"
    }
    target_folder_name = speaker_map.get(speaker, speaker)
    
    # Check if character_field contradicts speaker
    # e.g. speaker="SpongeBob", character_field="Patrick_Happy.png"
    is_contradiction = False
    for s_key, folder in speaker_map.items():
        if s_key != speaker and s_key.lower() in character_field.lower():
            is_contradiction = True
            break
            
    if is_contradiction:
        print(f"⚠️ Safety Check: Speaker is {speaker} but image is {character_field}. Forcing {speaker} image.")
        char_folder = os.path.join(ASSETS_DIR, "characters", target_folder_name)
    else:
        # Try to find the specific image
        # character_field might be "SpongeBob_Happy.png" or just "Happy.png"
        clean_name = character_field.replace(".png", "")
        if "_" in clean_name:
            parts = clean_name.split("_")
            # If first part is a speaker name, use second part as mood
            if parts[0] in speaker_map:
                mood = parts[1]
            else:
                mood = parts[0]
        else:
            mood = clean_name
            
        char_folder = os.path.join(ASSETS_DIR, "characters", target_folder_name)
        specific_path = os.path.join(char_folder, f"{mood}.png")
        if os.path.exists(specific_path):
            return specific_path

    # Fallback: Pick any image from the correct speaker's folder
    if os.path.exists(char_folder):
        files = glob.glob(os.path.join(char_folder, "*.png"))
        if files: return random.choice(files)
        
    return None

def create_difficulty_list(active_label, duration):
    clips = []
    for i, level in enumerate(DIFFICULTY_LEVELS):
        # Highlight current level Green, others White
        is_active = level["label"] == active_label
        color = "#2ecc71" if is_active else "white"
        
        txt = (TextClip(level["label"], font=CUSTOM_FONT, fontsize=50, color=color, 
                        stroke_color="black", stroke_width=2)
               .set_position((50, 100 + i * 70))
               .set_duration(duration))
        clips.append(txt)
    return clips

def generate_video(video_data):
    video_id = video_data["video_id"]
    print(f"🎬 Rendering Minecraft-Style Video {video_id}...")
    
    # 1. Asset Loading: Background & Music
    bg_files = glob.glob(os.path.join(ASSETS_DIR, "backgrounds", "*.mp4"))
    if not bg_files:
        print("❌ No background videos found!")
        return
    bg_source = VideoFileClip(random.choice(bg_files)).without_audio()
    
    music_files = glob.glob(os.path.join(ASSETS_DIR, "music", "*.mp3"))
    bg_music_path = random.choice(music_files) if music_files else None
    
    # Crop Background to 9:16
    w, h = bg_source.size
    target_ratio = 9/16
    if w/h > target_ratio:
        new_w = h * target_ratio
        bg_source = bg_source.crop(x1=w/2 - new_w/2, width=new_w, height=h)
    else:
        new_h = w / target_ratio
        bg_source = bg_source.crop(y1=h/2 - new_h/2, width=w, height=new_h)
    bg_source = bg_source.resize((1080, 1920))
    
    final_segment_clips = []
    dialogue_audios = []
    total_duration = 0
    bg_cursor = 0
    
    for i, segment in enumerate(video_data.get("segments", []), start=1):
        visuals = segment.get("visuals", {})
        text = segment.get("text", "")
        speaker = segment.get("speaker", "")
        is_timer = visuals.get("show_timer", False)
        
        # Audio & Duration
        audio_path = os.path.join(AUDIO_CACHE_DIR, f"v{video_id}_s{i}_{speaker}.wav")
        
        if is_timer:
            timer_path = os.path.join(ASSETS_DIR, "overlays", "timer.mp4")
            if os.path.exists(timer_path):
                timer_clip = VideoFileClip(timer_path)
                duration = timer_clip.duration
                seg_audio = timer_clip.audio
            else:
                print(f"⚠️ Timer overlay missing: {timer_path}")
                continue
        elif os.path.exists(audio_path):
            seg_audio = AudioFileClip(audio_path)
            duration = seg_audio.duration
        else:
            print(f"⚠️ Missing audio: {audio_path}")
            continue

        # Background Layer
        if bg_cursor + duration > bg_source.duration: bg_cursor = 0
        bg_clip = bg_source.subclip(bg_cursor, bg_cursor + duration)
        bg_cursor += duration
        
        layers = [bg_clip]
        
        # Character Layer
        char_file = visuals.get("character")
        if char_file and not is_timer:
            char_path = find_character_image(speaker, char_file)
            if char_path:
                char_clip = (ImageClip(char_path).resize(height=800)
                             .set_duration(duration)
                             .set_position(("center", "bottom"))
                             .fx(vfx.fadein, 0.2)) # Slide in effect (fadein as proxy or actual slide)
                # For actual slide in:
                # char_clip = char_clip.set_position(lambda t: ('center', 1920 - 800 * min(1, t/0.2)))
                layers.append(char_clip)
        
        # Subtitle Layer
        if text and not is_timer:
            color = visuals.get("subtitle_color", "yellow")
            layers.extend(create_word_subtitles(text, duration, color, CUSTOM_FONT))
            
        # Timer Layer
        if is_timer:
            # Mask Green Screen
            timer_overlay = (timer_clip.fx(vfx.mask_color, color=[0, 255, 0], thr=100, s=10)
                             .resize(width=900)
                             .set_position("center")
                             .set_duration(duration))
            layers.append(timer_overlay)

        # Difficulty List Layer
        layers.extend(create_difficulty_list(visuals.get("list_highlight", "1. EASY"), duration))

        # Composite Segment
        segment_comp = CompositeVideoClip(layers, size=(1080, 1920)).set_duration(duration)
        
        # Store for final assembly
        final_segment_clips.append(segment_comp)
        
        # Handle Audio Offset for CompositeAudioClip
        seg_audio = seg_audio.set_start(total_duration)
        dialogue_audios.append(seg_audio)
        
        total_duration += duration
        
    if not final_segment_clips:
        print("❌ No segments to render.")
        return

    # 4. The Audio Mix
    # Track 1: Dialogue
    dialogue_track = CompositeAudioClip(dialogue_audios)
    
    # Track 2: Background Music
    if bg_music_path:
        bg_music = AudioFileClip(bg_music_path).volumex(0.1).fx(afx.audio_loop, duration=total_duration)
        final_audio = CompositeAudioClip([bg_music, dialogue_track])
    else:
        final_audio = dialogue_track

    # Final Video Assembly
    final_video = concatenate_videoclips(final_segment_clips, method="compose")
    final_video = final_video.set_audio(final_audio)
    
    out_path = os.path.join(OUTPUT_DIR, f"video_{video_id}_production.mp4")
    final_video.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast")
    print(f"✅ Finished: {out_path}")

def main():
    if not os.path.exists(SCRIPTS_FILE):
        print(f"❌ {SCRIPTS_FILE} not found.")
        return
        
    with open(SCRIPTS_FILE, "r", encoding="utf-8") as f:
        scripts = json.load(f)
        
    for video in scripts:
        try:
            generate_video(video)
        except Exception as e:
            print(f"❌ Error on video {video.get('video_id')}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
