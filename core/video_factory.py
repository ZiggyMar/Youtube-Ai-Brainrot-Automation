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
import concurrent.futures
import time
import subprocess

# Configuration
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
SCRIPTS_FILE = os.path.join(DATA_DIR, "video_scripts.json")
AUDIO_CACHE_DIR = os.path.join(PROJECT_ROOT, "audio_cache")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# FFmpeg Configuration
FFMPEG_PATH = os.path.join(PROJECT_ROOT, "tools", "ffmpeg", "ffmpeg.exe")
if os.path.exists(FFMPEG_PATH):
    os.environ["IMAGEIO_FFMPEG_EXE"] = FFMPEG_PATH
    print(f"✅ Using Custom FFmpeg: {FFMPEG_PATH}")

def check_nvenc_support():
    """Checks if NVIDIA NVENC encoder is available."""
    try:
        cmd = [FFMPEG_PATH, "-encoders"]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if "h264_nvenc" in result.stdout:
            print("🚀 NVIDIA GPU Encoding (NVENC) Detected!")
            return True
    except Exception as e:
        print(f"⚠️ Could not check for NVENC: {e}")
    return False

HAS_NVENC = check_nvenc_support()

# Difficulty List Config
DIFFICULTY_LEVELS = [
    {"label": "1. EASY", "color": "#2ecc71"},       # Green
    {"label": "2. MEDIUM", "color": "#f39c12"},     # Orange
    {"label": "3. HARD", "color": "#9b59b6"},       # Purple
    {"label": "4. IMPOSSIBLE", "color": "#e74c3c"}  # Red
]

LAYOUT_CONFIG_FILE = os.path.join(DATA_DIR, "layout_config.json")
LAYOUT_CONFIG_ROOT = os.path.join(PROJECT_ROOT, "layout_config.json")

DEFAULT_LAYOUT = {
    "character": {"x": 0, "y": 1120, "width": 1080, "height": 850},
    "subtitles": {"x": 90, "y": 1050, "width": 900, "height": 150},
    "timer": {"x": 90, "y": 510, "width": 900, "height": 900},
    "cta": {"x": 140, "y": 560, "width": 800, "height": 800},
    "difficulty_list": {"x": 50, "y": 100, "width": 400, "height": 400, "font_size": 50}
}

def load_layout_config():
    # Check root first, then data dir
    target_path = LAYOUT_CONFIG_ROOT if os.path.exists(LAYOUT_CONFIG_ROOT) else LAYOUT_CONFIG_FILE
    
    if os.path.exists(target_path):
        try:
            with open(target_path, 'r') as f:
                config = json.load(f)
                print(f"✅ Loaded Custom Layout from {target_path}")
                # Merge with defaults to ensure all keys exist
                final_config = DEFAULT_LAYOUT.copy()
                for key in config:
                    if key in final_config:
                        final_config[key].update(config[key])
                return final_config
        except Exception as e:
            print(f"⚠️ Error loading layout config: {e}")
    return DEFAULT_LAYOUT

LAYOUT = load_layout_config()

def validate_video_asset(path):
    """Checks if a video file is readable by MoviePy."""
    if not os.path.exists(path): return False
    try:
        with VideoFileClip(path) as clip:
            _ = clip.get_frame(0)
        return True
    except Exception as e:
        print(f"⚠️ Asset validation failed for {path}: {e}")
        return False

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
    return None # PIL will handle None by loading default

CUSTOM_FONT_PATH = get_font_path()

def create_pil_text_image(text, font_path, color, stroke_width=6):
    """Generates a transparent PIL Image with stroked text, auto-scaling to fit width."""
    font_size = 110
    max_width = LAYOUT["subtitles"]["width"]
    
    try:
        if font_path:
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
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
            if font_path:
                font = ImageFont.truetype(font_path, font_size)
            else:
                break
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
        txt_clip = txt_clip.set_start(chunk["start"]).set_position(("center", LAYOUT["subtitles"]["y"]))
        clips.append(txt_clip)
        
    return clips

