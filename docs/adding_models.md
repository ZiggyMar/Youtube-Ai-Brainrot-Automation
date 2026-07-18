# Adding Custom AI Models

The Multi-LLM Resiliency Engine is designed to be highly extensible. You can inject entirely new providers (like Anthropic Claude, OpenAI, or local instances like Ollama) into the fallback rotation.

## 1. Implement the Provider Interface

Locate the `core/llm/` directory. Create a new provider file (e.g., `claude_provider.py`). 
Your class should implement the `BaseLLMProvider` abstract class.

```python
from core.llm.base import BaseLLMProvider

class ClaudeProvider(BaseLLMProvider):
    def __init__(self, api_key):
        self.api_key = api_key
        # Initialize Anthropic client here

    def generate_script(self, prompt, schema):
        # 1. Make the API request
        # 2. Extract the response
        # 3. Validate against the JSON schema
        # 4. Return the parsed JSON object
        pass
```

## 2. Register the Provider in the Fallback Chain

Open the `core/llm/manager.py` file, which handles the orchestration.
Import your new provider and inject it into the fallback list.

```python
from core.llm.claude_provider import ClaudeProvider

def initialize_providers():
    providers = []
    
    # Add your custom provider
    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append(ClaudeProvider(os.getenv("ANTHROPIC_API_KEY")))
        
    # Append existing fallback providers
    if os.getenv("GEMINI_API_KEY"):
        providers.append(GeminiProvider(os.getenv("GEMINI_API_KEY")))
        
    return providers
```

## 3. Test the Integration

Run the pipeline with only your new provider's API key in your `.env` file to ensure the script generation and schema validation succeed without falling back to the defaults.
