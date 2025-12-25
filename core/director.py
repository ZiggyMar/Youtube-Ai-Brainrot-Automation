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
GAME TYPE: 'Avoid Saying the Same Thing'.

STRICT RULES:
1. NO FILLER: Do not write questions like "Name a vegetable" unless it is the actual game round.
2. NO STAGE DIRECTIONS: Do not write (Laughs), (Cut to black), etc. Only dialogue.
3. NO SLANG MISUSE: Do not use "Ohio", "Sigma", etc. unless it makes perfect sense. Keep it simple.
4. STRICT FLOW: Question -> Timer -> Answer. Never leave a question unanswered.
5. ONE CTA VIDEO: The script should naturally lead to a Subscribe CTA early on.

CHARACTERS:
- SpongeBob (Excited, slightly strict host)
- Patrick (Complaining, tries to help the viewer)
- Squidward (Annoyed, arrogant)

SCRIPT STRUCTURE (STRICTLY FOLLOW THIS FLOW):
1. The Hook: SpongeBob sets an impossible elimination trap (e.g., "If you are breathing, you are OUT!").
2. The Redemption: Patrick complains it's too hard. Tells viewers to "Subscribe for a second chance/revive".
3. Round 1: SpongeBob asks Question 1 (Broad category).
   - [TIMER SEGMENT]
   - SpongeBob reveals Answer 1. "If you said [Answer], you're out!"
4. Round 2: Squidward asks Question 2.
   - [TIMER SEGMENT]
   - Squidward reveals Answer 2. "I chose [Answer]. If you matched me, leave."
5. Final Round: Patrick asks to pick between two options (e.g., "Krusty Krab or Chum Bucket").
   - Patrick reveals his choice. "I picked [Option]. Comment if you won!"

JSON OUTPUT FORMAT:
[
  {
    "video_id": 1,
    "segments": [
      {
        "text": "If you are wearing socks right now, you are ELIMINATED!",
        "speaker": "SpongeBob",
        "visuals": {
          "character": "SpongeBob",
          "subtitle_color": "Yellow",
          "list_highlight": "1. EASY",
          "show_timer": false,
          "answer_reveal": null
        }
      },
      {
        "text": "That is way too hard! Subscribe right now for a revive!",
        "speaker": "Patrick",
        "visuals": {
          "character": "Patrick",
          "subtitle_color": "Pink",
          "list_highlight": "1. EASY",
          "show_timer": false,
          "answer_reveal": null
        }
      },
      {
        "text": "Fine. Round 1. Name a fruit.",
        "speaker": "SpongeBob",
        "visuals": {
          "character": "SpongeBob",
          "subtitle_color": "Yellow",
          "list_highlight": "1. EASY",
          "show_timer": false,
          "answer_reveal": null
        }
      },
      {
        "text": "...",
        "speaker": "Timer",
        "visuals": {
          "character": null,
          "subtitle_color": "White",
          "list_highlight": "1. EASY",
          "show_timer": true,
          "answer_reveal": null
        }
      },
      {
        "text": "I picked Apple. If you said Apple, you are out!",
        "speaker": "SpongeBob",
        "visuals": {
          "character": "SpongeBob",
          "subtitle_color": "Yellow",
          "list_highlight": "1. EASY",
          "show_timer": false,
          "answer_reveal": "APPLE"
        }
      }
    ]
  }
]

IMPORTANT:
- Insert a segment with `visuals.show_timer=true` (and speaker="Timer", text="...") between EVERY Question and Answer.
- For ANSWER segments, set `visuals.answer_reveal` to the specific item.
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