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

# Pillow >=10 removed Image.ANTIALIAS (used by moviepy 1.0.3's resize). Shim for forward-compat.
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

import subprocess
import gc

# Configuration
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
SCRIPTS_FILE = os.path.join(DATA_DIR, "video_scripts.json")
AUDIO_CACHE_DIR = os.path.join(PROJECT_ROOT, "audio_cache")
TEMP_SEGMENTS_DIR = os.path.join(OUTPUT_DIR, "temp_segments")

os.makedirs(OUTPUT_DIR, exist_ok=True)
READY_TO_POST_DIR = os.path.join(OUTPUT_DIR, "ready_to_post")
os.makedirs(READY_TO_POST_DIR, exist_ok=True)
os.makedirs(TEMP_SEGMENTS_DIR, exist_ok=True)

# FFmpeg Configuration (cross-platform: bundled exe on Windows, system ffmpeg on Linux/server)
import shutil
def _resolve_ffmpeg():
    local = os.path.join(PROJECT_ROOT, "tools", "ffmpeg", "ffmpeg.exe")
    if os.path.exists(local):
        return local
    sys_ff = shutil.which("ffmpeg")
    if sys_ff:
        return sys_ff
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"
FFMPEG_PATH = _resolve_ffmpeg()
os.environ["IMAGEIO_FFMPEG_EXE"] = FFMPEG_PATH
print(f"✅ Using FFmpeg: {FFMPEG_PATH}")


# Difficulty List Config
DIFFICULTY_LEVELS = [
    {"label": "1. EASY", "color": "#2ecc71"},       # Green
    {"label": "2. MEDIUM", "color": "#f39c12"},     # Orange
    {"label": "3. HARD", "color": "#9b59b6"},       # Purple
    {"label": "4. IMPOSSIBLE", "color": "#e74c3c"}  # Red
]

# Brighter, screen-readable subtitle colors (PIL's default "blue"/"cyan" are too dark on gameplay).
SUBTITLE_COLOR_MAP = {
    "yellow": "#FFE600",
    "blue":   "#3FA9F5",   # bright sky-blue (was near-black navy)
    "cyan":   "#4FE3E3",
    "green":  "#3DDC5C",
    "pink":   "#FF6FB5",
    "red":    "#FF5151",
    "white":  "#FFFFFF",
    "brown":  "#D08A4E",
    "orange": "#FFA033",
}

DEFAULT_LAYOUT = {
    "character": {"x": 0, "y": 1120, "width": 1080, "height": 850},
    "subtitles": {"x": 90, "y": 1050, "width": 900, "height": 150},
    "timer": {"x": 0, "y": 0, "width": 1080, "height": 1920, "scale": 1.0},
    "cta": {"x": 0, "y": 0, "width": 1080, "height": 1920, "scale": 1.0},
    "difficulty_list": {"x": 50, "y": 100, "width": 400, "height": 400, "font_size": 50}
}

def load_layout_config():
    layout_root = os.path.join(PROJECT_ROOT, "layout_config.json")
    layout_data = os.path.join(DATA_DIR, "layout_config.json")
    target_path = layout_root if os.path.exists(layout_root) else layout_data
    
    if os.path.exists(target_path):
        try:
            with open(target_path, 'r') as f:
                config = json.load(f)
                print(f"✅ Loaded Custom Layout from {target_path}")
                final_config = DEFAULT_LAYOUT.copy()
                for key in config:
                    if key in final_config:
                        final_config[key].update(config[key])
                return final_config
        except Exception as e:
            print(f"⚠️ Error loading layout config: {e}")
    return DEFAULT_LAYOUT

LAYOUT = load_layout_config()

def get_font_path():
    font_path = os.path.join(ASSETS_DIR, "Font", "Burbank.ttf")
    if os.path.exists(font_path):
        print(f"✅ Using PIL Font: {font_path}")
        return font_path
    return None

CUSTOM_FONT_PATH = get_font_path()

