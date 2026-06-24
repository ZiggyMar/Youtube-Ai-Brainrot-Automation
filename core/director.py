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

PROMPT_TEMPLATE_BASE = """
You are a creative director for viral 'Shorts' trivia game videos.
Generate 1 NEW script.

THEME: {theme}
GAME TYPE: 'Avoid Saying the Same Thing' (or similar elimination format).

TITLE INSTRUCTIONS:
- Create a viral, clickbaity title suitable for the theme.
- DO NOT start every title with "Avoid Saying The Same Thing".
- GOOD EXAMPLES: "Can You Beat SpongeBob?", "Only 1% Pass This Test", "99% Impossible Challenge".
- MUST end with 3-4 relevant, DISTINCT hashtags including #Shorts and #{theme_hashtag} (do not repeat the same hashtag twice).

STYLE INSTRUCTIONS:
{style_instructions}

SCRIPT STRUCTURE (this is the PROVEN formula that grew a real channel 0 -> 40K subscribers - copy it precisely):

1. **THE HOOK + INSTANT SUBSCRIBE GATE**
   - Host (the LEAD character) MUST open by SCREAMING "WAIT!" to stop the scroll, then immediately the callout — e.g. "WAIT! If you are {intro_action} right now, you're eliminated." The "WAIT!" is a loud, urgent shout in the very first second whose ONLY job is to freeze a swiping thumb. ALWAYS start the first line with "WAIT!".
   - Sidekick (a DIFFERENT character) defends the viewer BY NAME, energetic with an exclamation: e.g. "But [Host's name], everyone is {intro_action}! Give them a chance!"
   - Host relents and gates survival on subscribing: "Ugh, fine! I'll let it slide... but ONLY if you SUBSCRIBE right now!" (MUST contain the word SUBSCRIBE; keep the urgency).

2. **ROUND 1 (EASY) -> LIKE CTA**
   - Host: "First question. Name a/an [broad category about {theme}]."
   - (Optional timer interrupt - see TIMER VARIETY) a character teases: "Don't say [Obvious Answer]!"
   - Host: "If you said [Obvious Answer] you're out! Like the video if you survived." (the LIKE call-to-action)

3. **ROUND 2 (MEDIUM) -> NO CTA (just the game + character humor)**
   - A character: "Next question. Name a/an [category about {theme}]."
   - (Optional timer interrupt) a character teases the obvious answer.
   - "If you said [Item], you're out!" — DO NOT add a like/subscribe/comment call-to-action here. Just the elimination, ideally with an in-character joke. (Spreading CTAs every single round feels beggy and makes people unsubscribe.)
   {round_2_override}

4. **ROUND 3 (HARD) -> COMMENT CTA**
   - A character: "Third question. Name a/an [category about {theme}]."
   - (Optional timer interrupt) "I bet they're gonna say [Item]..."
   - "If you said [Item], you're cooked. Comment below how many you got right!" (the COMMENT call-to-action)
   {round_3_override}

{final_round_description}

TIMER VARIETY (IMPORTANT): Do NOT put an interrupt on every round. About HALF the rounds (e.g. 2 of 4) should have a character interrupt DURING the timer ("Don't say X!" / "I bet they'll say X..."); the rest should be a SILENT timer segment (speaker="Timer", text="..."). Vary which rounds get the interrupt so videos don't feel repetitive.

CHARACTER PERSONALITY (IMPORTANT - this is what makes videos likeable & shareable): EVERY elimination/answer line MUST carry a short in-character joke, not a flat "you're out". Squidward sarcastic ("Squidward's not happy, you're eliminated"), MrKrabs greedy ("ARRGH, my money!" / "I'll just steal the formula!"), Plankton scheming ("my plans are ruined again!"), SpongeBob hyper and silly, Patrick lovable-but-dumb defending the viewer. The best-performing video leaned HARD into these jokes - dry, joke-less eliminations underperform, so never write a bare elimination.

OUTPUT FORMAT (Follow this structure exactly):
[
  {
    "title": "Viral Video Title #Hashtags",
    "script": [
      {
        "text": "WAIT! If you are {intro_action} right now, you are eliminated.",
        "speaker": "SpongeBob",
        "visuals": {
          "character": "SpongeBob",
          "subtitle_color": "Yellow",
          "list_highlight": "1. EASY",
          "show_timer": false,
          "answer_reveal": null
        }
      },
      ... (Follow the structure for all rounds)
    ]
  }
]

IMPORTANT:
- **STRICTLY USE ONLY THESE SPEAKERS**: ["SpongeBob", "Patrick", "Squidward", "Plankton", "MrKrabs"].
- **DO NOT** use any other names like "Narrator", "Host", "Reporter", "Sandy", or "Voice".
- Even if the theme is News or Pop Culture, assign the roles to these characters (e.g., SpongeBob as the Reporter).
- **TIMER RULES (CRITICAL)**:
  - For **QUESTION** segments: Set `visuals.show_timer=false`. (NEVER true).
  - For **ANSWER** segments: Set `visuals.show_timer=false`. (NEVER true).
  - For **HOOK** segments: Set `visuals.show_timer=false`.
  - ONLY set `visuals.show_timer=true` for the dedicated **TIMER** segments between Question and Answer.
- **INTERRUPT/BET LINES ARE THE TIMER SEGMENT (CRITICAL)**: The "Don't say [X]!" interrupt and the "I bet they're gonna say [X]..." bet lines are spoken WHILE the timer is on screen. Each MUST be a single timer segment with `show_timer=true` AND a real character as the speaker (NOT "Timer"). DO NOT create a separate segment after the timer for these lines, and DO NOT also emit a silent speaker="Timer" segment for that round. Each round has exactly ONE timer segment.
- **ITEM CONSISTENCY (CRITICAL)**: Within a single round, the item named in the timer line ("Don't say [X]!" / "I bet they're gonna say [X]...") MUST be the EXACT SAME item used in that round's elimination line ("If you said [X], you're out") and in `answer_reveal`. Never name two different items in the same round.
- **QUESTION FORMAT (CRITICAL for "don't say the same thing")**: Every question MUST be "Name a/an [broad category]" or "Pick between [X] or [Y]" — something a viewer would instinctively blurt out loud. NEVER ask for a single specific fact that only one answer fits (e.g. a license-plate number, an exact date, a phone number, a specific name). If only one answer is possible, the "don't say the same thing" premise breaks.
- **SUBSCRIBE FREQUENCY (CRITICAL)**: The word "subscribe" must appear EXACTLY TWICE in the whole script — once in the HOOK gate, and once in the FINAL round. NEVER say "subscribe" in the middle rounds (Round 2 or Round 3). Asking every round is beggy and makes people unsubscribe. Middle rounds use at most a LIKE (Round 1) and a COMMENT (Round 3) — nothing more.
- **GLOBAL REACH**: If the THEME is NOT SpongeBob-specific (e.g. "Universal Everyday Trivia" or "Hot Takes"), the QUESTIONS must be universal and globally-relatable to any English speaker (everyday colors, foods, animals, countries, first names, "pick heads or tails", "name any sport") and require NO niche/fandom knowledge. ALWAYS still use the SpongeBob characters as the fun presenters (they are the only available voices/images).
- For ANSWER segments, set `visuals.answer_reveal` to the specific item.
- **ROUND 4 (FINAL ROUND) RULES**:
{final_round_instructions}
- RETURN ONLY RAW JSON. NO MARKDOWN.
"""

