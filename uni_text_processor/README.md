# Universal AI Text Processor

A unified interface for processing text with multiple AI providers.

## Features

- Supports multiple AI providers (Hyperbolic, OpenRouter)
- Database-driven model configuration
- Provider-specific parameter handling
- Extensible architecture for adding new providers

## Supported Providers

1. **Hyperbolic** (Provider ID: 0)
   - Requires: temperature, top_p parameters
   - API endpoint: https://api.hyperbolic.xyz/v1/chat/completions

2. **OpenRouter** (Provider ID: 1)
   - Optional parameters: temperature, top_p
   - API endpoint: https://openrouter.ai/api/v1/chat/completions

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from uni_text_processor.universal_processor import UniversalAIProcessor

processor = UniversalAIProcessor()

# Process text with a specific model
result = await processor.process_text_with_model(
    system_content="You are a helpful assistant...",
    user_content="Hello, world!",
    model_id=1,
    model_name="meta-llama/Llama-3.3-70B-Instruct",
    provider_id=0,  # Hyperbolic
    temperature=0.7,
    top_p=0.9,
    max_tokens=500
)
```

## Testing

Run the test script to process text through all models in the database:

```bash
cd test
python test_processor.py
```

The test script will:
1. Read system and user content from text files
2. Fetch all models from the database
3. Process the text with each model
4. Output results in JSON format

## Environment Variables

- `HYPERBOLIC_API_KEY` - API key for Hyperbolic
- `OPENROUTER_API_KEY` - API key for OpenRouter
- Database configuration variables from .env