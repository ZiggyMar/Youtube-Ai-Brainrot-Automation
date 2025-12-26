import os
import sys
from google import genai
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

MY_API_KEY = os.environ.get("GEMINI_API_KEY")
if not MY_API_KEY:
    print("❌ Error: GEMINI_API_KEY not found in environment variables.")
    sys.exit(1)

client = genai.Client(api_key=MY_API_KEY)

print("🔍 Checking available models...")
try:
    with open("models.txt", "w", encoding="utf-8") as f:
        for m in client.models.list():
            f.write(f"{m.name} ({m.display_name})\n")
    print("✅ Models saved to models.txt")
except Exception as e:
    print(f"\n❌ Error: {e}")