import json
import os
import random
import glob
import numpy as np
from tqdm import tqdm
from moviepy.editor import (
    VideoFileClip, ImageClip, CompositeVideoClip, 
    AudioFileClip, concatenate_videoclips, vfx, 
    CompositeAudioClip, afx
)
from PIL import Image, ImageDraw, ImageFont

# Configuration
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
SCRIPTS_FILE = os.path.join(DATA_DIR, "video_scripts.json")
AUDIO_CACHE_DIR = os.path.join(PROJECT_ROOT, "audio_cache")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Difficulty List Config
DIFFICULTY_LEVELS = [
    {"label": "1. EASY", "color": "#2ecc71"},
    {"label": "2. MEDIUM", "color": "#f1c40f"},
    {"label": "3. HARD", "color": "#e67e22"},
    {"label": "4. IMPOSSIBLE", "color": "#e74c3c"}
]

def get_font_path():
    """Hardcoded check for Burbank.ttf"""
    font_path = os.path.join(ASSETS_DIR, "Font", "Burbank.ttf")
    if os.path.exists(font_path):
        print(f"✅ Using PIL Font: {font_path}")
        return font_path
    
    # Fallback
    font_path = os.path.join(ASSETS_DIR, "Font", "burbankbigcondensed_bold.otf")
    if os.path.exists(font_path):
        print(f"✅ Using PIL Font: {font_path}")
        return font_path
        
    print("⚠️ Font not found, using default.")
    return "arial.ttf"

CUSTOM_FONT_PATH = get_font_path()