def create_difficulty_list_pil(active_label, duration, revealed_answers=None):
    """Creates the difficulty list using PIL."""
    if revealed_answers is None:
        revealed_answers = {}

    clips = []
    for i, level in enumerate(DIFFICULTY_LEVELS):
        original_label = level["label"]
        is_active = original_label == active_label
        
        # Determine display text
        if original_label in revealed_answers:
            prefix = original_label.split(".")[0]
            answer_text = revealed_answers[original_label]
            display_text = f"{prefix}. {answer_text.upper()}"
        else:
            display_text = original_label

        # Color logic: Always use the level's color
        color = level["color"]
        
        try:
            font_size = LAYOUT["difficulty_list"].get("font_size", 50)
            if CUSTOM_FONT_PATH:
                font = ImageFont.truetype(CUSTOM_FONT_PATH, font_size)
            else:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
            font_size = 50
            
        dummy = Image.new('RGBA', (1, 1))
        draw = ImageDraw.Draw(dummy)
        bbox = draw.textbbox((0, 0), display_text, font=font, stroke_width=3)
        w, h = bbox[2]-bbox[0]+20, bbox[3]-bbox[1]+20
        img = Image.new('RGBA', (w, h), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        
        # Draw text with stroke
        draw.text((10,10), display_text, font=font, fill=color, stroke_width=3, stroke_fill="black")
        
        txt_clip = ImageClip(np.array(img)).set_duration(duration)
        spacing = font_size + 20
        txt_clip = txt_clip.set_position((LAYOUT["difficulty_list"]["x"], LAYOUT["difficulty_list"]["y"] + i * spacing))
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

def generate_video(video_data, use_gpu=False):
    video_id = video_data["video_id"]
    print(f"🎬 Rendering Video {video_id} with Perfect Sync... (GPU: {use_gpu})")
    
    # 1. Calculate Total Duration First
    total_duration = 0
    for i, segment in enumerate(video_data.get("segments", []), start=1):
        visuals = segment.get("visuals", {})
        speaker = segment.get("speaker", "")
        is_timer = visuals.get("show_timer", False)
        
        audio_path = os.path.join(AUDIO_CACHE_DIR, f"v{video_id}_s{i}_{speaker}.wav")
        if is_timer:
            timer_path = os.path.join(ASSETS_DIR, "overlays", "timer.mp4")
            if os.path.exists(timer_path):
                with VideoFileClip(timer_path) as tc:
                    total_duration += tc.duration
        elif os.path.exists(audio_path):
            with AudioFileClip(audio_path) as ac:
                total_duration += ac.duration

    # 2. Background with Random Start
    bg_files = glob.glob(os.path.join(ASSETS_DIR, "backgrounds", "*.mp4"))
    if not bg_files: return
    
    bg_path = random.choice(bg_files)
    bg_source = VideoFileClip(bg_path).without_audio()
    
    # Random Start Point
    if bg_source.duration > total_duration:
        max_start = bg_source.duration - total_duration
        start_time = random.uniform(0, max_start)
        bg_source = bg_source.subclip(start_time, start_time + total_duration)
    else:
        # Loop if background is too short
        bg_source = bg_source.fx(vfx.loop, duration=total_duration)

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
    keep_alive_clips = []  # Prevent premature GC
    current_time = 0
    bg_cursor = 0
    cta_shown = False
    revealed_answers = {}
    
    # Mapping from script tags to level labels
    LEVEL_MAPPING = {
        "2. R1": "1. EASY",
        "3. R2": "2. MEDIUM",
        "4. R3": "3. HARD",
        "5. R4": "4. IMPOSSIBLE"
    }
    
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
            try:
                timer_clip = VideoFileClip(timer_path)
                keep_alive_clips.append(timer_clip) # Keep alive
                duration = timer_clip.duration
                seg_audio = timer_clip.audio
            except Exception as e:
                print(f"⚠️ Skipping timer segment: {timer_path} error: {e}")
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
                    target_x = LAYOUT["character"]["x"]
                    target_y = LAYOUT["character"]["y"]
                    if t < SLIDE_DUR:
                        prog = t / SLIDE_DUR
                        ease = 1 - (1 - prog) ** 3
                        start_x = -1000 
                        cur_x = start_x + (target_x - start_x) * ease
                        return (int(cur_x), target_y)
                    return (target_x, target_y)

                char_clip = (ImageClip(char_path).resize(height=LAYOUT["character"]["height"])
                             .rotate(lambda t: 2 * np.sin(2 * np.pi * t / 3.0))
                             .set_duration(duration)
                             .set_position(slide_pos))
                layers.append(char_clip)
                
                # SFX
                sfx_dir = os.path.join(ASSETS_DIR, "Sounds")
                if os.path.exists(sfx_dir):
                    sfx_files = glob.glob(os.path.join(sfx_dir, "*.wav"))
                    if sfx_files:
                        sfx_clip = AudioFileClip(random.choice(sfx_files)).volumex(0.15)
                        if sfx_clip.duration > duration: sfx_clip = sfx_clip.subclip(0, duration)
                        dialogue_audios.append(sfx_clip.set_start(current_time))

        # Subtitles (Perfect Sync)
        if text and not is_timer:
            color = visuals.get("subtitle_color", "yellow")
            layers.extend(create_perfect_subtitles(json_path, CUSTOM_FONT_PATH, color))
            
        # Timer
        if is_timer:
            timer_overlay = (timer_clip.fx(vfx.mask_color, color=[0, 255, 0], thr=100, s=10)
                             .resize(width=LAYOUT["timer"]["width"])
                             .set_position((LAYOUT["timer"]["x"], LAYOUT["timer"]["y"]))
                             .set_duration(duration))
            layers.append(timer_overlay)
            
        # Difficulty List
        raw_highlight = visuals.get("list_highlight", "")
        active_label = LEVEL_MAPPING.get(raw_highlight, raw_highlight)
        
        answer_reveal = visuals.get("answer_reveal")
        if answer_reveal and active_label in [l["label"] for l in DIFFICULTY_LEVELS]:
            revealed_answers[active_label] = answer_reveal
            
        layers.extend(create_difficulty_list_pil(active_label, duration, revealed_answers))
        
        # CTA Overlay Logic
        cta_keywords = ["subscribe", "like", "button", "lock in"]
        if not cta_shown and text and any(k in text.lower() for k in cta_keywords):
            cta_shown = True
            # Use the pre-keyed Alpha MOV file if it exists (Much faster/stable)
            cta_path_alpha = os.path.join(ASSETS_DIR, "overlays", "subscribe_cta_alpha.mov")
            cta_path_orig = os.path.join(ASSETS_DIR, "overlays", "subscribe_cta.mp4")
            
            target_cta = cta_path_alpha if os.path.exists(cta_path_alpha) else cta_path_orig
            
            try:
                # Try to load the CTA
                cta_source = VideoFileClip(target_cta, has_mask=True) # has_mask=True for Alpha channel
                keep_alive_clips.append(cta_source) # Keep alive
                
                # Only apply green screen key if we are forced to use the MP4
                if target_cta.endswith(".mp4"):
                    cta_clip = cta_source.fx(vfx.mask_color, color=[0, 255, 0], thr=100, s=10)
                else:
                    cta_clip = cta_source # Alpha is already built-in!

                # Play CTA once. Do NOT loop it (causes freezing).
                if cta_clip.duration > duration:
                    cta_clip = cta_clip.subclip(0, duration)
                    if cta_source.audio:
                        cta_audio = cta_source.audio.subclip(0, duration).volumex(0.1)
                        dialogue_audios.append(cta_audio.set_start(current_time))
                else:
                    # Shorter than segment? Just play it once and let it end.
                    if cta_source.audio:
                        cta_audio = cta_source.audio.volumex(0.1)
                        dialogue_audios.append(cta_audio.set_start(current_time))
                
                # Apply layout config
                cta_clip = cta_clip.resize(width=LAYOUT["cta"]["width"]).set_position((LAYOUT["cta"]["x"], LAYOUT["cta"]["y"])).set_start(0)
                layers.append(cta_clip)
                print(f"   - Added CTA overlay (Duration: {cta_clip.duration:.2f}s)")
            except Exception as e:
                print(f"⚠️ Warning: Failed to load CTA overlay: {e}")
                cta_shown = False

        # Composite
        segment_comp = CompositeVideoClip(layers, size=(1080, 1920)).set_duration(duration)
        final_segment_clips.append(segment_comp)
        
        # Audio
        dialogue_audios.append(seg_audio.set_start(current_time))
        current_time += duration

    if not final_segment_clips: return

    # Assembly
    dialogue_track = CompositeAudioClip(dialogue_audios)
    if bg_music_path:
        bg_music = AudioFileClip(bg_music_path).volumex(0.1).fx(afx.audio_loop, duration=current_time)
        final_audio = CompositeAudioClip([bg_music, dialogue_track])
    else:
        final_audio = dialogue_track

    final_video = concatenate_videoclips(final_segment_clips, method="compose")
    final_video = final_video.set_audio(final_audio)
    
    # Filename
    import re
    def sanitize_filename(name):
        return re.sub(r'[<>:"/\\|?*]', '', name).strip()

    title = video_data.get("title", "")
    if title:
        safe_title = sanitize_filename(title)
        base_name = safe_title
    else:
        base_name = f"video_{video_id}_production"
    
    out_path = os.path.join(OUTPUT_DIR, f"{base_name}.mp4")
    counter = 1
    while os.path.exists(out_path):
        out_path = os.path.join(OUTPUT_DIR, f"{base_name}_{counter}.mp4")
        counter += 1
        
    temp_audio = os.path.join(OUTPUT_DIR, f"temp_audio_{video_id}.m4a")
    
    # Encoding Parameters
    if use_gpu and HAS_NVENC:
        codec = "h264_nvenc"
        ffmpeg_params = [
            "-rc:v", "vbr", 
            "-cq:v", "19", 
            "-preset", "p7"  # High quality, fast
        ]
        preset = None # NVENC doesn't use x264 presets
    else:
        codec = "libx264"
        ffmpeg_params = None
        preset = "ultrafast"

    final_video.write_videofile(
        out_path, fps=24, codec=codec, audio_codec="aac", 
        threads=4, preset=preset, ffmpeg_params=ffmpeg_params,
        logger='bar', temp_audiofile=temp_audio
    )
    
    # Cleanup temp audio
    if os.path.exists(temp_audio):
        try:
            os.remove(temp_audio)
            print(f"🧹 Cleaned up temp audio: {temp_audio}")
        except:
            pass

    # Cleanup clips
    try:
        final_video.close()
        bg_source.close()
        for clip in keep_alive_clips:
            clip.close()
    except:
        pass

    print(f"✅ Finished: {out_path}")

def process_video_wrapper(video_data):
    """Wrapper for parallel execution."""
    try:
        generate_video(video_data, use_gpu=HAS_NVENC)
        return True
    except Exception as e:
        print(f"❌ Error processing video {video_data.get('video_id')}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    if not os.path.exists(SCRIPTS_FILE): return
    with open(SCRIPTS_FILE, "r", encoding="utf-8") as f:
        scripts = json.load(f)
    
    print(f"🔥 Starting Perfect Sync Render of {len(scripts)} videos...")
    
    # Determine max workers (leave some CPU for system)
    max_workers = max(1, os.cpu_count() - 2)
    print(f"🚀 Starting Parallel Rendering with {max_workers} workers...")
    
    start_time = time.time()
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(tqdm(executor.map(process_video_wrapper, scripts), total=len(scripts), unit="video"))
        
    elapsed = time.time() - start_time
    print(f"✅ All videos processed in {elapsed:.2f} seconds!")

if __name__ == "__main__":
    # Windows multiprocessing support
    import multiprocessing
    multiprocessing.freeze_support()
    main()
