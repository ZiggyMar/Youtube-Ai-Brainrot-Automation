from google import genai
from google.genai import types
import json
import os
import random
from dotenv import load_dotenv

# Configuration
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# Load environment variables from .env in project root
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# ==========================================
# API KEY
# ==========================================
MY_API_KEY = os.environ.get("GEMINI_API_KEY")

def generate_scripts():
    if not MY_API_KEY or "PASTE_YOUR" in MY_API_KEY:
        print("❌ ERROR: Invalid API Key. Please check your .env file.")
        return

    client = genai.Client(api_key=MY_API_KEY)
    file_path = os.path.join(DATA_DIR, "video_scripts.json")
    cta_path = os.path.join(DATA_DIR, "cta_master_list.json")
    
    # Load CTAs
    ctas = {}
    if os.path.exists(cta_path):
        with open(cta_path, "r", encoding="utf-8") as f:
            ctas = json.load(f)
    
    redemption_cta = random.choice(ctas.get("redemption", ["Subscribe to respawn!"]))
    lock_in_cta = random.choice(ctas.get("lock_in", ["Subscribe to lock in!"]))

    print(f"🎬 Generating 5 scripts using gemini-flash-latest...")

    prompt_text = f"""
    You are a creative director for 'Avoid Saying The Same Thing' SpongeBob-themed videos.
    Generate 5 NEW scripts in a list.
    
    STRICT CONTENT LOGIC:
    - Level 1 (Easy): Question: 'Name a [Category] (e.g., Cereal)'. Answer: 'If you said [Item IN that category], you are out.' (e.g., Froot Loops).
    - Level 2 (Medium): Question: 'Name a [Category]'. Answer: 'If you said [Item IN that category], you are out.' (Avoid saying the same thing).
    - Level 3 (Hard): Question: 'Name a [Category]'. Answer: 'If you said [Item IN that category], you are out.' (Avoid saying the same thing).
    - Level 4 (Impossible): Brainrot/Gen Alpha slang theme.
    
    STRICT ASSET LOGIC:
    - If speaker is 'SpongeBob', visuals.character MUST contain 'SpongeBob' (e.g., 'SpongeBob_Happy.png').
    - If speaker is 'Patrick', visuals.character MUST contain 'Patrick' (e.g., 'Patrick_Confused.png').
    - If speaker is 'Squidward', visuals.character MUST contain 'Squidward'.
    - If speaker is 'Plankton', visuals.character MUST contain 'Plankton'.
    - If speaker is 'MrKrabs', visuals.character MUST contain 'MrKrabs'.
    
    SUBTITLE COLORS:
    - SpongeBob: "Yellow"
    - Patrick: "Pink"
    - Squidward: "Cyan"
    - Plankton: "Green"
    - MrKrabs: "Red"
    
    STRUCTURE PER VIDEO:
    1. Intro: Speaker A. "Level 1. If you are [Common Act], you are out."
    2. CTA 1: Speaker B. "{redemption_cta}"
    3. Level 1 (Easy): Q (Speaker A) -> Timer -> A (Speaker B).
    4. Level 2 (Medium): Q (Speaker A) -> Timer -> A (Speaker B).
    5. Level 3 (Hard): Q (Speaker A) -> Timer -> A (Speaker B).
    6. Level 4 (Impossible): Q (Speaker A) -> Timer -> A (Speaker B).
    7. CTA 2: Speaker A. "{lock_in_cta}"
    8. Outro: Speaker B. "Comment your streak!"

    JSON OUTPUT FORMAT:
    [
      {{
        "video_id": 1,
        "segments": [
          {{
            "text": "Spoken words",
            "speaker": "SpongeBob",
            "visuals": {{
              "character": "SpongeBob_Mood.png",
              "subtitle_color": "Yellow",
              "list_highlight": "1. EASY",
              "show_timer": false
            }}
          }},
          ...
        ]
      }}
    ]
    
    For Timer segments: speaker="Timer", text="...", visuals.character=null, visuals.show_timer=true.
    Use Gen Alpha slang (rizz, cooked, sigma, ohio) occasionally for flavor.
    """

    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt_text,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        generated_data = json.loads(response.text)
        
        # Assign IDs 1 to 5
        for i, script in enumerate(generated_data):
            script["video_id"] = i + 1
            
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(generated_data, f, indent=2)
            
        print(f"✅ Success! Generated 5 scripts in {file_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    generate_scripts()