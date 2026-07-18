<div align="center">

<!-- TODO: Insert a REAL screenshot or banner of your project here -->
<!-- ![YouTube AI Brainrot Automation Banner](assets/docs/real_banner.png) -->

# 🧠 Open-Source GenAI Video Rendering Framework

**A Headless Programmatic Video Compositing and Multi-Modal Orchestration Engine.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/ZiggyMar/Youtube-Ai-Brainrot-Automation/issues)

</div>

---

## 📖 System Overview

This framework is a highly stable, extensible **Multi-Modal Orchestration Engine** designed for **Headless Programmatic Video Compositing**. It solves the complex architectural challenge of synchronously bridging non-deterministic text generation (via LLMs), multi-stage audio processing pipelines (TTS and RVC voice cloning), and strict time-coded video layers (via FFmpeg). 

By providing a robust, data-driven compositing pipeline, this open-source framework democratizes advanced media generation infrastructure—capabilities typically paywalled behind expensive, closed-source SaaS platforms charging $50-$100/month.

## ⚙️ Deep Dive Into Core Systems

### Multi-LLM Resiliency Engine
At the core of the content generation tier is an abstract token provider that manages distributed API rate limits, implements graceful fallbacks, and enforces strict JSON schema validation across heterogeneous models (including Gemini, Groq, and Mistral). This ensures that upstream text generation maintains high availability and deterministic structured output regardless of individual provider outages.

### Deterministic Subtitle Component
To solve the industry-wide issue of subtitle drift, the pipeline programmatically parses raw JSON timestamp metadata emitted by OpenAI Whisper. It translates this data into a highly structured `layout_config.json` schema, driving the FFmpeg compositing engine to achieve frame-perfect, word-by-word UI rendering without drift over long durations.

### Headless Audio Engineering
The framework executes an automated audio-ducking pipeline that programmatically analyzes backing tracks, invokes Voice Conversion (RVC) models on synthesized speech, and cleanly merges the resulting frequency layers via complex FFmpeg filter graphs. This results in broadcast-quality audio mixes decoupled from any manual editing interface.

### Extensible Visual Orchestration
*   🎥 **Visual Layout Editor**: A decoupled, browser-based configuration tool for serializing positional data and visual constraints into the JSON schema, avoiding hardcoded coordinates.
*   🕺 **State-Driven Animations**: Programmatic character selection and coordinate transformations (e.g., "sway" animations) executed dynamically based on inferred semantic sentiment and energy levels.
*   🎬 **Automated Overlays & Chroma Keying**: Algorithmic integration of timer artifacts and Call-To-Action (CTA) layers utilizing automated green-screen masking.

---

## 🚀 Production Deployments & Case Studies

This headless framework actively drives high-volume media rendering pipelines in production environments. Engineered for reliability, it serves as a highly stable, scalable engine capable of handling real-world traffic, audience engagement, and strict algorithmic formatting.

| Deployment Case | Channel Scale / Impact | Key Pipeline Features Demonstrated | Live Link |
| :--- | :--- | :--- | :--- |
| **High-Engagement Trivia Shorts Pipeline** | Active deployment on a verified 30K+ subscriber automated content channel | Automated voice conversion ducking, dynamic mood-based asset swapping, and word-level Whisper tracking | [FactZapTV on YouTube](https://www.youtube.com/@FactZapTV) |
| **[Placeholder Deployment]** | [Placeholder Scale / Impact] | [Placeholder Features] | [Placeholder Link] |
| **[Placeholder Deployment]** | [Placeholder Scale / Impact] | [Placeholder Features] | [Placeholder Link] |

---

## 📸 Sneak Peek

### The Visual Layout Editor

<div align="center">
  <img src="assets/docs/real_layout_editor_screenshot.png" alt="Visual Layout Editor Preview" width="800">
</div>

*The built-in web editor lets you drag, drop, and scale your character sprites, text, and overlays perfectly into a 9:16 vertical video frame.*

---

## 🛠️ Installation & Setup

### 1. Prerequisites
Ensure you have the following installed on your system:
*   [Docker](https://www.docker.com/products/docker-desktop)
*   [Docker Compose](https://docs.docker.com/compose/install/)
*   Git

### 2. Clone the Repository
```bash
git clone https://github.com/ZiggyMar/Youtube-Ai-Brainrot-Automation.git
cd Youtube-Ai-Brainrot-Automation
```

### 3. Configure Environment Variables
Copy the template to create your `.env` file (do not commit this file). Add your API keys:
```bash
cp .env.example .env
```
*(Note: The project uses a fallback system, so you only strictly need one valid key to start!)*

### 4. Build and Run via Docker
The entire environment (including FFmpeg and all Python dependencies) is containerized for zero-setup execution. Simply run:
```bash
docker-compose up --build
```
Your generated videos will appear automatically in your local `output/` folder!
---

## 🎨 Workflow Guide

### Step 1: Design Your Layout
1. Open `tools/layout_editor.html` in any modern web browser.
2. Drag and scale your visual elements (Character, Subtitles, Timer, CTA) on the canvas.
3. Fine-tune settings like font size in the properties panel.
4. Click **Export layout_config.json**.
5. Move the downloaded `layout_config.json` to the root of your project directory.

### Step 2: Run the Pipeline
Execute the pipeline to start generating videos:
```bash
docker-compose up
```

### What Happens Next?
1. **Scripting**: An AI agent writes a highly engaging trivia/quiz script.
2. **Audio Generation**: Text is converted to speech via Edge-TTS and passed through an RVC voice model for character voice cloning.
3. **Transcription**: Whisper maps out exact timestamps for every word spoken.
4. **Compositing**: FFmpeg dynamically composites the background, sprites, subtitles, and music.
5. **Output**: Your final, production-ready `.mp4` is saved in the `output/` directory!

---

## 📁 Project Architecture

```text
Youtube-Ai-Brainrot-Automation/
├── assets/                 # Backgrounds, music, fonts, character sprites, docs
├── audio_cache/            # Temp directory for TTS and Whisper outputs
├── core/                   # The engine: Director, Voicebox, Video Factory
├── data/                   # Generated scripts and stored layout configurations
├── gui/                    # (WIP) Future graphical user interface components
├── output/                 # Your final rendered viral videos live here
├── tools/                  # Visual layout editor and FFmpeg binaries
├── utils/                  # Helper scripts and utilities
├── .env.example            # Template for environment variables
└── requirements.txt        # Python package dependencies
```

---

## 🔐 Security Best Practices
*   **Never commit your `.env` file.** Ensure it remains in your `.gitignore`.
*   If you previously committed API keys by accident, please revoke those keys immediately via your provider's dashboard and use a tool like [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) to purge them from your git history.

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.

## 📚 References & Acknowledgments
*   [OpenAI Whisper](https://github.com/openai/whisper) for precise transcription.
*   [Edge-TTS](https://github.com/rany2/edge-tts) for reliable text-to-speech.
*   [Retrieval-based Voice Conversion (RVC)](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) for high-quality voice cloning.