FINAL_ROUND_VARIANTS = {
    "BINARY_SUBSCRIBE": {
        "description": "5. **FINAL ROUND (IMPOSSIBLE): THE BINARY CHOICE** (the proven closer)\n   - Host: \"Final question. Choose between [Option A] or [Option B].\" (two fun options tied to {theme}).\n   - Resolution: give a playful response for BOTH options, and make ONE branch trigger a subscribe: \"If you picked [A] you're awesome! If you picked [B], hit subscribe because [in-character themed reason].\"",
        "instructions": """  - The final question MUST be a binary choice: "Choose between [Option A] or [Option B]" (both tied to {theme}).
  - The resolution MUST give a fun in-character response for BOTH options.
  - The losing/other branch MUST tell the viewer to subscribe with a playful in-character reason (the line MUST contain the word "subscribe").
  - You MAY include a short silent timer segment (speaker="Timer", text="...") between the question and the resolution.
- Include EXACTLY 4 Rounds: 1. EASY, 2. MEDIUM, 3. HARD, 4. IMPOSSIBLE. The final round is the binary-choice subscribe close."""
    },
    "UNFINISHED_SYMPHONY": {
        "description": "5. **FINAL ROUND: THE UNFINISHED SYMPHONY** (retention loop - the answer is NEVER revealed)\n   - Speaker A: \"Final question! But you HAVE to subscribe to find out if you're right... Name a/an [broad category].\" (MUST contain the word subscribe).\n   - **TIMER SEGMENT**: Silent ticking.\n   - **STOP HERE.** The video ends on the timer. NO answer is ever revealed - this makes viewers rewatch and the Short loops.",
        "instructions": """  - Speaker A MUST ask the Final Question in "Name a/an [category]" form, and the question line MUST include a subscribe push (e.g. "you have to subscribe to find out if you're right").
  - The NEXT and LAST segment MUST be a silent Timer segment (speaker="Timer", text="...", show_timer=true).
  - **STOP HERE.** The video ends immediately after the Timer.
  - **DO NOT** generate an Answer segment for Round 4 (the answer is never revealed - this is the retention loop).
  - The last item in the script array must be the Timer segment.
- Include EXACTLY 4 Rounds: 1. EASY, 2. MEDIUM, 3. HARD, 4. IMPOSSIBLE (Question + silent Timer ONLY)."""
    },
    "THE_BET": {
        "description": "5. **FINAL ROUND: THE BET** (retention loop - the answer is NEVER revealed)\n   - Speaker A: \"Final question - subscribe right now or you'll never know if you're right! Name a/an [broad category].\" (MUST contain the word subscribe).\n   - **TIMER SEGMENT (with bet)**: Speaker B says DURING the timer: \"I bet you're gonna say [Answer]...\" (show_timer=true, speaker=Speaker B).\n   - **STOP HERE.** The video ends on the timer. NO Answer Reveal.",
        "instructions": """  - Speaker A MUST ask the Final Question in "Name a/an [category]" form, and the question line MUST include a subscribe push (e.g. "subscribe or you'll never know if you're right").
  - The NEXT and LAST segment MUST be the Timer segment: show_timer=true, a real character as speaker, text "I bet you're gonna say [Answer]...".
  - **STOP HERE.** The video ends immediately after that timer segment.
  - **DO NOT** generate an Answer Reveal segment (the viewer never hears the answer - this is the retention loop).
  - The last item in the script array must be that timer-with-bet segment.
- Include EXACTLY 4 Rounds: 1. EASY, 2. MEDIUM, 3. HARD, 4. IMPOSSIBLE (Question + Timer-with-bet ONLY)."""
    }
}


