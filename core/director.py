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
    
    print(f"🎬 Generating 5 scripts using gemini-flash-latest...")

    prompt_text = f"""
    You are a creative director for viral 'Shorts' trivia game videos.
    Generate 5 NEW scripts in a list.

    THEME: SpongeBob SquarePants.
    GAME TYPE: 'Avoid Saying the Same Thing' OR 'Say the Same Thing' (Mix them up).

    CHARACTERS:
    - Host: SpongeBob (Enthusiastic/Strict) or Squidward (Grumpy/Arrogant).
    - Sidekick: Patrick (Goofy/Sympathetic).
    - Guest: Mr. Krabs (Greedy) or Plankton (Scheming).

    SCRIPT STRUCTURE (STRICTLY FOLLOW THIS FLOW):
    1. The Hook (0:00-0:05): Host eliminates viewers based on a common physical state (e.g., breathing, sitting, holding a phone). Shock value.
    2. The Save (0:05-0:10): Sidekick complains it's unfair. Host grants a "Second Chance" ONLY if viewer Subscribes immediately.
    3. Round 1 (General Knowledge) (0:10-0:20):
       - Host/Sidekick asks a BROAD question (e.g., Name a fruit).
       - [TIMER SEGMENT]
       - Host reveals the most common answer (The Trap).
    4. Engagement Check (0:20-0:30): Host tells survivors to "Like the video" to lock in their win.
    5. Round 2 (Show Trivia) (0:30-0:50):
       - Guest asks a question related to the SpongeBob universe (Lore).
       - [TIMER SEGMENT]
       - Guest reveals the answer.
    6. The Final Trap (End):
       - Host asks a binary choice (A or B).
       - One choice wins, the other loses.
       - "Comment your streak!" or "Tell me why you picked A".

    STRICT ASSET LOGIC:
    - If speaker is 'SpongeBob', visuals.character MUST contain 'SpongeBob' (e.g., 'SpongeBob_Happy.png').
    - If speaker is 'Patrick', visuals.character MUST contain 'Patrick'.
    - If speaker is 'Squidward', visuals.character MUST contain 'Squidward'.
    - If speaker is 'Plankton', visuals.character MUST contain 'Plankton'.
    - If speaker is 'MrKrabs', visuals.character MUST contain 'MrKrabs'.

    SUBTITLE COLORS:
    - SpongeBob: "Yellow"
    - Patrick: "Pink"
    - Squidward: "Cyan"
    - Plankton: "Green"
    - MrKrabs: "Red"

    JSON OUTPUT FORMAT:
    [
      {{
        "video_id": 1,
        "segments": [
          {{
            "text": "If you are breathing right now, you are OUT!",
            "speaker": "SpongeBob",
            "visuals": {{
              "character": "SpongeBob_Angry.png",
              "subtitle_color": "Yellow",
              "list_highlight": "1. EASY",
              "show_timer": false,
              "answer_reveal": null
            }}
          }},
          {{
            "text": "If you said Froot Loops, you are out!",
            "speaker": "SpongeBob",
            "visuals": {{
              "character": "SpongeBob_Laugh.png",
              "subtitle_color": "Yellow",
              "list_highlight": "1. EASY",
              "show_timer": false,
              "answer_reveal": "FROOT LOOPS"
            }}
          }},
          ...
        ]
      }}
    ]

    IMPORTANT:
    - Insert a segment with `visuals.show_timer=true` (and speaker="Timer", text="...") between the Question and the Answer for Round 1 and Round 2.
    - For ANSWER segments (where the host reveals the trap), set `visuals.answer_reveal` to the specific item (e.g., "APPLE", "FROOT LOOPS"). Otherwise set it to null.
    - Use Gen Alpha slang (rizz, cooked, sigma, ohio) naturally but lightly.
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