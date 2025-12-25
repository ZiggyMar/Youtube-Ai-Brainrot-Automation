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

def create_pil_text_image(text, font_path, color, stroke_width=6):
    """Generates a transparent PIL Image with stroked text, auto-scaling to fit 900px width."""
    font_size = 110
    max_width = 900
    
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()

    # Create dummy image for measurement
    dummy_img = Image.new('RGBA', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    
    # Auto-scale font size
    while True:
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        w = bbox[2] - bbox[0]
        if w <= max_width or font_size <= 20:
            break
        font_size -= 5
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            break
            
    # Final dimensions (with padding)
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    w = bbox[2] - bbox[0] + 20
    h = bbox[3] - bbox[1] + 20
    
    # Create final image
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw text centered in the image
    # Note: textbbox coordinates are relative to (0,0)
    # We want to draw at (10, 10) padding
    draw.text((10, 10), text, font=font, fill=color, 
              stroke_width=stroke_width, stroke_fill="black")
              
    return np.array(img)

def create_perfect_subtitles(json_path, font_path, color):
    """Creates subtitle clips using Whisper JSON timestamps."""
    if not os.path.exists(json_path):
        return []
        
    with open(json_path, 'r', encoding='utf-8') as f:
        words = json.load(f)
        
    if not words: return []
    
    clips = []
    
    # Group words into chunks of 2
    chunks = []
    for i in range(0, len(words), 2):
        chunk_words = words[i:i+2]
        text_str = " ".join([w["word"] for w in chunk_words])
        start_t = chunk_words[0]["start"]
        end_t = chunk_words[-1]["end"]
        chunks.append({"text": text_str, "start": start_t, "end": end_t})
        
    for chunk in chunks:
        duration = chunk["end"] - chunk["start"]
        if duration <= 0: continue
        
        img_array = create_pil_text_image(chunk["text"].upper(), font_path, color)
        txt_clip = ImageClip(img_array).set_duration(duration)
        txt_clip = txt_clip.set_start(chunk["start"]).set_position(("center", 1150))
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

        # Use a simpler text creation for list
        img_array = create_pil_text_image(display_text, CUSTOM_FONT_PATH, color, stroke_width=2)
        # Force resize if needed or just rely on auto-scale in function
        # But for list we want consistent size usually. 
        # The auto-scale function starts at 110, which is big. 
        # We should probably make a separate function or param for size, but user asked for specific logic.
        # User requirement: "Start size 110" was for subtitles. 
        # For list, let's just use the same function but maybe scale down the result if it's huge?
        # Actually, let's modify create_pil_text_image to accept start_size
        
        # Re-implementing specific list text logic to be safe and consistent
        try:
            font = ImageFont.truetype(CUSTOM_FONT_PATH, 50)
        except:
            font = ImageFont.load_default()
            
        dummy = Image.new('RGBA', (1, 1))
        draw = ImageDraw.Draw(dummy)
        bbox = draw.textbbox((0, 0), display_text, font=font, stroke_width=2)
        w, h = bbox[2]-bbox[0]+20, bbox[3]-bbox[1]+20
        img = Image.new('RGBA', (w, h), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.text((10,10), display_text, font=font, fill=color, stroke_width=2, stroke_fill="black")
        
        txt_clip = ImageClip(np.array(img)).set_duration(duration)
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
    print(f"🎬 Rendering Video {video_id} with Perfect Sync...")
    
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
        json_path = os.path.join(AUDIO_CACHE_DIR, f"v{video_id}_s{i}_{speaker}.json")
        
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
                        start_x = -1000 
                        cur_x = start_x + (target_x - start_x) * ease
                        return (int(cur_x), "bottom")
                    return ("center", "bottom")

                char_clip = (ImageClip(char_path).resize(height=800)
                             .rotate(lambda t: 2 * np.sin(2 * np.pi * t / 3.0))
                             .set_duration(duration)
                             .set_position(slide_pos))
                layers.append(char_clip)
                
                # SFX
                sfx_dir = os.path.join(ASSETS_DIR, "Sounds")
                if os.path.exists(sfx_dir):
                    sfx_files = glob.glob(os.path.join(sfx_dir, "*.wav"))
                    if sfx_files:
                        sfx_clip = AudioFileClip(random.choice(sfx_files)).volumex(0.05)
                        if sfx_clip.duration > duration: sfx_clip = sfx_clip.subclip(0, duration)
                        dialogue_audios.append(sfx_clip.set_start(total_duration))

        # Subtitles (Perfect Sync)
        if text and not is_timer:
            color = visuals.get("subtitle_color", "yellow")
            layers.extend(create_perfect_subtitles(json_path, CUSTOM_FONT_PATH, color))
            
        # Timer
        if is_timer:
            timer_overlay = (timer_clip.fx(vfx.mask_color, color=[0, 255, 0], thr=100, s=10)
                             .resize(width=900).set_position("center").set_duration(duration))
            layers.append(timer_overlay)
            
        # Difficulty List
        answer_reveal = visuals.get("answer_reveal")
        layers.extend(create_difficulty_list_pil(visuals.get("list_highlight", "1. EASY"), duration, answer_reveal))
        
        # CTA Overlay Logic
        cta_keywords = ["subscribe", "like", "button", "lock in"]
        if text and any(k in text.lower() for k in cta_keywords):
            cta_path = os.path.join(ASSETS_DIR, "overlays", "subscribe_cta.mp4")
            if os.path.exists(cta_path):
                cta_clip = VideoFileClip(cta_path).fx(vfx.mask_color, color=[0, 255, 0], thr=100, s=10)
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
    
    print(f"🔥 Starting Perfect Sync Render of {len(scripts)} videos...")
    for video in tqdm(scripts, desc="Total Progress", unit="video"):
        try:
            generate_video(video)
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