STYLES = {
    "STANDARD": {
        "instructions": "Keep the questions fair and standard. Focus on interesting trivia related to the theme.",
        "round_2_override": "",
        "round_3_override": ""
    },
    "CORRECTION_BAIT": {
        "instructions": "Generate a 'Correction Bait' script. In Round 2, the 'Correct Answer' MUST be factually WRONG. Do NOT acknowledge it is wrong. The goal is to make people comment corrections.",
        "round_2_override": "IMPORTANT: For Round 2, the Host MUST give a WRONG answer confidently. Example: 'Name the capital of France' -> 'If you said London, you are out!' (London is wrong).",
        "round_3_override": ""
    },
    "SOCIAL_ROULETTE": {
        "instructions": "Generate a 'Social Roulette' script. In Round 3, instead of a normal elimination, give a 'Share Challenge'.",
        "round_2_override": "",
        "round_3_override": "IMPORTANT: For Round 3, the question MUST be a Share Challenge. Example: 'Send this to the 2nd person on your share list.' The 'Answer' part should be: 'If they don't reply in 5 minutes, they owe you money.'"
    },
    "RAGE_BAIT": {
        "instructions": "Generate a 'Rage Bait' script. In Round 3 or 4, give an IMPOSSIBLE instruction.",
        "round_2_override": "",
        "round_3_override": "IMPORTANT: For Round 3, give an IMPOSSIBLE instruction. Example: 'Touch your nose with your elbow.' Then say 'If you couldn't do it, you're out!'"
    },
    "AMBIGUOUS_ELIMINATION": {
        "instructions": "Generate a 'Schrödinger’s Comment' script. In one round, make the elimination reason AMBIGUOUS.",
        "round_2_override": "",
        "round_3_override": "IMPORTANT: For Round 3, be AMBIGUOUS. Example: 'If you are wearing... uh... that color, you're out.' (Do NOT say the color). This forces people to ask 'WHAT COLOR??' in comments."
    }
}

