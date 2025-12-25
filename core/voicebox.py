import json
import os
import asyncio
import edge_tts
import torch
from pydub import AudioSegment, silence
from rvc_python.infer import RVCInference

# Monkeypatch torch.load to avoid weights_only errors
_original_load = torch.load
def safe_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = safe_load

# Configuration
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

AUDIO_CACHE_DIR = os.path.join(PROJECT_ROOT, "audio_cache")
RVC_MODELS_DIR = os.path.join(PROJECT_ROOT, "rvc_models")
SCRIPTS_FILE = os.path.join(DATA_DIR, "video_scripts.json")

# Ensure ffmpeg is in PATH
FFMPEG_DIR = os.path.join(PROJECT_ROOT, "tools", "ffmpeg")
os.environ["PATH"] += os.pathsep + FFMPEG_DIR

# Voice Mapping
VOICE_MAPPING = {
    "SpongeBob": {
        "voice": "en-US-GuyNeural",
        "rate": "+20%",
        "pitch": "+30Hz",
        "model": "spongebob"
    },
    "Patrick": {
        "voice": "en-US-RogerNeural",
        "rate": "+10%",
        "pitch": "-20Hz",
        "model": "patrick"
    },
    "Squidward": {
        "voice": "en-US-EricNeural",
        "rate": "+10%",
        "pitch": "-10Hz",
        "model": "squidward"
    },
    "Plankton": {
        "voice": "en-US-ChristopherNeural",
        "rate": "+15%",
        "pitch": "+10Hz",
        "model": "plankton"
    },
    "MrKrabs": {
        "voice": "en-US-BrianNeural",
        "rate": "+15%",
        "pitch": "-5Hz",
        "model": "mrkrabs"
    }
}

def clean_text(text):
    """Replaces abbreviations like Q1, Q2 with full words."""
    replacements = {
        "Q1": "Question One",
        "Q2": "Question Two",
        "Q3": "Question Three"
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text

async def generate_base_audio(text, voice, rate, pitch, output_path):
    """Generates base audio using edge-tts."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)

def smart_trim(audio_path, output_path, silence_thresh=-40, keep_silence_ms=60):
    """Trims leading and trailing silence but keeps a small buffer."""
    try:
        audio = AudioSegment.from_file(audio_path)
        
        start_trim = silence.detect_leading_silence(audio, silence_threshold=silence_thresh)
        end_trim = silence.detect_leading_silence(audio.reverse(), silence_threshold=silence_thresh)
        
        duration = len(audio)
        new_start = max(0, start_trim - keep_silence_ms)
        new_end = min(duration, duration - end_trim + keep_silence_ms)
        
        trimmed_audio = audio[new_start:new_end]
        trimmed_audio.export(output_path, format="wav")
        
    except Exception as e:
        print(f"Error trimming audio {audio_path}: {e}")
        if audio_path != output_path:
            import shutil
            shutil.copy(audio_path, output_path)

def convert_audio(input_path, output_path, model_name):
    """Converts audio using RVC."""
    model_path = os.path.join(RVC_MODELS_DIR, model_name, f"{model_name}.pth")
    index_path = os.path.join(RVC_MODELS_DIR, model_name, f"{model_name}.index")

    if not os.path.exists(model_path):
        print(f"Warning: Model not found at {model_path}. Skipping conversion.")
        import shutil
        shutil.copy(input_path, output_path)
        return

    rvc = RVCInference(device="cuda:0" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu")
    
    try:
        rvc.load_model(model_path, index_path=index_path if os.path.exists(index_path) else "")
        rvc.set_params(
            f0_method="rmvpe",
            f0_up_key=0,
            index_rate=0.75,
            filter_radius=3,
            resample_sr=0,
            rms_mix_rate=0.25,
            protect=0.33
        )
        rvc.infer_file(input_path, output_path)
    except Exception as e:
        print(f"Error converting audio: {e}")
        import shutil
        shutil.copy(input_path, output_path)

async def process_scripts():
    os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)

    # CLEAR CACHE to prevent mismatched audio/subtitles from previous runs
    print(f"🧹 Clearing audio cache in {AUDIO_CACHE_DIR}...")
    for f in os.listdir(AUDIO_CACHE_DIR):
        file_path = os.path.join(AUDIO_CACHE_DIR, f)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")

    if not os.path.exists(SCRIPTS_FILE):
        print(f"❌ Error: {SCRIPTS_FILE} not found.")
        return

    with open(SCRIPTS_FILE, 'r', encoding='utf-8') as f:
        scripts = json.load(f)
    
    print(f"Found {len(scripts)} videos in {SCRIPTS_FILE}.")

    for video in scripts:
        video_id = video.get("video_id")
        print(f"Processing Video {video_id}...")
        
        # Use enumerate to get segment_id (1-based)
        for i, segment in enumerate(video.get("segments", []), start=1):
            segment_id = i
            
            # Check visuals.show_timer
            visuals = segment.get("visuals", {})
            if visuals.get("show_timer") is True:
                print(f"  - Skipping Segment {segment_id} (Timer)")
                continue

            # Get text and speaker (Top level in new JSON)
            text = segment.get("text")
            speaker = segment.get("speaker")
            
            # Fallback for old JSON structure if needed
            if not text and "audio" in segment:
                text = segment["audio"].get("text")
                speaker = segment["audio"].get("speaker")

            if not text:
                print(f"  - Skipping Segment {segment_id}: Empty text.")
                continue
                
            if not speaker:
                print(f"  - Skipping Segment {segment_id}: Missing speaker.")
                continue

            # Clean text
            text = clean_text(text)
            
            # Get voice config
            config = VOICE_MAPPING.get(speaker)
            if not config:
                print(f"  - Warning: No configuration for speaker {speaker}. Skipping.")
                continue

            # Define Filenames
            base_filename = f"temp_base_v{video_id}_s{segment_id}.mp3"
            rvc_filename = f"temp_rvc_v{video_id}_s{segment_id}.wav"
            final_filename = f"v{video_id}_s{segment_id}_{speaker}.wav"
            
            base_path = os.path.join(AUDIO_CACHE_DIR, base_filename)
            rvc_path = os.path.join(AUDIO_CACHE_DIR, rvc_filename)
            final_path = os.path.join(AUDIO_CACHE_DIR, final_filename)

            if os.path.exists(final_path):
                print(f"  - Segment {segment_id} ({speaker}): Audio already exists.")
                continue

            print(f"  - Generating Segment {segment_id} ({speaker}): {text[:30]}...")

            # Generate Base Audio
            await generate_base_audio(text, config["voice"], config["rate"], config["pitch"], base_path)

            # Convert Audio
            convert_audio(base_path, rvc_path, config["model"])

            # Smart Trim
            smart_trim(rvc_path, final_path, silence_thresh=-40, keep_silence_ms=60)

            # Cleanup
            if os.path.exists(base_path):
                os.remove(base_path)
            if os.path.exists(rvc_path):
                os.remove(rvc_path)

    print("✅ All audio generation complete.")

if __name__ == "__main__":
    asyncio.run(process_scripts())
