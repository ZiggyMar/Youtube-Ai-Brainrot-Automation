import os
import json
import requests
import sys
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Configuration
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# API Keys from Environment
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

OUTPUT_FILE = os.path.join(DATA_DIR, "video_scripts.json")

PROMPT_TEXT = """
You are a creative director for viral 'Shorts' trivia game videos.
Generate 5 NEW scripts in a list.

THEME: SpongeBob SquarePants.
GAME TYPE: 'Avoid Saying the Same Thing' OR 'Say the Same Thing' (Mix them up).
VARIETY RULE: Do NOT repeat the same slang (like 'OHIO', 'SKIBIDI', 'RIZZ') or catchphrases across the 5 scripts. Each script must feel unique and fresh.

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
    {
    "video_id": 1,
    "segments": [
        {
        "text": "If you are breathing right now, you are OUT!",
        "speaker": "SpongeBob",
        "visuals": {
            "character": "SpongeBob_Angry.png",
            "subtitle_color": "Yellow",
            "list_highlight": "1. EASY",
            "show_timer": false,
            "answer_reveal": null
        }
        },
        {
        "text": "If you said Froot Loops, you are out!",
        "speaker": "SpongeBob",
        "visuals": {
            "character": "SpongeBob_Laugh.png",
            "subtitle_color": "Yellow",
            "list_highlight": "1. EASY",
            "show_timer": false,
            "answer_reveal": "FROOT LOOPS"
        }
        }
    ]
    }
]

IMPORTANT:
- Insert a segment with `visuals.show_timer=true` (and speaker="Timer", text="...") between the Question and the Answer for Round 1 and Round 2.
- For ANSWER segments (where the host reveals the trap), set `visuals.answer_reveal` to the specific item (e.g., "APPLE", "FROOT LOOPS"). Otherwise set it to null.
- Use Gen Alpha slang (rizz, cooked, sigma, ohio) naturally but lightly.
- RETURN ONLY RAW JSON. NO MARKDOWN.
"""

def save_scripts(data):
    try:
        # Assign IDs 1 to 5
        for i, script in enumerate(data):
            script["video_id"] = i + 1
            
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Success! Saved to {OUTPUT_FILE}")
        return True
    except Exception as e:
        print(f"❌ Error saving scripts: {e}")
        return False

def try_gemini():
    print("🔹 Attempting Gemini...")
    if not GEMINI_API_KEY: return False
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=PROMPT_TEXT,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return save_scripts(json.loads(response.text))
    except Exception as e:
        print(f"⚠️ Gemini Failed: {e}")
        return False

def try_groq():
    print("🔹 Attempting Groq...")
    if not GROQ_API_KEY: return False
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "messages": [{"role": "user", "content": PROMPT_TEXT}],
            "model": "llama-3.3-70b-versatile",
            "response_format": {"type": "json_object"}
        }
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        return save_scripts(json.loads(content))
    except Exception as e:
        print(f"⚠️ Groq Failed: {e}")
        return False

def try_mistral():
    print("🔹 Attempting Mistral...")
    if not MISTRAL_API_KEY: return False
    try:
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "messages": [{"role": "user", "content": PROMPT_TEXT}],
            "model": "mistral-small-latest",
            "response_format": {"type": "json_object"}
        }
        response = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        return save_scripts(json.loads(content))
    except Exception as e:
        print(f"⚠️ Mistral Failed: {e}")
        return False

def try_openrouter():
    print("🔹 Attempting OpenRouter...")
    if not OPENROUTER_API_KEY: return False
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "messages": [{"role": "user", "content": PROMPT_TEXT}],
            "model": "meta-llama/llama-3-8b-instruct:free",
        }
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        
        # Clean markdown if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        return save_scripts(json.loads(content))
    except Exception as e:
        print(f"⚠️ OpenRouter Failed: {e}")
        return False

def generate_scripts():
    print("🎬 Starting Script Generation with Fallbacks...")
    
    if try_gemini(): return
    print("⏳ Waiting 2s before fallback...")
    time.sleep(2)
    
    if try_groq(): return
    print("⏳ Waiting 2s before fallback...")
    time.sleep(2)
    
    if try_mistral(): return
    print("⏳ Waiting 2s before fallback...")
    time.sleep(2)
    
    if try_openrouter(): return
    
    print("❌ CRITICAL: All AI providers failed.")
    sys.exit(1)

if __name__ == "__main__":
    generate_scripts()