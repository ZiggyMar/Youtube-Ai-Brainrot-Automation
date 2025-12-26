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

PROMPT_TEXT = """
You are a creative director for viral 'Shorts' trivia game videos.
Generate 1 NEW script.

THEME: SpongeBob SquarePants.
GAME TYPE: 'Avoid Saying the Same Thing'.

TITLE INSTRUCTIONS:
- Format: "Avoid saying the same thing as FREAKBOB [Optional Emoji/Variation] #Spongebob #Quiz #BrainrotQuiz #AIQuiz"
- MUST use "FREAKBOB" instead of "SpongeBob" in the title.
- MUST include hashtags: #Spongebob #Quiz #BrainrotQuiz #AIQuiz.
- Example: "Avoid saying the same thing as FREAKBOB 💀 #Spongebob #Quiz #BrainrotQuiz #AIQuiz"

OUTPUT FORMAT (actual "text" is an example of what is expected in the script, but should never be word for word):
[
  {
    "title": "Avoid saying the same thing as FREAKBOB 💀 #Spongebob #Quiz #BrainrotQuiz #AIQuiz",
    "script": [
      {
        "text": "If you're on youtube right now, you are out!",
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
      },
      {
        "text": "Round 2. Name a color.",
        "speaker": "SpongeBob",
        "visuals": {
          "character": "SpongeBob",
          "subtitle_color": "Yellow",
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
        "text": "I picked Blue. If you said Blue, you are out!",
        "speaker": "SpongeBob",
        "visuals": {
          "character": "SpongeBob",
          "subtitle_color": "Yellow",
          "list_highlight": "2. MEDIUM",
          "show_timer": false,
          "answer_reveal": "BLUE"
        }
      },
      {
        "text": "Round 3. Name a drink.",
        "speaker": "SpongeBob",
        "visuals": {
          "character": "SpongeBob",
          "subtitle_color": "Yellow",
          "list_highlight": "3. HARD",
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
          "list_highlight": "3. HARD",
          "show_timer": true,
          "answer_reveal": null
        }
      },
      {
        "text": "I picked Water. If you said Water, you are out!",
        "speaker": "SpongeBob",
        "visuals": {
          "character": "SpongeBob",
          "subtitle_color": "Yellow",
          "list_highlight": "3. HARD",
          "show_timer": false,
          "answer_reveal": "WATER"
        }
      },
      {
        "text": "Round 4. Name a planet.",
        "speaker": "SpongeBob",
        "visuals": {
          "character": "SpongeBob",
          "subtitle_color": "Yellow",
          "list_highlight": "4. IMPOSSIBLE",
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
          "list_highlight": "4. IMPOSSIBLE",
          "show_timer": true,
          "answer_reveal": null
        }
      },
      {
        "text": "I picked Mars. If you said Mars, you are out!",
        "speaker": "SpongeBob",
        "visuals": {
          "character": "SpongeBob",
          "subtitle_color": "Yellow",
          "list_highlight": "4. IMPOSSIBLE",
          "show_timer": false,
          "answer_reveal": "MARS"
        }
      }
    ]
  }
]

IMPORTANT:
- Insert a segment with `visuals.show_timer=true` (and speaker="Timer", text="...") between EVERY Question and Answer.
    time.sleep(2)
    
    if try_groq(): return
    print("⏳ Waiting 2s before fallback...")
    time.sleep(2)
    
    if try_mistral(): return
    print("⏳ Waiting 2s before fallback...")
    time.sleep(2)
    
    if try_openrouter(): return
    
    print("❌ CRITICAL: All AI providers failed. Using DUMMY script.")
    generate_dummy_script()

if __name__ == "__main__":
    generate_scripts()