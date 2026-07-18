import os

def patch_main():
    path = "core/main.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    target = 'def main():\n    """\n    Entry point for sequential manual testing of the video pipeline.\n    Generates a batch of videos back-to-back.\n    """\n    # Number of videos to generate in sequence'
    
    replacement = '''def check_environment():
    """Validates that at least one required API key is present."""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
    
    keys = ["GEMINI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY", "OPENROUTER_API_KEY"]
    if not any(os.environ.get(k) and os.environ.get(k).strip() for k in keys):
        print("\\n\\u274c CRITICAL CONFIGURATION ERROR \\u274c")
        print("No valid LLM API keys were found in your environment.")
        print("Please copy '.env.example' to '.env' and add at least one API key.")
        print("Example:")
        print("  cp .env.example .env")
        print("  nano .env\\n")
        import sys
        sys.exit(1)

def main():
    """
    Entry point for sequential manual testing of the video pipeline.
    Generates a batch of videos back-to-back.
    """
    check_environment()
    
    # Number of videos to generate in sequence'''
    
    content = content.replace(target, replacement)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
        
def patch_director():
    path = "core/director.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Patch Gemini
    content = content.replace('print(f"\\u26a0\\ufe0f Gemini Key #{i+1} Failed: {e}")',
                              'print(f"\\u26a0\\ufe0f [LLM FALLBACK] Gemini Key #{i+1} failed or is invalid/revoked: {e}")')
    
    # Patch Groq
    content = content.replace('print(f"\\u26a0\\ufe0f Groq Failed: {e}")',
                              'print(f"\\u26a0\\ufe0f [LLM FALLBACK] Groq request failed (check if key is invalid/revoked): {e}")')
                              
    # Patch Mistral
    content = content.replace('print(f"\\u26a0\\ufe0f Mistral Failed: {e}")',
                              'print(f"\\u26a0\\ufe0f [LLM FALLBACK] Mistral request failed (check if key is invalid/revoked): {e}")')
                              
    # Patch OpenRouter
    content = content.replace('print(f"\\u26a0\\ufe0f OpenRouter Failed: {e}")',
                              'print(f"\\u26a0\\ufe0f [LLM FALLBACK] OpenRouter request failed (check if key is invalid/revoked): {e}")')
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    patch_main()
    patch_director()
    print("Patching successful.")
