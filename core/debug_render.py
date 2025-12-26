import json
import os
import sys

# Add core to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import video_factory

def debug_render():
    scripts_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'video_scripts.json')
    
    with open(scripts_file, 'r', encoding='utf-8') as f:
        scripts = json.load(f)
        
    if not scripts:
        print("No scripts found.")
        return

    # Pick the first video
    video_data = scripts[0]
    print(f"Debugging rendering for Video {video_data['video_id']}")
    
    # Call generate_video directly
    video_factory.generate_video(video_data, use_gpu=False)

if __name__ == "__main__":
    debug_render()