def create_pil_text_image(text, font_path, color, stroke_width=6):
    font_size = 110
    max_width = LAYOUT["subtitles"]["width"]
    try:
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    dummy_img = Image.new('RGBA', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    while True:
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        if (bbox[2] - bbox[0]) <= max_width or font_size <= 20: break
        font_size -= 5
        try:
            if font_path: font = ImageFont.truetype(font_path, font_size)
            else: break
        except: break
            
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    w, h = bbox[2] - bbox[0] + 20, bbox[3] - bbox[1] + 20
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), text, font=font, fill=color, stroke_width=stroke_width, stroke_fill="black")
    return np.array(img)

def create_perfect_subtitles(json_path, font_path, color):
    # Brighten dark named colors (e.g. "Blue") for on-screen readability.
    color = SUBTITLE_COLOR_MAP.get(str(color).strip().lower(), color)
    if not os.path.exists(json_path): return []
    with open(json_path, 'r', encoding='utf-8') as f:
        words = json.load(f)
    if not words: return []
    
    # Subtle "bing" pop on every subtitle chunk: snap up to ~118% then settle to 100% in the
    # first ~0.18s. Kills the flat, statically-spawned look without ever drifting off-screen
    # (position stays centered; the tiny vertical growth is well within frame).
    def _sub_pop(t):
        if t < 0.10:
            return 0.85 + (1.18 - 0.85) * (t / 0.10)
        elif t < 0.18:
            return 1.18 - 0.18 * ((t - 0.10) / 0.08)
        return 1.0

    clips = []
    for i in range(0, len(words), 2):
        chunk_words = words[i:i+2]
        text_str = " ".join([w["word"] for w in chunk_words])
        start_t, end_t = chunk_words[0]["start"], chunk_words[-1]["end"]
        duration = end_t - start_t
        if duration <= 0: continue
        img_array = create_pil_text_image(text_str.upper(), font_path, color)
        txt_clip = (ImageClip(img_array).set_duration(duration)
                    .resize(_sub_pop)
                    .set_start(start_t)
                    .set_position(("center", LAYOUT["subtitles"]["y"])))
        clips.append(txt_clip)
    return clips

