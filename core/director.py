import os
import json
import requests
import sys
import time
import random
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
ARCHIVE_FILE = os.path.join(DATA_DIR, "archive_scripts.json")

PROMPT_TEXT = """
You are a creative director for viral 'Shorts' trivia game videos.
Generate 1 NEW script.

THEME: SpongeBob SquarePants.
GAME TYPE: 'Avoid Saying the Same Thing'.

TITLE INSTRUCTIONS:
- Format: "Avoid saying the same thing as FREAKBOB [Optional Emoji/Variation] #Spongebob #Quiz #BrainrotQuiz #AIQuiz"
- MUST use "FREAKBOB" instead of "SpongeBob" in the title.
- MUST include hashtags: #Spongebob #Quiz #BrainrotQuiz #AIQuiz.

SCRIPT STRUCTURE (STRICTLY FOLLOW THIS FLOW):

1. **THE HOOK (Instant Elimination)**
   - Speaker A (SpongeBob): "If you are [universal action e.g. breathing, blinking, sitting, touching a phone], you are eliminated."
   - Speaker B (Patrick/Squidward/etc): "But SpongeBob, everyone is doing that! Give them a chance."
   - Speaker A: "Fine! I'll let it slide. But only if you SUBSCRIBE right now." (MUST use the word "SUBSCRIBE" to trigger overlay).

2. **ROUND 1: THE TRAP (Obvious Answer)**
   - Speaker A: "First question. Name [Something with a VERY obvious answer]."
   - **TIMER SEGMENT (SPECIAL)**: During the timer, Speaker B (NOT the host) interrupts: "Don't say [The Obvious Answer]!"
   - Speaker A: "If you said [The Obvious Answer] you're out! Like the video if you survived."

3. **ROUND 2: STANDARD**
   - Speaker C: "Next question. Name [Category]."
   - **TIMER SEGMENT**: Silent or generic ticking.
   - Speaker C: "If you said [Item], you are out. Subscribe if you picked anything else."

4. **ROUND 3: COMMENT BAIT**
   - Speaker E: "Third question. Name [Category]."
   - **TIMER SEGMENT**: Silent or generic ticking.
   - Speaker F: "I bet they're gonna say [Item]."
   - Speaker E: "If you said [Item], you're cooked. Comment below how many you got right so far."

5. **FINAL ROUND: PICK A SIDE (A vs B)**
   - Speaker A: "Final question. Pick between [Option A] or [Option B]." (Do NOT say "Pick between A or B", say the actual options).
   - **TIMER SEGMENT**: Silent or generic ticking.
   - Speaker B: "[Short comment on one option]."
   - Speaker A: "If you picked [Option A], you're safe. If you picked [Option B], you HAVE to subscribe."

OUTPUT FORMAT (Follow this structure exactly):
[
  {
    "title": "Avoid saying the same thing as FREAKBOB \ud83d\udc80 #Spongebob #Quiz #BrainrotQuiz #AIQuiz",
    "script": [
      {
        "text": "If you are blinking right now, you are eliminated.",
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
        "text": "SpongeBob, come on! Everyone blinks!",
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
        "text": "Okay fine. I'll let it slide. But only if you SUBSCRIBE right now.",
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
        "text": "Round 1. Name something you eat at the Krusty Krab.",
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
        "text": "Don't say Krabby Patty!",
        "speaker": "Patrick",
        "visuals": {
          "character": "Patrick",
          "subtitle_color": "Pink",
          "list_highlight": "1. EASY",
          "show_timer": true,
          "answer_reveal": null
        }
      },
      {
        "text": "If you said Krabby Patty you're out! Like the video if you are still in.",
        "speaker": "SpongeBob",
        "visuals": {
          "character": "SpongeBob",
          "subtitle_color": "Yellow",
          "list_highlight": "1. EASY",
          "show_timer": false,
          "answer_reveal": "KRABBY PATTY"
        }
      },
      {
        "text": "Round 2. Name a color.",
        "speaker": "Patrick",
        "visuals": {
          "character": "Patrick",
          "subtitle_color": "Pink",
          "list_highlight": "2. MEDIUM",
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
          "list_highlight": "2. MEDIUM",
          "show_timer": true,
          "answer_reveal": null
        }
      },
      {
        "text": "I picked Pink. If you said Pink, you're out!",
        "speaker": "Patrick",
        "visuals": {
          "character": "Patrick",
          "subtitle_color": "Pink",
          "list_highlight": "2. MEDIUM",
          "show_timer": false,
          "answer_reveal": "PINK"
        }
      },
      ... (Continue through Round 4: IMPOSSIBLE)
    ]
  }
]

IMPORTANT:
- ONLY use these speakers: SpongeBob, Patrick, Squidward, Plankton, MrKrabs, Sandy.
- Insert a segment with `visuals.show_timer=true` between EVERY Question and Answer.
- **CRITICAL FOR ROUND 1**: The Timer segment MUST have a speaker (NOT 'Timer') and text "Don't say [Obvious Answer]!".
- For other rounds, the Timer segment can have speaker="Timer" and text="...".
- For ANSWER segments, set `visuals.answer_reveal` to the specific item.
- Include EXACTLY 4 Rounds: 1. EASY, 2. MEDIUM, 3. HARD, 4. IMPOSSIBLE.
- RETURN ONLY RAW JSON. NO MARKDOWN.
"""

