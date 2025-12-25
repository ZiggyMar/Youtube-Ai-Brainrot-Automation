# 🧠 YouTube AI Brainrot Automation 🚀

Welcome to the **Brainrot Factory 3000**! This project is a fully automated pipeline for creating those high-engagement, Gen-Alpha-slang-filled, SpongeBob-themed quiz videos that dominate YouTube Shorts and TikTok. 

If you've ever wanted to make Squidward call someone "cooked" while Minecraft parkour plays in the background, you're in the right place.

---

## 🛠️ How It Works

The magic happens in three main stages:

1.  **The Brain (`director.py`)**: Uses **Google Gemini 1.5 Flash** to generate scripts. It picks characters (SpongeBob, Patrick, Squidward, etc.), writes brainrot-infused dialogue (rizz, ohio, skibidi), and structures the quiz levels.
2.  **The Voice (`voicebox.py`)**: 
    - First, it uses `edge-tts` to generate a base text-to-speech voice.
    - Then, it runs that audio through **RVC (Retrieval-based Voice Conversion)** to transform it into the actual voices of SpongeBob characters.
3.  **The Studio (`video_factory.py`)**: Uses **MoviePy** to layer everything together:
    - Minecraft parkour backgrounds.
    - Character images that "talk" (gentle swaying).
    - Dynamic subtitles with character-specific colors.
    - Background music and sound effects (timer ticking).
    - Green-screen overlays for timers.

---

## 📂 Where is Everything?

| Asset Type | Location | Description |
| :--- | :--- | :--- |
| **🎵 Music** | `assets/music/` | Lo-fi and catchy tracks like *Ladyfingers* and *The Lamp Is Low*. |
| **🎮 Gameplay** | `assets/backgrounds/` | High-quality Minecraft Parkour vertical videos. |
| **🗣️ Voice Models** | `rvc_models/` | The `.pth` and `.index` files for SpongeBob, Patrick, Squidward, Plankton, and Mr. Krabs. |
| **🎭 Characters** | `assets/characters/` | Transparent PNGs of our favorite Bikini Bottom residents. |
| **⏱️ Overlays** | `assets/overlays/` | Green-screen timer videos and other visual FX. |
| **📝 Scripts** | `video_scripts.json` | The JSON output from the Director, ready to be voiced. |

---

## 🚀 Quick Start

1.  **Setup**: 
    - Rename `.env.example` to `.env` (if not already done).
    - Paste your `GEMINI_API_KEY` into the `.env` file.
2.  **Install Dependencies**: 
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: Make sure you have **FFmpeg** installed and added to your system PATH.)*
3.  **Run the Factory**:
    - Execute `main.py` to run the full pipeline:
      ```bash
      python main.py
      ```
    - Or use `run.bat` if you're on Windows for a one-click solution!

---

## 🎨 Visual Style

- **Font**: Impact (The classic meme font).
- **Colors**:
    - **SpongeBob**: Yellow 🟡
    - **Patrick**: Pink 🌸
    - **Squidward**: Cyan 🧊
    - **Plankton**: Green 🟢
    - **Mr. Krabs**: Red 🦀

---

## ⚠️ Disclaimer
This project is for educational/entertainment purposes. Use your brainrot powers responsibly. Don't let the rizz get to your head. 💀
