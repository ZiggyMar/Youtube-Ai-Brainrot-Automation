import os
from google import genai

# PASTE YOUR API KEY HERE
MY_API_KEY = "AIzaSyDubhc3fO4CG9e1KRk8NSk6-sRRgqCaox8"

client = genai.Client(api_key=MY_API_KEY)

print("🔍 Checking available models...")
try:
    with open("models.txt", "w", encoding="utf-8") as f:
        for m in client.models.list():
            f.write(f"{m.name} ({m.display_name})\n")
    print("✅ Models saved to models.txt")
except Exception as e:
    print(f"\n❌ Error: {e}")