def validate_and_repair_script(video):
    """Ensures the video object has all required fields and correct types."""
    if not isinstance(video, dict):
        return None
    
    # 1. Title
    if "title" not in video or not video["title"]:
        video["title"] = "Avoid saying the same thing as FREAKBOB 💀 #Spongebob #Quiz #BrainrotQuiz #AIQuiz"
    
    # 2. Script list
    if "script" not in video or not isinstance(video["script"], list):
        print(f"⚠️ Video '{video['title']}' is missing a valid 'script' list.")
        return None
    
    # 3. Speaker & Color Mapping
    speaker_colors = {
        "SpongeBob": "Yellow",
        "Patrick": "Pink",
        "Squidward": "Cyan",
        "Plankton": "Green",
        "MrKrabs": "Red",
        "Sandy": "Brown",
        "Announcer": "White",
        "Timer": "White"
    }
    
    repaired_script = []
    for i, seg in enumerate(video["script"]):
        if not isinstance(seg, dict):
            continue
            
        # Ensure basic fields
        seg["text"] = str(seg.get("text", "..."))
        seg["speaker"] = str(seg.get("speaker", "SpongeBob"))
        
        # Normalize speaker name (case-insensitive match)
        found_speaker = None
        for s in speaker_colors:
            if s.lower() == seg["speaker"].lower():
                found_speaker = s
                break
        if found_speaker:
            seg["speaker"] = found_speaker
        
        # Ensure visuals dict
        if "visuals" not in seg or not isinstance(seg["visuals"], dict):
            seg["visuals"] = {}
            
        v = seg["visuals"]
        v["character"] = v.get("character") or (seg["speaker"] if seg["speaker"] != "Timer" else None)
        
        # Normalize character name
        if v["character"]:
            for s in speaker_colors:
                if s.lower() == v["character"].lower():
                    v["character"] = s
                    break
        
        # Subtitle Color
        v["subtitle_color"] = v.get("subtitle_color") or speaker_colors.get(seg["speaker"], "White")
        # Normalize color name
        if isinstance(v["subtitle_color"], str):
            v["subtitle_color"] = v["subtitle_color"].capitalize()
        
        # List Highlight
        v["list_highlight"] = v.get("list_highlight") or "1. EASY"
        
        # Show Timer
        v["show_timer"] = bool(v.get("show_timer", False))
        if seg["speaker"] == "Timer":
            v["show_timer"] = True
            
        # Answer Reveal
        v["answer_reveal"] = v.get("answer_reveal")
        if v["answer_reveal"] == "null": v["answer_reveal"] = None
        
        repaired_script.append(seg)
    
    video["script"] = repaired_script
    return video

def save_scripts(data):
    try:
        # 1. Normalize input to a list of video objects
        if isinstance(data, dict):
            if "script" in data: 
                data = [data]
            elif "scripts" in data and isinstance(data["scripts"], list): 
                data = data["scripts"]
            elif "segments" in data: 
                data = [{"title": "Untitled Video", "script": data["segments"]}]
            else: 
                data = [data]
        
        if not isinstance(data, list):
            print(f"❌ Error: Expected list or dict, got {type(data)}")
            return False

        # 2. Check if it's a list of segments instead of a list of video objects
        if len(data) > 0 and "text" in data[0] and "speaker" in data[0]:
            print("⚠️ AI returned a flat list of segments. Wrapping into a video object...")
            data = [{"title": "Avoid saying the same thing as FREAKBOB 💀 #Spongebob #Quiz #BrainrotQuiz #AIQuiz", "script": data}]

        # 3. Final validation, repair, and ID assignment
        max_id = 0
        for fpath in [OUTPUT_FILE, ARCHIVE_FILE]:
            if os.path.exists(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                        if isinstance(existing, list):
                            for v in existing:
                                max_id = max(max_id, v.get("video_id", 0))
                except: pass

        final_data = []
        for i, video in enumerate(data):
            repaired_video = validate_and_repair_script(video)
            if not repaired_video:
                print(f"⚠️ Skipping invalid video object at index {i}")
                continue
            
            repaired_video["video_id"] = max_id + len(final_data) + 1
            final_data.append(repaired_video)
            
        if not final_data:
            print("❌ Error: No valid video scripts found in data.")
            return False

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2)
        print(f"✅ Success! Saved {len(final_data)} videos to {OUTPUT_FILE}")
        return True
    except Exception as e:
        print(f"❌ Error saving scripts: {e}")
        import traceback
        traceback.print_exc()
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
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
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
        headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"}
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
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
        payload = {"messages": [{"role": "user", "content": PROMPT_TEXT}], "model": "meta-llama/llama-3-8b-instruct:free"}
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        if "```json" in content: content = content.split("```json")[1].split("```")[0]
        elif "```" in content: content = content.split("```")[1].split("```")[0]
        return save_scripts(json.loads(content))
    except Exception as e:
        print(f"⚠️ OpenRouter Failed: {e}")
        return False