# ONLY the two formats that grew the channel: SpongeBob "avoid saying the same thing"
# and "Hot Takes" quizzes. The OG "Did You Know"/news/fact format is intentionally removed.
THEMES = [
    {"name": "SpongeBob SquarePants", "hashtag": "Spongebob"},
    {"name": "SpongeBob SquarePants", "hashtag": "Spongebob"},  # higher weight - top performer (49K-view EP8)
    {"name": "SpongeBob SquarePants", "hashtag": "Spongebob"},  # majority SpongeBob, but not exclusively
    {"name": "Universal Everyday Trivia", "hashtag": "Quiz"},      # global reach - colors/foods/countries/animals
    {"name": "Unpopular Opinions / Hot Takes", "hashtag": "HotTakes"}  # global reach - relatable hot takes
]

TITLE_TEMPLATES = [
    # === PROVEN WINNERS (listed multiple times to weight selection toward them) ===
    # "Only 1% Can Survive This SpongeBob Game! 🧽" was the top converter (+27 subs / 2.26%).
    "Only 1% Can Survive This {theme} Game! 🧽",
    "Only 1% Can Survive This {theme} Game! 🧽",
    "Only 1% Can Survive This {theme} Challenge! 🧽",
    "Only 1% Can Survive This {theme} Challenge! 🧽",
    "Can You Survive This {theme} Game? 🧽",
    "99% Of People Fail This {theme} Test 🧽",
    "Can You Beat {character}? (Impossible Mode) ⭐️",
    "Only True Fans Know The Answer... 🤫",
    "DON'T SAY THE SAME THING AS ME!❌",
    "Avoid Saying The Same Thing As {character}🧽!",
    "Avoid saying the same ❌😆",
    "Can You Beat {character}? (99% IMPOSSIBLE) 🧠",
    "Only Gen Z Can Pass This Test 🤫",
    "{theme} Trivia: 99% Fail 🚫",
    "Do You Know {theme} Better Than {character}? 🤔",
    "If You Say The Same Thing As {character}, You're Out! 🚫",
    "The Hardest {theme} Quiz Ever? 🤯",
    "Can You Survive This {theme} Challenge? 💀",
    "Don't Get Eliminated By {character}! 😱",
    "Bet You Can't Beat {character} At This Game 😈",
    "Are You Smarter Than {character}? 🧠",
    "The Ultimate {theme} Brain Rot Quiz 🤪",
    "You Will Fail This {theme} Challenge 🛑",
    "Don't Pick The Same Answer As {character}! ⚠️",
    "Survival Mode: {theme} Edition 🛡️",
    "Impossible {theme} Trivia (99% Fail) 📉",
    "Can You Beat The {theme} AI? 🤖",
    "Only 1% Can Beat {character} 🥇",
    "Don't Say It! ({theme} Edition) 🤐",
    "The {theme} Test You Will Fail 📉",
    "Brain Rot Quiz: {theme} Edition 🧠",
    "Do Not Say The Same Thing! 🚫",
    "Challenge: Beat {character} In 4 Rounds 🥊",
    "Test Your {theme} Knowledge! 📚",
    "Are You A Fake {theme} Fan? 🧐",
    "Level 99 {theme} Boss Fight ⚔️",
    "Don't Let {character} Win! 🏆",
    "Speedrun This {theme} Quiz ⏱️",
    "Can You Name These {theme} Items? 🧐",
    "The Impossible {theme} Challenge 🚫",
    "Only 0.1% Pass This {theme} Test 📉",
    "Don't Blink! {theme} Edition 👁️",
    "You Vs {character}: Who Wins? 🥊",
    "The Ultimate {theme} Trivia Gauntlet 🛡️",
    "Can You Beat The {theme} Master? 🧙‍♂️",
    "Don't Make A Mistake! ({theme}) ❌",
    "The {theme} Quiz That Breaks Friendships 💔",
    "Are You A {theme} Expert? 🎓",
    "Prove You Know {theme} 📜",
    "The {theme} Test: Impossible Mode 💀",
    "Don't Say The Same As {character} (Hard) 😤",
    "Can You Outsmart {character}? 🧠",
    "The {theme} Challenge No One Passes 🚫",
    "Expert Level {theme} Trivia 🤓",
    "God Level {theme} Quiz 😇",
    "Noob vs Pro: {theme} Edition 👶👴",
    "The {theme} IQ Test 🧠",
    "What Is Your {theme} IQ? 📉",
    "Only {character} Can Pass This 🤫",
    "Don't Get Tricked By {character}! 🤡",
    "The {theme} Trap 🪤",
    "Beware of {character}! ({theme}) ⚠️",
    "The Cursed {theme} Quiz 👻",
    "Do You Remember {theme}? 🕰️",
    "The Nostalgia {theme} Test 📺",
    "Can You Guess The {theme} Character? 👤",
    "Who Is This {theme} Character? 🕵️‍♂️",
    "The {theme} Mystery Quiz 🔍",
    "Solve This {theme} Riddle 🧩",
    "The {theme} Puzzle 🧩",
    "Don't Laugh: {theme} Edition 😐",
    "Try Not To Say The Same Thing ({theme}) 🤐",
    "The Silent {theme} Challenge 🤫"
]

