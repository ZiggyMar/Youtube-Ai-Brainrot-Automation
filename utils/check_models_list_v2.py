from google import genai
import os

MY_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyDubhc3fO4CG9e1KRk8NSk6-sRRgqCaox8")
client = genai.Client(api_key=MY_API_KEY)

for model in client.models.list():
    print(model.name)