def create_difficulty_list_pil(active_label, duration, revealed_answers=None):
    if revealed_answers is None: revealed_answers = {}
    clips = []
    for i, level in enumerate(DIFFICULTY_LEVELS):
        original_label = level["label"]
        if original_label in revealed_answers:
            prefix = original_label.split(".")[0]
            display_text = f"{prefix}. {revealed_answers[original_label].upper()}"
        else:
            display_text = original_label

        color = level["color"]
        font_size = LAYOUT["difficulty_list"].get("font_size", 50)
        try:
            font = ImageFont.truetype(CUSTOM_FONT_PATH, font_size) if CUSTOM_FONT_PATH else ImageFont.load_default()
        except:
            font = ImageFont.load_default()
            
        dummy = Image.new('RGBA', (1, 1))
        draw = ImageDraw.Draw(dummy)
        bbox = draw.textbbox((0, 0), display_text, font=font, stroke_width=3)
        w, h = bbox[2]-bbox[0]+20, bbox[3]-bbox[1]+20
        img = Image.new('RGBA', (w, h), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.text((10,10), display_text, font=font, fill=color, stroke_width=3, stroke_fill="black")
        
        txt_clip = ImageClip(np.array(img)).set_duration(duration)
        spacing = font_size + 20
        txt_clip = txt_clip.set_position((LAYOUT["difficulty_list"]["x"], LAYOUT["difficulty_list"]["y"] + i * spacing))
        clips.append(txt_clip)
    return clips

def create_hook_overlay(text, duration):
    if not text: return None

    font_size = 165
    try:
        font = ImageFont.truetype(CUSTOM_FONT_PATH, font_size) if CUSTOM_FONT_PATH else ImageFont.load_default()
    except:
        font = ImageFont.load_default()
        
    # Create text image
    dummy = Image.new('RGBA', (1, 1))
    draw = ImageDraw.Draw(dummy)
    
    # Word wrap logic (simple)
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        bbox = draw.textbbox((0, 0), " ".join(current_line), font=font)
        if bbox[2] > 900: # Max width
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    lines.append(" ".join(current_line))
    
    final_text = "\n".join(lines)
    
    bbox = draw.textbbox((0, 0), final_text, font=font, stroke_width=12)
    w, h = bbox[2]-bbox[0]+48, bbox[3]-bbox[1]+48

    img = Image.new('RGBA', (w, h), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    # Hook text ALWAYS gets the animated RGB rainbow cycle (drawn white, then hue-cycled per
    # frame) - user preference. Heavy black outline always.
    rainbow = True
    fill = "white"
    draw.text((24, 24), final_text, font=font, fill=fill, stroke_width=12, stroke_fill="black", align="center")

    # Slam-then-clear: the hook lives ~1.9s (grab the open, then reveal the clean scoreboard).
    hook_dur = min(1.9, duration)
    clip = ImageClip(np.array(img)).set_duration(hook_dur)

    # Frame-1 SLAM: pop the hook onto screen instantly (kills the slow fade).
    def _hook_pop(t):
        if t < 0.16:
            return 0.4 + (1.18 - 0.4) * (t / 0.16)
        elif t < 0.28:
            return 1.18 - 0.18 * ((t - 0.16) / 0.12)
        return 1.0
    clip = clip.resize(_hook_pop)

    if rainbow:
        import colorsys
        def _rgb_cycle(get_frame, t):
            fr = get_frame(t).astype("float32")
            r, g, b = colorsys.hsv_to_rgb((t / 1.5) % 1.0, 1.0, 1.0)
            fr[..., 0] *= r; fr[..., 1] *= g; fr[..., 2] *= b
            return fr.astype("uint8")
        clip = clip.fl(_rgb_cycle)

    # Slam in hard, then FADE OUT (don't hard-cut) so the hook gently clears the frame
    # before the scoreboard reveal. Fade occupies the last ~0.4s of its life.
    fade_d = min(0.4, hook_dur / 3)
    clip = clip.crossfadeout(fade_d)

    # Position BELOW the difficulty scoreboard so it never sits behind the 1/2/3/4 list.
    clip = clip.set_position(("center", 600))
    return clip

def find_character_image(speaker, character_field):
    speaker_map = {"SpongeBob": "SpongeBob", "Patrick": "Patrick", "Squidward": "Squidward", "Plankton": "Plankton", "MrKrabs": "Mr. Krabs"}
    target_folder_name = speaker_map.get(speaker, speaker)
    char_folder = os.path.join(ASSETS_DIR, "characters", target_folder_name)
    
    clean_name = character_field.replace(".png", "")
    mood = clean_name.split("_")[1] if "_" in clean_name else clean_name
    specific_path = os.path.join(char_folder, f"{mood}.png")
    
    if os.path.exists(specific_path): return specific_path
    if os.path.exists(char_folder):
        files = glob.glob(os.path.join(char_folder, "*.png"))
        if files: return random.choice(files)
    return None

def preprocess_assets():
    print("🛠️ Pre-processing Assets...")
    for name, key in [("timer", "timer"), ("subscribe_cta", "cta")]:
        mp4 = os.path.join(ASSETS_DIR, "overlays", f"{name}.mp4")
        mov = os.path.join(ASSETS_DIR, "overlays", f"{name}_alpha_scaled.mov")
        if os.path.exists(mp4) and not os.path.exists(mov):
            w, h = LAYOUT[key]["width"], LAYOUT[key]["height"]
            print(f"   - Converting {name} to {w}x{h} Alpha MOV...")
            cmd = [FFMPEG_PATH, "-y", "-i", mp4, "-vf", f"chromakey=0x00FF00:0.1:0.1,scale={w}:{h}", "-c:v", "qtrle", mov]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def render_segment(video_id, i, segment, bg_clip, revealed_answers, cta_shown, timer_clip_ref=None, cta_clip_ref=None, woosh_file=None, is_first_segment=False, hook_text=None):
    visuals = segment.get("visuals", {})
    text = segment.get("text", "")
    speaker = segment.get("speaker", "")
    is_timer = visuals.get("show_timer", False)
    duration = bg_clip.duration
    
    audio_path = os.path.join(AUDIO_CACHE_DIR, f"v{video_id}_s{i}_{speaker}.wav")
    json_path = os.path.join(AUDIO_CACHE_DIR, f"v{video_id}_s{i}_{speaker}.json")
    
    # Audio Logic: Timer + Character Mixing
    seg_audio = None
    character_audio = None
    
    # Load Timer Audio explicitly from MP4 if available (MOV might miss audio)
    timer_audio_source = None
    if is_timer:
        timer_mp4 = os.path.join(ASSETS_DIR, "overlays", "timer.mp4")
        if os.path.exists(timer_mp4):
            timer_audio_source = AudioFileClip(timer_mp4)
        elif timer_clip_ref and timer_clip_ref.audio:
            timer_audio_source = timer_clip_ref.audio

    if is_timer and timer_audio_source:
        seg_audio = timer_audio_source.set_start(0)
        # If we are mixing, lower the timer volume slightly so voice is clear
        if os.path.exists(audio_path):
            seg_audio = seg_audio.volumex(0.6)
    
    if os.path.exists(audio_path):
        character_audio = AudioFileClip(audio_path).set_start(0)
        if seg_audio:
            # Mix timer ticking with character speech
            # Ensure both start at 0
            # Use duration of the segment (which is speech + 0.5s)
            seg_audio = CompositeAudioClip([seg_audio, character_audio])
        else:
            seg_audio = character_audio

    # Hook Sound Logic
    hook_audio = None
    if is_first_segment:
        hook_dir = os.path.join(ASSETS_DIR, "Sounds", "Hook")
        if os.path.exists(hook_dir):
            hooks = glob.glob(os.path.join(hook_dir, "*.*"))
            if hooks:
                hook_file = random.choice(hooks)
                print(f"   - 🎣 Adding Hook Sound: {os.path.basename(hook_file)}")
                try:
                    hook_audio = AudioFileClip(hook_file).volumex(0.18).set_start(0)
                    # Mix it in
                    if seg_audio:
                        seg_audio = CompositeAudioClip([seg_audio, hook_audio])
                    else:
                        seg_audio = hook_audio
                except Exception as e:
                    print(f"⚠️ Failed to load hook sound: {e}")

    layers = [bg_clip]
    keep_alive = []

    # Character Logic (Show character even during timer if they are speaking)
    if (not is_timer) or (is_timer and character_audio):
        char_path = find_character_image(speaker, visuals.get("character", ""))
        if char_path:
            # On a timer segment the character only stays on screen while speaking, then leaves;
            # the timer overlay & background keep running for the full segment duration.
            char_display_dur = duration
            if is_timer and character_audio is not None:
                char_display_dur = min(character_audio.duration + 0.3, duration)
            def slide_pos(t):
                # Frame-1 retention fix: anchor character INSTANTLY on segment 1.
                # The 0.4s slide burned 21% of the hook's 1.9s lifetime with the
                # anchor off-screen during the make-or-break swipe-or-stay window.
                # Slide-in is kept for later segments where it adds personality
                # and isn't competing with first-impression retention.
                if is_first_segment and LAYOUT.get("HOOK_STYLE", "punch") == "punch":
                    return (LAYOUT["character"]["x"], LAYOUT["character"]["y"])
                if t < 0.4:
                    prog = t / 0.4
                    ease = 1 - (1 - prog) ** 3
                    return (int(-1000 + (LAYOUT["character"]["x"] + 1000) * ease), LAYOUT["character"]["y"])
                return (LAYOUT["character"]["x"], LAYOUT["character"]["y"])
            # Pre-roll freeze+zoom on the FIRST segment only: a 0.2s (6 frames @ 30fps)
            # 1.05 -> 1.00 character "settle" gives the eye a motion vector to lock
            # onto at t=0, complementing the hook text's scale-pop without competing
            # with it. No-op for non-first segments and for HOOK_STYLE == "classic".
            _char_zoom_active = is_first_segment and LAYOUT.get("HOOK_STYLE", "punch") == "punch"
            def _char_zoom(t):
                if _char_zoom_active and t < 0.2:
                    return 1.05 - 0.05 * (t / 0.2)
                return 1.0
            char_clip = ImageClip(char_path).resize(height=LAYOUT["character"]["height"]).resize(_char_zoom).rotate(lambda t: 2 * np.sin(2 * np.pi * t / 3.0)).set_duration(char_display_dur).set_position(slide_pos)
            layers.append(char_clip)
            keep_alive.append(char_clip)
            
            # SFX
            if woosh_file and os.path.exists(woosh_file):
                sfx = AudioFileClip(woosh_file).volumex(0.15).set_start(0)
                if sfx.duration > duration: sfx = sfx.subclip(0, duration)
                seg_audio = CompositeAudioClip([seg_audio, sfx]) if seg_audio else sfx

    # Timer Overlay (Add BEFORE subtitles so it doesn't cover them)
    if is_timer and timer_clip_ref:
        # Use preloaded timer clip
        timer_overlay = timer_clip_ref.copy().set_position((LAYOUT["timer"]["x"], LAYOUT["timer"]["y"])).set_duration(duration)
        layers.append(timer_overlay)
        keep_alive.append(timer_overlay)

    # Subtitles (Add AFTER timer)
    if text:
        subs = create_perfect_subtitles(json_path, CUSTOM_FONT_PATH, visuals.get("subtitle_color", "yellow"))
        layers.extend(subs)
        keep_alive.extend(subs)

    # Hook Overlay (First Segment Only)
    if is_first_segment and hook_text:
        hook_clip = create_hook_overlay(hook_text, duration)
        if hook_clip:
            layers.append(hook_clip)
            keep_alive.append(hook_clip)

    LEVEL_MAPPING = {"2. R1": "1. EASY", "3. R2": "2. MEDIUM", "4. R3": "3. HARD", "5. R4": "4. IMPOSSIBLE"}
    raw_highlight = visuals.get("list_highlight", "")
    active_label = LEVEL_MAPPING.get(raw_highlight, raw_highlight)
    if visuals.get("answer_reveal"): revealed_answers[active_label] = visuals.get("answer_reveal")
    diff_list = create_difficulty_list_pil(active_label, duration, revealed_answers)
    layers.extend(diff_list)
    keep_alive.extend(diff_list)

    cta_audio_to_add = None
    # CTA Logic: Trigger on "subscribe" keyword
    if text and "subscribe" in text.lower() and cta_clip_ref:
        try:
            cta_clip = cta_clip_ref.copy().set_position((LAYOUT["cta"]["x"], LAYOUT["cta"]["y"])).set_start(0)
            if cta_clip.duration > duration: cta_clip = cta_clip.subclip(0, duration)
            
            if cta_clip_ref.audio:
                cta_audio_to_add = cta_clip_ref.audio.subclip(0, min(cta_clip_ref.audio.duration, duration)).volumex(0.1).set_start(0)
                
            layers.append(cta_clip)
            keep_alive.append(cta_clip)
            cta_shown = True
        except Exception as e:
            print(f"⚠️ CTA Error: {e}")

    segment_comp = CompositeVideoClip(layers, size=(1080, 1920)).set_duration(duration)
    seg_audios = [seg_audio] if seg_audio else []
    if cta_audio_to_add: seg_audios.append(cta_audio_to_add)
    if seg_audios: segment_comp = segment_comp.set_audio(CompositeAudioClip(seg_audios))

    out_path = os.path.join(TEMP_SEGMENTS_DIR, f"v{video_id}_s{i}.mp4")
    print(f"   - Rendering Segment {i} ({duration:.2f}s)...")
    
    try:
        segment_comp.write_videofile(
            out_path,
            fps=30,
            codec="libx264", 
            audio_codec="aac", 
            threads=1, 
            preset="ultrafast", 
            logger=None, 
            verbose=False
        )
    finally:
        # Crucial: Close EVERYTHING
        segment_comp.close()
        for c in keep_alive:
            try: c.close()
            except: pass
        if seg_audio:
            try: seg_audio.close()
            except: pass
        if timer_audio_source:
            try: timer_audio_source.close()
            except: pass
        if cta_audio_to_add:
            try: cta_audio_to_add.close()
            except: pass
        if character_audio:
            try: character_audio.close()
            except: pass
        if hook_audio:
            try: hook_audio.close()
            except: pass
        
        # Force garbage collection after each segment
        gc.collect()
        
    return out_path, cta_shown

def generate_video(video_data):
    video_id = video_data["video_id"]
    print(f"🎬 Rendering Video {video_id} (Segment-Based)...")
    
    # Preload Assets (Timer & CTA)
    timer_clip_ref = None
    cta_clip_ref = None
    
    # Timer: Prefer MP4 source and apply runtime mask for reliability
    timer_path = os.path.join(ASSETS_DIR, "overlays", "timer.mp4")
    if not os.path.exists(timer_path): timer_path = os.path.join(ASSETS_DIR, "overlays", "timer_alpha.mov")
    
    if os.path.exists(timer_path):
        # Force green screen removal for MP4, or if it's the MOV fallback (just in case)
        timer_clip_ref = VideoFileClip(timer_path)
        timer_clip_ref = timer_clip_ref.fx(vfx.mask_color, color=[0, 255, 0], thr=100, s=10)
        
        # Apply Scale
        timer_scale = LAYOUT["timer"].get("scale", 1.0)
        if timer_scale != 1.0:
            timer_clip_ref = timer_clip_ref.resize(timer_scale)
        else:
            timer_clip_ref = timer_clip_ref.resize(newsize=(LAYOUT["timer"]["width"], LAYOUT["timer"]["height"]))
            
        # Position Logic (Center in 1080x1920 frame if scaled, plus offset)
        if timer_scale != 1.0:
            # Calculate centered position relative to 1080x1920
            # The clip is now (1080*scale) x (1920*scale)
            # Centered at (1080-w)/2, (1920-h)/2
            # Add user offset (LAYOUT x, y)
            
            w, h = timer_clip_ref.size
            center_x = (1080 - w) // 2
            center_y = (1920 - h) // 2
            
            final_x = center_x + LAYOUT["timer"]["x"]
            final_y = center_y + LAYOUT["timer"]["y"]
            
            timer_clip_ref = timer_clip_ref.set_position((final_x, final_y))
        else:
             timer_clip_ref = timer_clip_ref.set_position((LAYOUT["timer"]["x"], LAYOUT["timer"]["y"]))

    # CTA: Prefer MP4 source and apply runtime mask for reliability
    cta_path = os.path.join(ASSETS_DIR, "overlays", "subscribe_cta.mp4")
    if not os.path.exists(cta_path): cta_path = os.path.join(ASSETS_DIR, "overlays", "subscribe_cta_alpha.mov")
    
    if os.path.exists(cta_path):
        # Force green screen removal for MP4, or if it's the MOV fallback (just in case)
        cta_clip_ref = VideoFileClip(cta_path)
        cta_clip_ref = cta_clip_ref.fx(vfx.mask_color, color=[0, 255, 0], thr=100, s=10)
            
        # Apply Scale
        cta_scale = LAYOUT["cta"].get("scale", 1.0)
        if cta_scale != 1.0:
            cta_clip_ref = cta_clip_ref.resize(cta_scale)
        else:
            cta_clip_ref = cta_clip_ref.resize(newsize=(LAYOUT["cta"]["width"], LAYOUT["cta"]["height"]))

        # Position Logic (Center in 1080x1920 frame if scaled, plus offset)
        if cta_scale != 1.0:
            w, h = cta_clip_ref.size
            center_x = (1080 - w) // 2
            center_y = (1920 - h) // 2
            
            final_x = center_x + LAYOUT["cta"]["x"]
            final_y = center_y + LAYOUT["cta"]["y"]
            
            cta_clip_ref = cta_clip_ref.set_position((final_x, final_y))
        else:
            cta_clip_ref = cta_clip_ref.set_position((LAYOUT["cta"]["x"], LAYOUT["cta"]["y"]))

    total_duration = 0
    segments_to_render = []
    for i, segment in enumerate(video_data.get("script", []), start=1):
        visuals = segment.get("visuals", {})
        speaker = segment.get("speaker", "")
        audio_path = os.path.join(AUDIO_CACHE_DIR, f"v{video_id}_s{i}_{speaker}.wav")
        seg_dur = 0
        
        # Determine duration based on audio or timer
        if visuals.get("show_timer"):
            if timer_clip_ref:
                seg_dur = timer_clip_ref.duration
            # If a character speaks DURING the timer (e.g. "Don't say X!" / "I bet they'll say X"),
            # the timer must still run its FULL length. The character appears, says the line, then
            # leaves while the clock keeps ticking. Only extend if speech is longer than the timer.
            if os.path.exists(audio_path):
                with AudioFileClip(audio_path) as ac:
                    seg_dur = max(seg_dur, ac.duration + 0.5)
        elif os.path.exists(audio_path):
            with AudioFileClip(audio_path) as ac: seg_dur = ac.duration
            
        if seg_dur > 0:
            total_duration += seg_dur
            segments_to_render.append((i, segment, seg_dur))

    if not segments_to_render: 
        if timer_clip_ref: timer_clip_ref.close()
        if cta_clip_ref: cta_clip_ref.close()
        return

    bg_files = glob.glob(os.path.join(ASSETS_DIR, "backgrounds", "*.mp4"))
    if not bg_files:
        print("❌ No background videos found in assets/backgrounds/")
        return
    # Robustly pick a USABLE background: some files probe fine but fail moviepy's
    # first-frame read. Never let one bad file kill an unattended render — try others.
    random.shuffle(bg_files)
    bg_source = None
    for bgf in bg_files:
        candidate = None
        try:
            candidate = VideoFileClip(bgf).without_audio()
            candidate.get_frame(0)  # force-validate the first frame
            bg_source = candidate
            print(f"   - 🎮 Background: {os.path.basename(bgf)}")
            break
        except Exception as e:
            print(f"   ⚠️ Skipping unreadable background '{os.path.basename(bgf)}': {e}")
            if candidate is not None:
                try: candidate.close()
                except: pass
    if bg_source is None:
        print("❌ No readable background videos available.")
        return
    
    # Random Speed Factor (1.1x to 1.4x)
    speed_factor = random.uniform(1.1, 1.4)
    print(f"   - ⏩ Gameplay Speed: {speed_factor:.2f}x")
    
    # We need more raw footage because speeding it up shortens it
    needed_raw_duration = total_duration * speed_factor
    
    if bg_source.duration > needed_raw_duration:
        # Pick a random start point
        start_t = random.uniform(0, bg_source.duration - needed_raw_duration)
        bg_segment = bg_source.subclip(start_t, start_t + needed_raw_duration)
    else:
        # Loop it to get enough raw footage
        bg_segment = bg_source.fx(vfx.loop, duration=needed_raw_duration)
        
    # Apply speed effect
    bg_full = bg_segment.fx(vfx.speedx, speed_factor)
    
    # Ensure exact duration
    bg_full = bg_full.set_duration(total_duration)
    
    w, h = bg_full.size
    if w/h > 9/16:
        new_w = h * (9/16)
        bg_full = bg_full.crop(x1=w/2 - new_w/2, width=new_w, height=h)
    else:
        new_h = w / (9/16)
        bg_full = bg_full.crop(y1=h/2 - new_h/2, width=w, height=new_h)
    bg_full = bg_full.resize((1080, 1920))

    segment_files, revealed_answers, cta_shown, bg_cursor = [], {}, False, 0
    
    # Pre-scan Woosh Sounds
    sfx_dir = os.path.join(ASSETS_DIR, "Sounds")
    available_wooshes = []
    if os.path.exists(sfx_dir):
        available_wooshes.extend(glob.glob(os.path.join(sfx_dir, "*.wav")))
        available_wooshes.extend(glob.glob(os.path.join(sfx_dir, "*.mp3")))
    character_woosh_map = {}

    for i, seg_data, dur in segments_to_render:
        # Assign Woosh Sound
        speaker = seg_data.get("speaker", "")
        if speaker and speaker not in character_woosh_map and available_wooshes:
            character_woosh_map[speaker] = random.choice(available_wooshes)

        bg_slice = bg_full.subclip(bg_cursor, bg_cursor + dur)
        bg_cursor += dur
        
        is_first = (i == 1)
        hook_txt = video_data.get("hook_text") if is_first else None
        seg_path, cta_shown = render_segment(video_id, i, seg_data, bg_slice, revealed_answers, cta_shown, timer_clip_ref, cta_clip_ref, woosh_file=character_woosh_map.get(speaker), is_first_segment=is_first, hook_text=hook_txt)
        
        segment_files.append(seg_path)
        bg_slice.close()
        gc.collect() # Extra collection between segments

    bg_full.close()
    bg_source.close()
    if timer_clip_ref: timer_clip_ref.close()
    if cta_clip_ref: cta_clip_ref.close()
    gc.collect()

    import re
    safe_title = re.sub(r'[<>:"/\\|?*]', '', video_data.get("title", f"video_{video_id}")).strip()
    out_path = os.path.join(OUTPUT_DIR, f"{safe_title}.mp4")
    
    concat_list = os.path.join(TEMP_SEGMENTS_DIR, f"v{video_id}_list.txt")
    print("   - Concatenating Segments...")
    temp_concat = os.path.join(TEMP_SEGMENTS_DIR, f"v{video_id}_concat.mp4")
    
    with open(concat_list, "w", encoding="utf-8") as f:
        for sf in segment_files:
            if sf:
                safe_sf = sf.replace('\\', '/')
                f.write(f"file '{safe_sf}'\n")

    subprocess.run([FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", temp_concat], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("   - Final Polish...")
    music_files = glob.glob(os.path.join(ASSETS_DIR, "music", "*.mp3"))
    bg_music = random.choice(music_files) if music_files else None
    if bg_music:
        # Random Music Speed (1.0x - 1.25x)
        music_speed = random.uniform(1.0, 1.25)
        audio_filter = f"atempo={music_speed:.4f},"
        print(f"   - 🎵 Applying Music Speed: {music_speed:.2f}x")

        # Add volume normalization
        audio_filter += "volume=0.1"
        
        cmd = [FFMPEG_PATH, "-y", "-i", temp_concat, "-stream_loop", "-1", "-i", bg_music, "-filter_complex", f"[1:a]{audio_filter}[music];[0:a][music]amix=inputs=2:duration=first[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest", out_path]
    else:
        cmd = [FFMPEG_PATH, "-y", "-i", temp_concat, "-c", "copy", out_path]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        if os.path.exists(concat_list): os.remove(concat_list)
        if os.path.exists(temp_concat): os.remove(temp_concat)
    except Exception as e:
        print(f"   ⚠️ Cleanup warning: {e}")

    for sf in segment_files:
        try:
            if sf and os.path.exists(sf): os.remove(sf)
        except: pass
    print(f"✅ Finished: {out_path}")

    # Move to ready_to_post
    try:
        final_path = os.path.join(READY_TO_POST_DIR, os.path.basename(out_path))
        import shutil
        shutil.move(out_path, final_path)
        print(f"📦 Moved to Ready to Post: {final_path}")
    except Exception as e:
        print(f"⚠️ Error moving video to ready_to_post: {e}")

def process_video_wrapper(video_data):
    try:
        generate_video(video_data)
        return True
    except Exception as e:
        print(f"❌ Error processing video {video_data.get('video_id')}: {e}")
        return False

def cleanup_temp_files():
    print("🧹 Cleaning temp files...")
    for f in glob.glob(os.path.join(OUTPUT_DIR, "temp_audio_*.m4a")) + glob.glob(os.path.join(TEMP_SEGMENTS_DIR, "*.*")):
        try: os.remove(f)
        except: pass

def main():
    cleanup_temp_files()
    preprocess_assets()
    if not os.path.exists(SCRIPTS_FILE): return
    with open(SCRIPTS_FILE, "r", encoding="utf-8") as f:
        scripts = json.load(f)
    print(f"🔥 Starting Render of {len(scripts)} videos...")
    for video in tqdm(scripts, unit="video"):
        process_video_wrapper(video)

if __name__ == "__main__":
    main()