HASHTAG_POOL = [
    "#brainteasers", "#mindgames", "#didyouknow", "#spongebob", 
    "#mindgamesrevealed", "#shorts", "#challenge", "#trivia", 
    "#quiz", "#brainrot", "#game", "#fun", "#viral"
]

def dedupe_title_hashtags(title):
    """Removes duplicate hashtags from a title (case-insensitive), preserving order.
    e.g. 'Beat SpongeBob #Quiz #Brainrot #Shorts #Quiz' -> '... #Quiz #Brainrot #Shorts'."""
    if not title or "#" not in title:
        return title
    head, _, tags_part = title.partition("#")
    tags = ("#" + tags_part).split()
    seen, kept = set(), []
    for tag in tags:
        key = tag.lstrip("#").lower()
        if key and key not in seen:
            seen.add(key)
            kept.append(tag)
    return (head.rstrip() + " " + " ".join(kept)).strip()

def get_recent_titles():
    """Reads every past title (output, archive, AND the permanent video_archive) so we
    NEVER reuse a title - identical titles across uploads can trigger spam/ban flags."""
    titles = set()
    for fpath in [OUTPUT_FILE, ARCHIVE_FILE]:
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for v in data:
                            if "title" in v and v["title"]:
                                titles.add(v["title"].split("#")[0].strip().lower())
            except: pass
    # Also scan the permanent per-video archive (every video ever made).
    archive_root = os.path.join(DATA_DIR, "video_archive")
    if os.path.isdir(archive_root):
        try:
            for folder in os.listdir(archive_root):
                meta = os.path.join(archive_root, folder, "meta.json")
                if os.path.exists(meta):
                    with open(meta, "r", encoding="utf-8") as f:
                        t = json.load(f).get("title", "")
                        if t:
                            titles.add(t.split("#")[0].strip().lower())
        except: pass
    return titles

def generate_varied_title(theme="SpongeBob", character="SpongeBob", forbidden_titles=None):
    if forbidden_titles is None:
        forbidden_titles = set()
        
    for _ in range(20): # Try 20 times to find a unique title
        template = random.choice(TITLE_TEMPLATES)
        title_base = template.replace("{theme}", theme).replace("{character}", character)
        
        # Check uniqueness of the base title (ignoring hashtags for now)
        clean_title = title_base.strip().lower()
        if clean_title not in forbidden_titles:
            # Pick 2-3 unique hashtags
            num_hashtags = random.randint(2, 3)
            hashtags = random.sample(HASHTAG_POOL, num_hashtags)
            return f"{title_base} {' '.join(hashtags)}"
            
    # Fallback if we can't find a unique one (unlikely with 30+ templates)
    template = random.choice(TITLE_TEMPLATES)
    title_base = template.replace("{theme}", theme).replace("{character}", character)
    num_hashtags = random.randint(2, 3)
    hashtags = random.sample(HASHTAG_POOL, num_hashtags)
    return f"{title_base} {' '.join(hashtags)}"

