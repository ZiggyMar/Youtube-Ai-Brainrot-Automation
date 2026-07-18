import subprocess
import os
import json
import sys

# Configuration
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')

SCRIPTS_FILE = os.path.join(DATA_DIR, 'video_scripts.json')
ARCHIVE_FILE = os.path.join(DATA_DIR, 'archive_scripts.json')

def run_step(script_name, stage_title):
    """
    Executes a python script sequentially as part of the video pipeline.
    Raises exceptions on failure to stop the pipeline.
    """
    print(f"\n{'='*50}")
    print(f"=== {stage_title} ===")
    print(f"{'='*50}\n")
    
    script_path = os.path.join(CORE_DIR, script_name)
    
    if not os.path.exists(script_path):
        print(f"❌ Error: Script not found: {script_name}")
        raise FileNotFoundError(f"Script not found: {script_name}")

    try:
        # Run the script and wait for it to complete
        result = subprocess.run([sys.executable, script_path], check=True)
        if result.returncode != 0:
            print(f"❌ {script_name} failed with exit code {result.returncode}")
            raise RuntimeError(f"{script_name} failed with exit code {result.returncode}")
        print(f"✅ {stage_title} Complete.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running {script_name}: {e}")
        raise e
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise e

def archive_completed_videos():
    """
    Moves completed video scripts from video_scripts.json to archive_scripts.json
    based on the existence of {title}.mp4 in the output directory.
    """
    import re
    print(f"\n{'='*50}")
    print(f"=== STAGE 4: ARCHIVING & CLEANUP ===")
    print(f"{'='*50}\n")

    if not os.path.exists(SCRIPTS_FILE):
        print(f"ℹ️ No scripts file found at {SCRIPTS_FILE}")
        return

    try:
        with open(SCRIPTS_FILE, 'r', encoding='utf-8') as f:
            current_scripts = json.load(f)
    except Exception as e:
        print(f"❌ Error loading scripts: {e}")
        return

    if not current_scripts:
        print("ℹ️ No scripts to archive.")
        return

    archive_data = []
    if os.path.exists(ARCHIVE_FILE):
        try:
            with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                archive_data = json.load(f)
        except: pass

    remaining_scripts = []
    moved_count = 0

    ready_dir = os.path.join(OUTPUT_DIR, "Ready To Post")
    os.makedirs(ready_dir, exist_ok=True)

    for video in current_scripts:
        title = video.get("title", f"video_{video.get('video_id')}")
        # Sanitize title same as video_factory.py
        safe_title = re.sub(r'[<>:"/\\|?*]', '', title).strip()
        video_path = os.path.join(OUTPUT_DIR, f"{safe_title}.mp4")
        
        if os.path.exists(video_path):
            print(f"   -> Archiving Video: {safe_title}")
            archive_data.append(video)
            moved_count += 1
            
            # Move file to Ready To Post
            target_path = os.path.join(ready_dir, f"{safe_title}.mp4")
            try:
                # If target exists, add a timestamp or ID to avoid overwrite
                if os.path.exists(target_path):
                    target_path = os.path.join(ready_dir, f"{safe_title}_{video.get('video_id')}.mp4")
                os.rename(video_path, target_path)
                print(f"      ✅ Moved to {os.path.relpath(target_path, PROJECT_ROOT)}")
            except Exception as e:
                print(f"      ⚠️ Could not move file: {e}")
        else:
            remaining_scripts.append(video)

    if moved_count > 0:
        with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(archive_data, f, indent=2)
        with open(SCRIPTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(remaining_scripts, f, indent=2)
        print(f"✅ Archived {moved_count} scripts to {os.path.basename(ARCHIVE_FILE)}")
    else:
        print("ℹ️ No completed videos found in output/ to archive.")

def check_environment():
    """Validates that at least one required API key is present."""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
    
    keys = ["GEMINI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY", "OPENROUTER_API_KEY"]
    if not any(os.environ.get(k) and os.environ.get(k).strip() for k in keys):
        print("\n\u274c CRITICAL CONFIGURATION ERROR \u274c")
        print("No valid LLM API keys were found in your environment.")
        print("Please copy '.env.example' to '.env' and add at least one API key.")
        print("Example:")
        print("  cp .env.example .env")
        print("  nano .env\n")
        import sys
        sys.exit(1)

def main():
    """
    Entry point for sequential manual testing of the video pipeline.
    Generates a batch of videos back-to-back.
    """
    check_environment()
    
    # Number of videos to generate in sequence
    NUM_VIDEOS = 5

    for i in range(NUM_VIDEOS):
        print(f"\n🎬 === STARTING VIDEO GENERATION SEQUENCE {i+1}/{NUM_VIDEOS} ===")
        
        # Step 1: Always Generate New Scripts
        print("ℹ️ Generating fresh script...")
        run_step("director.py", "STAGE 1: WRITING SCRIPTS")

        # Step 2: Voicebox (Generate Audio)
        run_step("voicebox.py", "STAGE 2: GENERATING AUDIO")

        # Step 3: Video Factory (Render)
        run_step("video_factory.py", "STAGE 3: RENDERING VIDEOS")

        # Step 4: Cleanup
        archive_completed_videos()
        
        print(f"✅ Sequence {i+1} Complete.\n")

    print(f"\n{'='*50}")
    print("🎉 ALL SEQUENTIAL VIDEOS COMPLETE 🎉")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()
