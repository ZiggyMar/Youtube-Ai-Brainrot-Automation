import json
import os
import re
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

# Ensure ffmpeg is in PATH (bundled on Windows; system ffmpeg on Linux/server)
FFMPEG_DIR = os.path.join(PROJECT_ROOT, "tools", "ffmpeg")
if os.path.isdir(FFMPEG_DIR):
    os.environ["PATH"] += os.pathsep + FFMPEG_DIR

# Voice Mapping
VOICE_MAPPING = {
    "SpongeBob": {
        "voice": "en-US-GuyNeural",
        "rate": "+27%",
        "pitch": "+20Hz",
        "model": "spongebob"
    },
    "Patrick": {
        "voice": "en-US-RogerNeural",
        "rate": "+25%",
        "pitch": "-5Hz",
        "model": "patrick"
    },
    "Squidward": {
        "voice": "en-US-EricNeural",
        "rate": "+27%",
        "pitch": "-10Hz",
        "model": "squidward"
    },
    "Plankton": {
        "voice": "en-US-ChristopherNeural",
        "rate": "+17%",
        "pitch": "+10Hz",
        "model": "plankton"
    },
    "MrKrabs": {
        "voice": "en-US-BrianNeural",
        "rate": "+17%",
        "pitch": "-5Hz",
        "model": "mrkrabs"
    },
    # Generic / Fallback Voices
    "Reporter": { "voice": "en-US-SteffanNeural", "rate": "+10%", "pitch": "+0Hz", "model": None },
    "Voice": { "voice": "en-US-JennyNeural", "rate": "+10%", "pitch": "+0Hz", "model": None },
    "Director": { "voice": "en-US-DavisNeural", "rate": "+10%", "pitch": "-5Hz", "model": None },
    "Sidekick": { "voice": "en-US-GuyNeural", "rate": "+10%", "pitch": "+0Hz", "model": None },
    "Narrator": { "voice": "en-US-ChristopherNeural", "rate": "+10%", "pitch": "-5Hz", "model": None },
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

async def generate_base_audio(text, voice, rate, pitch, output_path, volume="+0%"):
    """Generates base audio using edge-tts. Handles silent/empty text gracefully."""
    # Sanitize text
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')

    # Check if text is empty or just punctuation (like "...")
    clean_text_content = text.strip().replace(".", "").replace("!", "").replace("?", "").replace(" ", "")

    if not clean_text_content:
        print(f"   ℹ️ Text '{text}' is silent. Generating 1s silence.")
        # Generate 1 second of silence
        silence_segment = AudioSegment.silent(duration=1000)
        silence_segment.export(output_path, format="mp3")
        return

    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
        await communicate.save(output_path)
    except Exception as e:
        print(f"❌ Error generating TTS for '{text}': {e}. Generating silence fallback.")
        silence_segment = AudioSegment.silent(duration=1000)
        silence_segment.export(output_path, format="mp3")

def remove_internal_silence(audio_path, output_path, min_silence_len=200, silence_thresh=-45, keep_silence=50):
    """Aggressively removes silence from within the audio to cut breathing pauses."""
    try:
        audio = AudioSegment.from_file(audio_path)
        
        # Split on silence
        chunks = silence.split_on_silence(
            audio,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
            keep_silence=keep_silence
        )
        
        if chunks:
            combined = chunks[0]
            for chunk in chunks[1:]:
                combined += chunk
            combined.export(output_path, format="wav")
        else:
            # If no silence found or split failed, just export original (trimmed edges)
            # But let's at least do leading/trailing trim if split didn't happen
            start_trim = silence.detect_leading_silence(audio, silence_threshold=silence_thresh)
            end_trim = silence.detect_leading_silence(audio.reverse(), silence_threshold=silence_thresh)
            duration = len(audio)
            new_start = max(0, start_trim - keep_silence)
            new_end = min(duration, duration - end_trim + keep_silence)
            audio[new_start:new_end].export(output_path, format="wav")
            
    except Exception as e:
        print(f"Error processing silence for {audio_path}: {e}")
        if audio_path != output_path:
            import shutil
            shutil.copy(audio_path, output_path)

def run_rvc_batch(speaker, tasks):
    """Runs RVC inference for a batch of files using a single model load."""
    if not tasks: return
    
    print(f"🎤 Loading RVC Model for {speaker}...")
    config = VOICE_MAPPING.get(speaker, VOICE_MAPPING["Reporter"]) # Fallback for config in batch
    model_name = config.get("model")
    
    if not model_name:
        print(f"ℹ️ No RVC model for {speaker}. Using base TTS.")
        for task in tasks:
            import shutil
            shutil.copy(task['base_path'], task['rvc_path'])
        return

    # Resolve the model folder case-insensitively (Linux is case-sensitive).
    model_dir = os.path.join(RVC_MODELS_DIR, model_name)
    if not os.path.isdir(model_dir) and os.path.isdir(RVC_MODELS_DIR):
        for d in os.listdir(RVC_MODELS_DIR):
            if d.lower() == model_name.lower():
                model_dir = os.path.join(RVC_MODELS_DIR, d)
                break
    model_path = os.path.join(model_dir, f"{model_name}.pth")
    index_path = os.path.join(model_dir, f"{model_name}.index")

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
        # NOTE: rvc-python's valid keys are f0method / f0up_key (NO underscores). The old code
        # passed f0_method / f0_up_key, which were silently ignored -> RVC fell back to the
        # default "harvest" pitch extractor (warbly/robotic). "rmvpe" is far cleaner.
        rvc.set_params(
            f0method="rmvpe",
            f0up_key=0,
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
    tasks_by_speaker = {} # Initialize empty, fill dynamically
    
    print("📋 Analyzing scripts...")
    for video in scripts:
        video_id = video.get("video_id")
        for i, segment in enumerate(video.get("script", []), start=1):
            segment_id = i
            
            visuals = segment.get("visuals", {})
            is_timer = visuals.get("show_timer") is True

            text = segment.get("text")
            speaker = segment.get("speaker")

            if not text and "audio" in segment:
                text = segment["audio"].get("text")
                speaker = segment["audio"].get("speaker")

            if not text or not speaker: continue

            # Skip ONLY pure silent timers (speaker "Timer" or empty/ellipsis text).
            # A timer segment with a real character + line (e.g. "Don't say SpongeBob!",
            # "I bet they'll say X") DOES get a voice — it plays while the clock runs.
            clean_check = str(text).strip().replace(".", "").replace(" ", "")
            if is_timer and (speaker == "Timer" or not clean_check):
                continue
            
            config = VOICE_MAPPING.get(speaker)
            if not config:
                print(f"⚠️ Unknown speaker '{speaker}'. Using fallback (Reporter).")
                speaker = "Reporter"
                config = VOICE_MAPPING["Reporter"]
            
            # Paths
            base_filename = f"temp_base_v{video_id}_s{segment_id}.mp3"
            rvc_filename = f"temp_rvc_v{video_id}_s{segment_id}.wav"
            final_filename = f"v{video_id}_s{segment_id}_{speaker}.wav" # Note: Filename might change if speaker changed
            # Actually, we should keep the original speaker name in filename to match video_factory?
            # video_factory looks for f"v{video_id}_s{i}_{speaker}.wav" using the speaker FROM THE SCRIPT.
            # So if we change 'speaker' variable here, we must ensure the filename matches what video_factory expects.
            # video_factory reads the script. The script has "Reporter".
            # So we must save as "Reporter".
            # But if "Reporter" is not in VOICE_MAPPING, we use the config of the fallback.
            
            # Let's revert the speaker variable change and just use the config.
            # But wait, tasks_by_speaker uses 'speaker' as key.
            # If we use "Reporter" config but keep "Unknown" speaker name, run_rvc_batch needs to handle it.
            
            # Better approach:
            # If unknown, map it to a known fallback key in tasks_by_speaker, 
            # BUT keep the filename as the original speaker so video_factory finds it.
            
            original_speaker = speaker
            if speaker not in VOICE_MAPPING:
                 # Use Reporter config
                 config = VOICE_MAPPING["Reporter"]
            
            # Paths
            base_filename = f"temp_base_v{video_id}_s{segment_id}.mp3"
            rvc_filename = f"temp_rvc_v{video_id}_s{segment_id}.wav"
            final_filename = f"v{video_id}_s{segment_id}_{original_speaker}.wav" # Use original name!
            json_filename = f"v{video_id}_s{segment_id}_{original_speaker}.json"
            
            base_path = os.path.join(AUDIO_CACHE_DIR, base_filename)
            rvc_path = os.path.join(AUDIO_CACHE_DIR, rvc_filename)
            final_path = os.path.join(AUDIO_CACHE_DIR, final_filename)
            json_path = os.path.join(AUDIO_CACHE_DIR, json_filename)
            
            # Skip if done
            if os.path.exists(final_path) and os.path.exists(json_path):
                continue
                
            # SCREAM EMPHASIS: if the FIRST word is a drawn-out "WAAAIT!" scroll-stopper,
            # render that line louder, higher and a touch slower so the lead character
            # actually YELLS it instead of saying it in a flat tone like the rest.
            rate = config["rate"]
            pitch = config["pitch"]
            volume = "+0%"
            first_word = text.strip().split()[0] if text.strip().split() else ""
            first_word_letters = re.sub(r"[^a-zA-Z]", "", first_word)
            is_scream = re.sub(r"(.)\1+", r"\1", first_word_letters).upper() == "WAIT"
            if is_scream:
                rate = "-8%"          # stretch the yell out
                pitch = "+45Hz"       # high, panicked, cartoonish
                volume = "+40%"       # LOUD

            task = {
                "text": clean_text(text),
                "speaker": original_speaker, # Used for filename/logging
                "config": config,
                "rate": rate,
                "pitch": pitch,
                "volume": volume,
                "base_path": base_path,
                "rvc_path": rvc_path,
                "final_path": final_path,
                "json_path": json_path,
                "id": f"v{video_id}_s{segment_id}"
            }
            
            all_tasks.append(task)
            
            # Group by the CONFIG speaker (or just use the original speaker name if we added it to mapping)
            # Since I added "Reporter" etc to VOICE_MAPPING, they ARE known now.
            # The fallback is only for truly unknown ones.
            
            # If it was truly unknown (e.g. "Alien"), we use "Reporter" config.
            # We should group it under "Reporter" for RVC batching (if Reporter had RVC).
            # But Reporter has no RVC.
            
            # Let's just use the original speaker as the key, and ensure run_rvc_batch handles it.
            if original_speaker not in tasks_by_speaker:
                tasks_by_speaker[original_speaker] = []
            tasks_by_speaker[original_speaker].append(task)

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
            task["rate"],
            task["pitch"],
            task["base_path"],
            task["volume"]
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
        # Trim and Remove Internal Silence
        remove_internal_silence(task['rvc_path'], task['final_path'])
        
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