def get_prompt_text(forced_theme=None, forced_hashtag=None):
    # Openers are constrained to UNIVERSAL states that implicate ~100% of anyone scrolling
    # a Short (the winning video used "sitting down"; weak non-universal callouts like
    # "wearing socks" underperformed). Every option here is true of nearly every viewer.
    actions = [
        "breathing", "blinking", "sitting down", "holding your phone",
        "touching your screen", "awake", "alive", "watching this short",
        "scrolling right now", "using your thumb",
    ]
    action = random.choice(actions)
    
    # Pick a random style and theme
    style_name = random.choice(list(STYLES.keys()))
    style_config = STYLES[style_name]
    
    if forced_theme:
        theme_name = forced_theme
        theme_hashtag = forced_hashtag if forced_hashtag else "Quiz"
        print(f"🎲 Using Forced Theme: {theme_name}")
    else:
        theme_obj = random.choice(THEMES)
        theme_name = theme_obj["name"]
        theme_hashtag = theme_obj["hashtag"]
        print(f"🎲 Selected Style: {style_name} | Theme: {theme_name}")

    # Select a Final Round Ending - a deliberate 50/50 split:
    #   - 50% "finishing close" (BINARY_SUBSCRIBE): the video resolves the final round.
    #   - 50% retention loop (THE_BET / UNFINISHED_SYMPHONY): the final answer is NEVER
    #     revealed -> viewers rewatch to the end -> the Short loops -> watch-time exceeds
    #     100% -> YouTube pushes harder.
    ending_pool = (
        ["THE_BET"] * 1 +
        ["UNFINISHED_SYMPHONY"] * 1 +
        ["BINARY_SUBSCRIBE"] * 2
    )
    ending_variant_name = random.choice(ending_pool)
    ending_config = FINAL_ROUND_VARIANTS[ending_variant_name]
    print(f"🔚 Selected Ending: {ending_variant_name}")
    
    prompt = PROMPT_TEMPLATE_BASE.replace("{intro_action}", action)
    prompt = prompt.replace("{theme}", theme_name)
    prompt = prompt.replace("{theme_hashtag}", theme_hashtag)
    prompt = prompt.replace("{style_instructions}", style_config["instructions"])
    prompt = prompt.replace("{round_2_override}", style_config["round_2_override"])
    prompt = prompt.replace("{round_3_override}", style_config["round_3_override"])
    prompt = prompt.replace("{final_round_description}", ending_config["description"])
    prompt = prompt.replace("{final_round_instructions}", ending_config["instructions"])
    
    return prompt

def validate_and_repair_script(video, existing_titles=None):
    """Ensures the video object has all required fields and correct types."""
    if not isinstance(video, dict):
        return None
    
    if existing_titles is None:
        existing_titles = set()
    
    # 1. Title & Hook Text
    if "hook_text" not in video:
        # HOOK_STYLE flag (read from layout_config.json) lets you A/B without
        # code edits:  "punch" = rotating high-CTR pool (default, the fix for
        # the 47.9% swipe-away);  "classic" = original single hardcoded line.
        try:
            import json as _json, os as _os
            _cfg_path = _os.path.join(
                _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                "layout_config.json",
            )
            with open(_cfg_path, "r", encoding="utf-8") as _cf:
                _hook_style = _json.load(_cf).get("HOOK_STYLE", "punch")
        except Exception:
            _hook_style = "punch"

        if _hook_style == "classic":
            video["hook_text"] = "Don't Say The Same Thing!"
        else:
            video["hook_text"] = random.choice([
                "ONLY 1% CAN BEAT THIS",
                "99% WILL FAIL THIS",
                "DON'T SAY THE WORD",
                "BET YOU CAN'T DO THIS",
                "ONLY GENIUSES PASS",
                "THIS BREAKS YOUR BRAIN",
                "QUICK! DON'T LOOK AWAY",
                "WATCH BEFORE IT'S GONE",
                "THIS QUIZ IS RIGGED",
                "YOU'LL FAIL IN 5 SECONDS",
            ])
        
    if "title" not in video or not video["title"]:
        video["title"] = generate_varied_title(forbidden_titles=existing_titles)
    else:
        clean = video["title"].split("#")[0].strip().lower()
        # Regenerate a unique title if it's generic OR collides with any past title.
        if clean in existing_titles or video["title"].lower().startswith("avoid saying the same thing"):
            print(f"   ↻ Title collision/generic ('{video['title'][:40]}...') - regenerating unique title.")
            video["title"] = generate_varied_title(forbidden_titles=existing_titles)
             
    # Remove any duplicated hashtags (e.g. "#Quiz ... #Quiz")
    video["title"] = dedupe_title_hashtags(video["title"])

    # Add the new title to existing_titles to prevent duplicates in the same batch
    clean_new_title = video["title"].split("#")[0].strip().lower()
    existing_titles.add(clean_new_title)
    
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
        "Timer": "White",
        "Narrator": "White",
        "Sidekick": "Yellow",
        "NewsAnchor": "Blue",
        "Reporter": "Green"
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
    
    # Check for round count
    round_count = 0
    for seg in repaired_script:
        txt = seg["text"].lower()
        if "round" in txt and "name" in txt:
            round_count += 1
        elif "final question" in txt:
            round_count += 1
            
    if round_count < 4:
        print(f"⚠️ Warning: Script for '{video['title']}' seems to have only {round_count} rounds (expected 4).")

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
            # We need to fetch existing titles here too if we want uniqueness, 
            # but for simplicity let's just use the function. Ideally we'd move get_recent_titles up.
            # Let's just call it here, it's fast enough.
            existing_titles_fallback = get_recent_titles()
            data = [{"title": generate_varied_title(forbidden_titles=existing_titles_fallback), "script": data}]

        # 3. Final validation, repair, and ID assignment
        max_id = 0
        existing_titles = get_recent_titles()
        
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
            repaired_video = validate_and_repair_script(video, existing_titles)
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