def generate_dummy_script():
    print("⚠️ Generating DUMMY script due to API failures...")
    rand_id = random.randint(1000, 9999)
    data = [{
        "title": f"Avoid saying the same thing as FREAKBOB {rand_id} 💀 #Spongebob #Quiz #BrainrotQuiz #AIQuiz",
        "script": [
            {"text": "If you are breathing right now, then you are out!", "speaker": "SpongeBob", "visuals": {"character": "SpongeBob", "subtitle_color": "Yellow", "list_highlight": "1. EASY", "show_timer": False, "answer_reveal": None}},
            {"text": "But SpongeBob, that's too mean! Give them another chance!", "speaker": "Patrick", "visuals": {"character": "Patrick", "subtitle_color": "Pink", "list_highlight": "1. EASY", "show_timer": False, "answer_reveal": None}},
            {"text": "Ugh, fine! But only if they SUBSCRIBE right now!", "speaker": "SpongeBob", "visuals": {"character": "SpongeBob", "subtitle_color": "Yellow", "list_highlight": "1. EASY", "show_timer": False, "answer_reveal": None}},
            {"text": "Round 1. Name a fruit.", "speaker": "SpongeBob", "visuals": {"character": "SpongeBob", "subtitle_color": "Yellow", "list_highlight": "1. EASY", "show_timer": False, "answer_reveal": None}},
            {"text": "Don't say Apple!", "speaker": "Patrick", "visuals": {"character": "Patrick", "subtitle_color": "Pink", "list_highlight": "1. EASY", "show_timer": True, "answer_reveal": None}},
            {"text": "I picked Apple!", "speaker": "SpongeBob", "visuals": {"character": "SpongeBob", "subtitle_color": "Yellow", "list_highlight": "1. EASY", "show_timer": False, "answer_reveal": "APPLE"}},
            {"text": "Round 2. Name a color.", "speaker": "SpongeBob", "visuals": {"character": "SpongeBob", "subtitle_color": "Yellow", "list_highlight": "2. MEDIUM", "show_timer": False, "answer_reveal": None}},
            {"text": "...", "speaker": "Timer", "visuals": {"character": None, "subtitle_color": "White", "list_highlight": "2. MEDIUM", "show_timer": True, "answer_reveal": None}},
            {"text": "I picked Blue!", "speaker": "SpongeBob", "visuals": {"character": "SpongeBob", "subtitle_color": "Yellow", "list_highlight": "2. MEDIUM", "show_timer": False, "answer_reveal": "BLUE"}},
            {"text": "Round 3. Name a drink.", "speaker": "SpongeBob", "visuals": {"character": "SpongeBob", "subtitle_color": "Yellow", "list_highlight": "3. HARD", "show_timer": False, "answer_reveal": None}},
            {"text": "...", "speaker": "Timer", "visuals": {"character": None, "subtitle_color": "White", "list_highlight": "3. HARD", "show_timer": True, "answer_reveal": None}},
            {"text": "I picked Water!", "speaker": "SpongeBob", "visuals": {"character": "SpongeBob", "subtitle_color": "Yellow", "list_highlight": "3. HARD", "show_timer": False, "answer_reveal": "WATER"}},
            {"text": "Round 4. Name a planet.", "speaker": "SpongeBob", "visuals": {"character": "SpongeBob", "subtitle_color": "Yellow", "list_highlight": "4. IMPOSSIBLE", "show_timer": False, "answer_reveal": None}},
            {"text": "...", "speaker": "Timer", "visuals": {"character": None, "subtitle_color": "White", "list_highlight": "4. IMPOSSIBLE", "show_timer": True, "answer_reveal": None}},
            {"text": "I picked Mars!", "speaker": "SpongeBob", "visuals": {"character": "SpongeBob", "subtitle_color": "Yellow", "list_highlight": "4. IMPOSSIBLE", "show_timer": False, "answer_reveal": "MARS"}}
        ]
    }]
    return save_scripts(data)

def generate_scripts():
    print("🎬 Starting Script Generation with Fallbacks...")
    if try_gemini(): return
    time.sleep(2)
    if try_groq(): return
    time.sleep(2)
    if try_mistral(): return
    time.sleep(2)
    if try_openrouter(): return
    print("❌ CRITICAL: All AI providers failed. Using DUMMY script.")
    generate_dummy_script()

if __name__ == "__main__":
    generate_scripts()