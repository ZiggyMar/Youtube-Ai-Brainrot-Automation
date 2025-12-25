# 🧠 YouTube AI Brainrot Automation 🚀

Welcome to the **Brainrot Factory 3000**! This project is a fully automated pipeline for creating those high-engagement, Gen-Alpha-slang-filled, SpongeBob-themed quiz videos that dominate YouTube Shorts and TikTok. 

---

## 🛠️ How It Works

The magic happens in three main stages:

1.  **The Brain (`core/director.py`)**: Uses **Google Gemini 1.5 Flash** to generate scripts. It picks characters, writes brainrot-infused dialogue (rizz, ohio, skibidi), and structures the quiz levels.
2.  **The Voice (`core/voicebox.py`)**: 
    - Generates base TTS using `edge-tts`.
    - Converts voices using **RVC** (Retrieval-based Voice Conversion) for that authentic SpongeBob sound.
3.  **The Studio (`core/video_factory.py`)**: Uses **MoviePy** to layer Minecraft parkour, character animations, dynamic subtitles, and sound effects.

---

## 📂 Project Structure

```text
Youtube/
├── core/               # Main engine scripts (Director, Voicebox, Factory)
├── utils/              # Setup and diagnostic utilities
├── data/               # JSON scripts, master lists, and logs
├── assets/             # Backgrounds, music, characters, and overlays
├── tools/              # FFmpeg and ImageMagick binaries
├── rvc_models/         # AI Voice models (.pth and .index files)
├── audio_cache/        # Generated voice segments
├── output/             # Final rendered videos
├── .env                # Your API keys (Keep this private!)
└── run.bat             # One-click Windows launcher
```

---

## 🚀 Quick Start

1.  **Setup**: 
    - Rename `.env.example` to `.env` (if not already done).
    - Paste your `GEMINI_API_KEY` into the `.env` file.
2.  **Install Dependencies**: 
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the Factory**:
    - Execute the main pipeline:
      ```bash
      python core/main.py
      ```
    - Or just double-click **`run.bat`**!

---

## 🎨 Visual Style

- **Font**: Impact (The classic meme font).
- **Colors**:
    - **SpongeBob**: Yellow 🟡 | **Patrick**: Pink 🌸 | **Squidward**: Cyan 🧊
    - **Plankton**: Green 🟢 | **Mr. Krabs**: Red 🦀

---

## ⚠️ Disclaimer
This project is for educational/entertainment purposes. Use your brainrot powers responsibly. Don't let the rizz get to your head. 💀
