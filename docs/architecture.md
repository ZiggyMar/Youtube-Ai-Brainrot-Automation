# Multi-Modal System Architecture

The Open-Source GenAI Video Rendering Framework handles the complex task of synchronizing text generation, text-to-speech, audio manipulation, and frame-by-frame video compositing. 

## 1. Multi-LLM Fallback System

Because cloud LLM providers can experience rate-limiting and downtime, our engine utilizes a structured Fallback Rotation mechanism. 

When a video script request is initiated:
1. **Primary Node:** The system queries the primary provider (e.g., Google Gemini).
2. **Schema Enforcement:** The response must strictly match the expected JSON schema (e.g., `[{"speaker": "A", "text": "...", "mood": "excited"}]`).
3. **Failover Execution:** If a timeout or schema validation failure occurs, the engine immediately switches to the secondary provider (e.g., Groq or Mistral) without interrupting the broader pipeline.

## 2. Frame-Perfect Whisper Synchronization

Subtitles are a critical engagement factor in short-form video. The framework achieves 0ms drift using OpenAI Whisper.

- **Transcription:** Once the TTS audio is generated, Whisper transcribes the file at the word level.
- **Timestamp Extraction:** Whisper outputs a raw metadata JSON containing exact start and end timestamps (`"word": "Hello", "start": 0.4, "end": 0.8`).
- **Compositing Matrix:** These timestamps are mapped directly into FFmpeg filter directives. Text overlays are rendered into the exact frames corresponding to the audio waveform.

## 3. Headless Audio-Ducking Logic

To achieve a professional audio mix automatically, the framework relies on dynamic audio-ducking.

- Background music volume is mapped to an FFmpeg `sidechaincompress` filter.
- The voiceover track (post-RVC conversion) acts as the control signal.
- Whenever speech is detected, the background track is automatically reduced ("ducked") in volume, and returns to normal when speech stops, ensuring clear vocal intelligibility without manual audio engineering.
