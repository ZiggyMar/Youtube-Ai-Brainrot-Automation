# 🧠 YouTube AI Brainrot Automation

A high-performance, automated pipeline for generating viral "Brainrot" style trivia and quiz videos for YouTube Shorts, TikTok, and Reels. Featuring a visual layout editor and frame-perfect subtitle synchronization.

## 🚀 Features

- **Visual Layout Editor**: A browser-based tool (`tools/layout_editor.html`) to visually position and scale all video elements.
- **Perfect Sync Subtitles**: Word-level synchronization using OpenAI Whisper timestamps.
- **Multi-LLM Fallback**: Robust script generation using Gemini, Groq, Mistral, and OpenRouter to bypass quota limits.
- **Dynamic Character Animations**: Automatic character selection and "sway" animations based on speaker mood.
- **Professional Audio Mixing**: Automated TTS (Edge-TTS), Voice Conversion (RVC), and background music ducking.
- **Automated Overlays**: Integrated timer videos and CTA (Call to Action) overlays with green-screen masking.

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ZiggyMar/Youtube-Ai-Brainrot-Automation.git
   cd Youtube-Ai-Brainrot-Automation
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup FFmpeg**:
   Ensure FFmpeg is located in `tools/ffmpeg/ffmpeg.exe` or installed in your system PATH.

3. **Setup YouTube API**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Create a new project and enable the **YouTube Data API v3**.
   - Create **OAuth 2.0 Client IDs** (Desktop application).
   - Download the JSON file, rename it to `client_secrets.json`, and place it in the project root.
   - The first time you run the pipeline, a browser window will open for authorization.

4. **Configure Environment**:
   Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_key_here
   ```

## 🎨 Using the Layout Editor

1. Open `tools/layout_editor.html` in your browser.
2. Drag and scale elements (Character, Subtitles, Timer, CTA).
3. Adjust the **Difficulty List** font size in the properties panel.
4. Click **Export layout_config.json**.
5. Place the exported file in the project root.

## 🎬 Running the Pipeline

Simply run the main entry point:
```bash
python core/main.py
```

The pipeline will:
1. Generate scripts using the available AI provider.
2. Generate and convert audio files.
3. Transcribe audio for word-level timestamps.
4. Render the final production-ready MP4 files in the `output/` folder.

## 📁 Project Structure

- `core/`: Main logic (Director, Voicebox, Video Factory).
- `data/`: Scripts and layout configurations.
- `assets/`: Backgrounds, music, fonts, and character images.
- `tools/`: Layout editor and FFmpeg binaries.
- `audio_cache/`: Temporary audio and transcription files.
- `output/`: Final rendered videos.

## 📜 License
MIT
