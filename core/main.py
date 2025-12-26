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
    Runs a python script and waits for it to finish.
    """
    print(f"\n{'='*50}")
    print(f"=== {stage_title} ===")
    print(f"{'='*50}\n")
    
    script_path = os.path.join(CORE_DIR, script_name)
    
    if not os.path.exists(script_path):
        print(f"❌ Error: Script not found: {script_name}")
        sys.exit(1)

    try:
        # Run the script and wait for it to complete
        result = subprocess.run([sys.executable, script_path], check=True)
        if result.returncode != 0:
            print(f"❌ {script_name} failed with exit code {result.returncode}")
            sys.exit(result.returncode)
        print(f"✅ {stage_title} Complete.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running {script_name}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

def archive_completed_videos():
    """
    Moves completed video scripts from video_scripts.json to archive_scripts.json
    based on the existence of final_video_{id}.mp4 in the output directory.
    """
    print(f"\n{'='*50}")
    print(f"=== STAGE 4: ARCHIVING & CLEANUP ===")
    print(f"{'='*50}\n")

    # 1. Identify Completed Video IDs
    if not os.path.exists(OUTPUT_DIR):
        print("⚠️ Output directory does not exist. Nothing to archive.")
        return

    completed_ids = set()
    for filename in os.listdir(OUTPUT_DIR):
        if filename.startswith("video_") and filename.endswith("_production.mp4"):
            # Extract ID: video_1_production.mp4 -> 1
            try:
                vid_id_str = filename.replace("video_", "").replace("_production.mp4", "")
                completed_ids.add(int(vid_id_str))
            except ValueError:
                continue
    
    if not completed_ids:
        print("ℹ️ No completed videos found in output/.")
        return

    print(f"🔍 Found {len(completed_ids)} completed videos: {sorted(list(completed_ids))}")

    # 2. Load Current Scripts
    if not os.path.exists(SCRIPTS_FILE):
        print(f"⚠️ {SCRIPTS_FILE} not found. Skipping archive.")
        return

    try:
        with open(SCRIPTS_FILE, 'r', encoding='utf-8') as f:
            current_scripts = json.load(f)
    except json.JSONDecodeError:
        print(f"❌ Error decoding {SCRIPTS_FILE}.")
        return

    # 3. Load or Initialize Archive
    archive_data = []
    if os.path.exists(ARCHIVE_FILE):
        try:
            with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                archive_data = json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Error decoding {ARCHIVE_FILE}. Starting with empty archive.")

    # 4. Separate Completed vs Incomplete
    remaining_scripts = []
    moved_count = 0

    for video in current_scripts:
        vid_id = video.get('video_id')
        if vid_id in completed_ids:
            archive_data.append(video)
            moved_count += 1
            print(f"   -> Archiving Video {vid_id}...")
        else:
            remaining_scripts.append(video)

    # 5. Save Files
    if moved_count > 0:
        # Save Archive
        with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(archive_data, f, indent=2)
        print(f"✅ Saved {len(archive_data)} total videos to {os.path.basename(ARCHIVE_FILE)}")

        # Save Remaining
        with open(SCRIPTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(remaining_scripts, f, indent=2)
        print(f"✅ Updated {os.path.basename(SCRIPTS_FILE)} with {len(remaining_scripts)} remaining videos.")
    else:
        print("ℹ️ No matching scripts found to archive (IDs might not match).")

def main():
    # Number of videos to generate in sequence
    NUM_VIDEOS = 1 # Default to 1 per run as per "generate 1 video at a time" request, or maybe 5?
    # User said "so it makes video one, then video two", implying a sequence. 
    # But also "everytime the .run is called it makes a whole new script".
    # I will set it to 1 for now, as the user can just run the batch file multiple times or I can ask.
    # Actually, "so it makes video one, then video two" implies a loop in the script.
    # Let's set it to 5 to match the previous batch size but done sequentially.
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