def try_gemini(forced_theme=None, forced_hashtag=None):
    print("🔹 Attempting Gemini...")
    if not GEMINI_API_KEY: return False
    
    # Split keys by comma and strip whitespace
    api_keys = [k.strip() for k in GEMINI_API_KEY.split(',') if k.strip()]
    
    for i, key in enumerate(api_keys):
        print(f"   Trying Gemini Key #{i+1}...")
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=get_prompt_text(forced_theme, forced_hashtag),
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return save_scripts(json.loads(response.text))
        except Exception as e:
            print(f"⚠️ Gemini Key #{i+1} Failed: {e}")
            # If this was the last key, return False to trigger fallback
            if i == len(api_keys) - 1:
                print("❌ All Gemini keys failed.")
                return False
            print("   Switching to next key...")
            time.sleep(1) # Brief pause before next key
            
    return False

def try_groq(forced_theme=None, forced_hashtag=None):
    print("🔹 Attempting Groq...")
    if not GROQ_API_KEY: return False
    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "messages": [{"role": "user", "content": get_prompt_text(forced_theme, forced_hashtag)}],
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

def try_mistral(forced_theme=None, forced_hashtag=None):
    print("🔹 Attempting Mistral...")
    if not MISTRAL_API_KEY: return False
    try:
        headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "messages": [{"role": "user", "content": get_prompt_text(forced_theme, forced_hashtag)}],
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

def try_openrouter(forced_theme=None, forced_hashtag=None):
    print("🔹 Attempting OpenRouter...")
    if not OPENROUTER_API_KEY: return False
    try:
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
        payload = {"messages": [{"role": "user", "content": get_prompt_text(forced_theme, forced_hashtag)}], "model": "meta-llama/llama-3-8b-instruct:free"}
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
    action = random.choice(["breathing", "blinking", "sitting down", "holding your phone", "touching your screen", "awake", "watching this short", "scrolling right now"])
    existing_titles = get_recent_titles()
    data = [{
        "title": generate_varied_title(forbidden_titles=existing_titles),
        "hook_text": random.choice(["99% WILL FAIL THIS", "ONLY 1% CAN BEAT THIS", "YOU'LL FAIL IN 5 SECONDS"]),
        "script": [
            {"text": f"WAIT! If you are {action} right now, then you are out!", "speaker": "SpongeBob", "visuals": {"character": "SpongeBob", "subtitle_color": "Yellow", "list_highlight": "1. EASY", "show_timer": False, "answer_reveal": None}},
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

def generate_scripts(forced_theme=None, forced_hashtag=None):
    print("🎬 Starting Script Generation with Fallbacks...")
    if try_gemini(forced_theme, forced_hashtag): return
    time.sleep(2)
    if try_groq(forced_theme, forced_hashtag): return
    time.sleep(2)
    if try_mistral(forced_theme, forced_hashtag): return
    time.sleep(2)
    if try_openrouter(forced_theme, forced_hashtag): return
    print("❌ CRITICAL: All AI providers failed. Using DUMMY script.")
    generate_dummy_script()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=str, help="Force a specific topic/theme")
    parser.add_argument("--hashtag", type=str, help="Force a specific hashtag (optional)")
    args = parser.parse_args()
    
    generate_scripts(args.topic, args.hashtag)