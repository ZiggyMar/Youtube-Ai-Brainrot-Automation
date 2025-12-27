import json
import os
import asyncio
import edge_tts
import torch
import whisper
import gc

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
        "rate": "+35%",
        "pitch": "+20Hz",
        "model": "spongebob"
    },
    "Patrick": {
        "voice": "en-US-RogerNeural",
        "rate": "+25%",
        "pitch": "-10Hz",
        "model": "patrick"
    },
    "Squidward": {
        "voice": "en-US-EricNeural",
        "rate": "+25%",
        "pitch": "-10Hz",
        "model": "squidward"
    },
    "Plankton": {
        "voice": "en-US-ChristopherNeural",
        "rate": "+25%",
        "pitch": "+10Hz",
        "model": "plankton"
    },
    "MrKrabs": {
        "voice": "en-US-BrianNeural",
        "rate": "+25%",
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

def smart_trim(audio_path, output_path, silence_thresh=-50, keep_silence_ms=50):
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

def run_rvc_batch(speaker, tasks):
    """Runs RVC inference for a batch of files using a single model load."""
    if not tasks: return
    
    print(f"🎤 Loading RVC Model for {speaker}...")
    config = VOICE_MAPPING[speaker]
    model_name = config.get("model")
    
    if not model_name:
        print(f"ℹ️ No RVC model for {speaker}. Using base TTS.")
        for task in tasks:
            import shutil
            shutil.copy(task['base_path'], task['rvc_path'])
        return

    model_path = os.path.join(RVC_MODELS_DIR, model_name, f"{model_name}.pth")
    index_path = os.path.join(RVC_MODELS_DIR, model_name, f"{model_name}.index")

    if not os.path.exists(model_path):
        print(f"⚠️ Model not found: {model_path}. Skipping RVC for {speaker}.")
        # Fallback: Copy base to rvc path
        for task in tasks:
            import shutil
            shutil.copy(task['base_path'], task['rvc_path'])
        return

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    
    # Load Model ONCE
    try:
        rvc = RVCInference(device=device)
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
        
        print(f"⚡ Converting {len(tasks)} files for {speaker}...")
        for task in tasks:
            rvc.infer_file(task['base_path'], task['rvc_path'])
            
    except Exception as e:
        print(f"❌ Error during RVC batch for {speaker}: {e}")
        # Fallback
        for task in tasks:
            if not os.path.exists(task['rvc_path']):
                import shutil
                shutil.copy(task['base_path'], task['rvc_path'])
    finally:
        # Cleanup to free VRAM
        if 'rvc' in locals():
            del rvc
        gc.collect()
        torch.cuda.empty_cache()

async def process_scripts():
    os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
    
    # Check Scripts
    if not os.path.exists(SCRIPTS_FILE):
        print(f"❌ Error: {SCRIPTS_FILE} not found.")
        return

    with open(SCRIPTS_FILE, 'r', encoding='utf-8') as f:
        scripts = json.load(f)
    
    print(f"🔥 Optimizing Workflow: Batching by Speaker to maximize GPU usage.")
    
    # 1. Collect All Tasks
    all_tasks = []
    tasks_by_speaker = {k: [] for k in VOICE_MAPPING.keys()}
    
    print("📋 Analyzing scripts...")
    for video in scripts:
        video_id = video.get("video_id")
        for i, segment in enumerate(video.get("script", []), start=1):
            segment_id = i
            
            # Skip Timer
            visuals = segment.get("visuals", {})
            if visuals.get("show_timer") is True: continue

            text = segment.get("text")
            speaker = segment.get("speaker")
            
            if not text and "audio" in segment:
                text = segment["audio"].get("text")
                speaker = segment["audio"].get("speaker")

            if not text or not speaker: continue
            
            config = VOICE_MAPPING.get(speaker)
            if not config: continue
            
            # Paths
            base_filename = f"temp_base_v{video_id}_s{segment_id}.mp3"
            rvc_filename = f"temp_rvc_v{video_id}_s{segment_id}.wav"
            final_filename = f"v{video_id}_s{segment_id}_{speaker}.wav"
            json_filename = f"v{video_id}_s{segment_id}_{speaker}.json"
            
            base_path = os.path.join(AUDIO_CACHE_DIR, base_filename)
            rvc_path = os.path.join(AUDIO_CACHE_DIR, rvc_filename)
            final_path = os.path.join(AUDIO_CACHE_DIR, final_filename)
            json_path = os.path.join(AUDIO_CACHE_DIR, json_filename)
            
            # Skip if done
            if os.path.exists(final_path) and os.path.exists(json_path):
                continue
                
            task = {
                "text": clean_text(text),
                "speaker": speaker,
                "config": config,
                "base_path": base_path,
                "rvc_path": rvc_path,
                "final_path": final_path,
                "json_path": json_path,
                "id": f"v{video_id}_s{segment_id}"
            }
            
            all_tasks.append(task)
            tasks_by_speaker[speaker].append(task)

    if not all_tasks:
        print("✅ All audio is already up to date.")
        return

    print(f"🚀 Processing {len(all_tasks)} audio segments...")

    # 2. Generate All Base Audio (Parallel)
    print("🗣️ Generating Base TTS (Parallel)...")
    tts_coroutines = []
    for task in all_tasks:
        tts_coroutines.append(generate_base_audio(
            task["text"], 
            task["config"]["voice"], 
            task["config"]["rate"], 
            task["config"]["pitch"], 
            task["base_path"]
        ))
    
    if tts_coroutines:
        await asyncio.gather(*tts_coroutines)
    print("✅ TTS Generation Complete.")

    # 3. Run RVC Batches (Sequential by Speaker, but Fast)
    print("🤖 Starting RVC Batch Processing...")
    for speaker, tasks in tasks_by_speaker.items():
        if tasks:
            run_rvc_batch(speaker, tasks)
    print("✅ RVC Processing Complete.")

    # 4. Whisper Transcribe & Trim (Sequential or Parallel)
    print("📝 Transcribing and Trimming...")
    try:
        whisper_model = whisper.load_model("base")
    except Exception as e:
        print(f"❌ Failed to load Whisper: {e}")
        return

    for task in all_tasks:
        # Trim
        smart_trim(task['rvc_path'], task['final_path'])
        
        # Transcribe
        result = whisper_model.transcribe(task['final_path'], word_timestamps=True)
        
        word_data = []
        for segment in result["segments"]:
            for word in segment["words"]:
                word_data.append({
                    "word": word["word"].strip(),
                    "start": word["start"],
                    "end": word["end"]
                })
        
        with open(task['json_path'], "w", encoding="utf-8") as f:
            json.dump(word_data, f, indent=2)
            
        # Cleanup temps
        if os.path.exists(task['base_path']): os.remove(task['base_path'])
        if os.path.exists(task['rvc_path']): os.remove(task['rvc_path'])

    print("🎉 All audio processing complete!")

if __name__ == "__main__":
    asyncio.run(process_scripts())
