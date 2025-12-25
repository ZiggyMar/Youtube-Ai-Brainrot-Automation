import json
import os

def check_assets():
    # Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, 'video_scripts.json')
    assets_dir = os.path.join(base_dir, 'assets')
    
    # Character name mapping for specific capitalization
    char_mapping = {
        'spongebob': 'SpongeBob',
        'patrick': 'Patrick',
        'squidward': 'Squidward',
        'plankton': 'Plankton',
        'mr_krabs': 'Mr. Krabs', # Assuming this might appear
        'sandy': 'Sandy'
    }

    # Load JSON
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Could not find {json_path}")
        return
    except json.JSONDecodeError:
        print(f"❌ Error: Could not decode {json_path}")
        return

    print(f"🔍 Auditing assets based on {json_path}...\n")

    missing_count = 0
    found_count = 0

    # 1. Audit Character Images
    print("--- Character Images ---")
    
    # Set to track checked paths to avoid duplicate output
    checked_paths = set()

    for video in data:
        video_id = video.get('video_id', '?')
        for segment in video.get('segments', []):
            visuals = segment.get('visuals', {})
            char_filename = visuals.get('character')
            
            if not char_filename:
                continue

            # Parse filename
            # Expected format: speaker_emotion.png
            # Split by first underscore only? Or all? 
            # User said: "Split the filename by _. The first part is the Speaker, the second is the File."
            # Example: spongebob_gangster.png -> ['spongebob', 'gangster.png']
            
            parts = char_filename.split('_', 1)
            if len(parts) < 2:
                print(f"⚠️  Warning: Invalid filename format '{char_filename}' in Video {video_id}")
                continue
                
            speaker_key = parts[0].lower()
            file_part = parts[1]
            
            # Determine directory name
            speaker_dir_name = char_mapping.get(speaker_key, speaker_key.title())
            
            # Construct full path
            # assets/characters/Speaker/File
            target_path = os.path.join(assets_dir, 'characters', speaker_dir_name, file_part)
            
            if target_path in checked_paths:
                continue
            checked_paths.add(target_path)

            # Check existence
            if os.path.exists(target_path):
                print(f"✅ Found: {speaker_dir_name}/{file_part}")
                found_count += 1
            else:
                print(f"❌ MISSING: {speaker_dir_name}/{file_part}")
                # print(f"   (Expected at: {target_path})")
                missing_count += 1

    print(f"\nCharacter Audit Complete: {found_count} found, {missing_count} missing.\n")

    # 2. Check Backgrounds and Music
    print("--- General Assets Check ---")
    
    # Check Backgrounds
    bg_dir = os.path.join(assets_dir, 'backgrounds')
    if os.path.isdir(bg_dir) and len(os.listdir(bg_dir)) > 0:
        print(f"✅ Backgrounds directory is valid ({len(os.listdir(bg_dir))} files).")
    else:
        print("❌ MISSING or EMPTY: /assets/backgrounds/")

    # Check Music
    music_dir = os.path.join(assets_dir, 'music')
    if os.path.isdir(music_dir) and len(os.listdir(music_dir)) > 0:
        print(f"✅ Music directory is valid ({len(os.listdir(music_dir))} files).")
    else:
        print("❌ MISSING or EMPTY: /assets/music/")

if __name__ == "__main__":
    check_assets()