def create_pil_text_image(text, font_path, font_size, color, stroke_width=6):
    """Generates a transparent PIL Image with stroked text."""
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()

    # Calculate text size
    dummy_img = Image.new('RGBA', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    
    # Add padding
    w += 20
    h += 20
    
    # Create image
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw text with stroke
    # Center position
    x, y = 10, 10
    
    draw.text((x, y), text, font=font, fill=color, 
              stroke_width=stroke_width, stroke_fill="black")
              
    return np.array(img)

def create_text_clip_pil(text, font_path, font_size, color, stroke_width, duration):
    """Creates a MoviePy ImageClip from a PIL image."""
    img_array = create_pil_text_image(text, font_path, font_size, color, stroke_width)
    return ImageClip(img_array).set_duration(duration)

def create_word_subtitles(text, duration, color, font_path):
    """Splits text and creates a sequence of PIL-based clips."""
    words = text.split()
    if not words: return []
    
    # Split into chunks of 2 words max
    chunks = [" ".join(words[i:i+2]) for i in range(0, len(words), 2)]
    num_chunks = len(chunks)
    chunk_duration = duration / num_chunks
    
    clips = []
    for i, chunk in enumerate(chunks):
        start_t = i * chunk_duration
        
        # Create Clip using PIL
        txt_clip = create_text_clip_pil(chunk.upper(), font_path, 110, color, 6, chunk_duration)
        
        txt_clip = txt_clip.set_start(start_t).set_position(("center", 1150))
        clips.append(txt_clip)
        
    return clips

def create_difficulty_list_pil(active_label, duration, answer_reveal=None):
    """Creates the difficulty list using PIL."""
    clips = []
    for i, level in enumerate(DIFFICULTY_LEVELS):
        is_active = level["label"] == active_label
        color = "#2ecc71" if is_active else "white"
        
        display_text = level["label"]
        if is_active and answer_reveal:
            prefix = level["label"].split(".")[0]
            display_text = f"{prefix}. {answer_reveal.upper()}"

        txt_clip = create_text_clip_pil(display_text, CUSTOM_FONT_PATH, 50, color, 2, duration)
        txt_clip = txt_clip.set_position((50, 100 + i * 70))
        clips.append(txt_clip)
        
    return clips

def find_character_image(speaker, character_field):
    """Resolves character image path."""
    speaker_map = {
        "SpongeBob": "SpongeBob", "Patrick": "Patrick", "Squidward": "Squidward",
        "Plankton": "Plankton", "MrKrabs": "Mr. Krabs", "Mr. Krabs": "Mr. Krabs"
    }
    target_folder_name = speaker_map.get(speaker, speaker)
    
    # Check for contradiction
    is_contradiction = False
    for s_key in speaker_map:
        if s_key != speaker and s_key.lower() in character_field.lower():
            is_contradiction = True
            break
            
    if is_contradiction:
        char_folder = os.path.join(ASSETS_DIR, "characters", target_folder_name)
    else:
        clean_name = character_field.replace(".png", "")
        if "_" in clean_name:
            parts = clean_name.split("_")
            mood = parts[1] if parts[0] in speaker_map else parts[0]
        else:
            mood = clean_name
            
        char_folder = os.path.join(ASSETS_DIR, "characters", target_folder_name)
        specific_path = os.path.join(char_folder, f"{mood}.png")
        if os.path.exists(specific_path):
            return specific_path

    if os.path.exists(char_folder):
        files = glob.glob(os.path.join(char_folder, "*.png"))
        if files: return random.choice(files)
    return None

def generate_video(video_data):
    video_id = video_data["video_id"]
    print(f"🎬 Rendering Video {video_id} with PIL Text Engine...")
    
    # 1. Background
    bg_files = glob.glob(os.path.join(ASSETS_DIR, "backgrounds", "*.mp4"))
    if not bg_files: return
    bg_source = VideoFileClip(random.choice(bg_files)).without_audio()
    
    # Crop to 9:16
    w, h = bg_source.size
    target_ratio = 9/16
    if w/h > target_ratio:
        new_w = h * target_ratio
        bg_source = bg_source.crop(x1=w/2 - new_w/2, width=new_w, height=h)
    else:
        new_h = w / target_ratio
        bg_source = bg_source.crop(y1=h/2 - new_h/2, width=w, height=new_h)
    bg_source = bg_source.resize((1080, 1920))
    
    # 2. Music
    music_files = glob.glob(os.path.join(ASSETS_DIR, "music", "*.mp3"))
    bg_music_path = random.choice(music_files) if music_files else None
    
    final_segment_clips = []
    dialogue_audios = []
    total_duration = 0
    bg_cursor = 0
    
    for i, segment in enumerate(video_data.get("segments", []), start=1):
        visuals = segment.get("visuals", {})
        text = segment.get("text", "")
        speaker = segment.get("speaker", "")
        is_timer = visuals.get("show_timer", False)
        
        # Audio
        audio_path = os.path.join(AUDIO_CACHE_DIR, f"v{video_id}_s{i}_{speaker}.wav")
        
        if is_timer:
            timer_path = os.path.join(ASSETS_DIR, "overlays", "timer.mp4")
            if os.path.exists(timer_path):
                timer_clip = VideoFileClip(timer_path)
                duration = timer_clip.duration
                seg_audio = timer_clip.audio
            else:
                continue
        elif os.path.exists(audio_path):
            seg_audio = AudioFileClip(audio_path)
            duration = seg_audio.duration
        else:
            continue

        # Background Slice
        if bg_cursor + duration > bg_source.duration: bg_cursor = 0
        bg_clip = bg_source.subclip(bg_cursor, bg_cursor + duration)
        bg_cursor += duration
        
        layers = [bg_clip]
        
        # Character Layer
        char_file = visuals.get("character")
        if char_file and not is_timer:
            char_path = find_character_image(speaker, char_file)
            if char_path:
                # Slide Animation
                def slide_pos(t):
                    SLIDE_DUR = 0.4
                    if t < SLIDE_DUR:
                        prog = t / SLIDE_DUR
                        ease = 1 - (1 - prog) ** 3
                        target_x = 240 
                        start_x = -1000 # Assume left for simplicity or random
                        cur_x = start_x + (target_x - start_x) * ease
                        return (int(cur_x), "bottom")
                    return ("center", "bottom")

                char_clip = (ImageClip(char_path).resize(height=800)
                             .rotate(lambda t: 2 * np.sin(2 * np.pi * t / 3.0))
                             .set_duration(duration)
                             .set_position(slide_pos)) # Simplified slide
                layers.append(char_clip)
                
                # SFX
                sfx_dir = os.path.join(ASSETS_DIR, "Sounds")
                if os.path.exists(sfx_dir):
                    sfx_files = glob.glob(os.path.join(sfx_dir, "*.wav"))
                    if sfx_files:
                        sfx_clip = AudioFileClip(random.choice(sfx_files)).volumex(0.05)
                        if sfx_clip.duration > duration: sfx_clip = sfx_clip.subclip(0, duration)
                        dialogue_audios.append(sfx_clip.set_start(total_duration))

        # Subtitles (PIL)
        if text and not is_timer:
            color = visuals.get("subtitle_color", "yellow")
            layers.extend(create_word_subtitles(text, duration, color, CUSTOM_FONT_PATH))
            
        # Timer
        if is_timer:
            timer_overlay = (timer_clip.fx(vfx.mask_color, color=[0, 255, 0], thr=100, s=10)
                             .resize(width=900).set_position("center").set_duration(duration))
            layers.append(timer_overlay)
            
        # Difficulty List (PIL)
        answer_reveal = visuals.get("answer_reveal")
        layers.extend(create_difficulty_list_pil(visuals.get("list_highlight", "1. EASY"), duration, answer_reveal))
        
        # CTA Overlay Logic
        cta_keywords = ["subscribe", "like", "button", "lock in"]
        if text and any(k in text.lower() for k in cta_keywords):
            cta_path = os.path.join(ASSETS_DIR, "overlays", "subscribe_cta.mp4")
            if os.path.exists(cta_path):
                cta_clip = VideoFileClip(cta_path).fx(vfx.mask_color, color=[0, 255, 0], thr=100, s=10)
                # Loop or trim to fit
                if cta_clip.duration < duration:
                    cta_clip = vfx.loop(cta_clip, duration=duration)
                else:
                    cta_clip = cta_clip.subclip(0, duration)
                
                cta_clip = cta_clip.resize(width=800).set_position(("center", "center")).set_start(0)
                layers.append(cta_clip)

        # Composite
        segment_comp = CompositeVideoClip(layers, size=(1080, 1920)).set_duration(duration)
        final_segment_clips.append(segment_comp)
        
        # Audio
        dialogue_audios.append(seg_audio.set_start(total_duration))
        total_duration += duration

    if not final_segment_clips: return

    # Assembly
    dialogue_track = CompositeAudioClip(dialogue_audios)
    if bg_music_path:
        bg_music = AudioFileClip(bg_music_path).volumex(0.1).fx(afx.audio_loop, duration=total_duration)
        final_audio = CompositeAudioClip([bg_music, dialogue_track])
    else:
        final_audio = dialogue_track

    final_video = concatenate_videoclips(final_segment_clips, method="compose")
    final_video = final_video.set_audio(final_audio)
    
    # Filename
    base_name = f"video_{video_id}_production"
    out_path = os.path.join(OUTPUT_DIR, f"{base_name}.mp4")
    counter = 1
    while os.path.exists(out_path):
        out_path = os.path.join(OUTPUT_DIR, f"{base_name}_{counter}.mp4")
        counter += 1
        
    final_video.write_videofile(
        out_path, fps=24, codec="libx264", audio_codec="aac", 
        threads=4, preset="ultrafast", logger='bar',
        temp_audiofile=os.path.join(OUTPUT_DIR, f"temp_audio_{video_id}.m4a")
    )
    print(f"✅ Finished: {out_path}")

def main():
    if not os.path.exists(SCRIPTS_FILE): return
    with open(SCRIPTS_FILE, "r", encoding="utf-8") as f:
        scripts = json.load(f)
    
    print(f"🔥 Starting PIL-based render of {len(scripts)} videos...")
    for video in tqdm(scripts, desc="Total Progress", unit="video"):
        try:
            generate_video(video)
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
