# Universal AI Text Processor Configuration System

## Overview

This document describes the new shared configuration system for the Universal AI Text Processor that integrates with the existing localization system and provides pre-filled forms for advanced users.

## Key Features

1. **Shared Configuration File**: System prompts are stored in a centralized JSON configuration file
2. **Localization Integration**: Supports multiple languages with automatic fallback
3. **Form Pre-filling**: Automatically pre-fills forms for advanced users
4. **Backward Compatibility**: Maintains compatibility with existing code
5. **Flexible Testing**: Allows testing with different system content files

## Configuration Structure

The system uses a JSON configuration file located at:
```
uni_text_processor/config/system_prompts.json
```

### File Format

```json
{
  "default": {
    "en": "English system prompt content...",
    "ru": "Russian system prompt content..."
  }
}
```

## Integration with Localization System

The configuration system automatically detects the user's preferred language and loads the appropriate system prompt:

1. **Automatic Detection**: The system first tries to load the prompt for the requested language
2. **Fallback Mechanism**: If the requested language is not available, it falls back to English
3. **Hardcoded Backup**: If the configuration file is missing or corrupted, it uses the hardcoded default

## Pre-filled Forms for Advanced Users

In advanced user forms, the system automatically pre-fills:

1. **System Prompt**: Based on user's language preference
2. **Model Parameters**: With sensible defaults (temperature=0.7, top_p=0.9, max_tokens=500)
3. **Language Selection**: Automatically selected based on user's preference

This is implemented in the `get_default_system_prompt(language)` method of the `UniversalAIProcessor` class.

## Backward Compatibility

The system maintains full backward compatibility:

- Existing code using `processor.get_default_system_prompt()` continues to work without changes
- The [system_content_to_test_AI.txt](file:///opt/taiger/uni_text_processor/test/system_content_to_test_AI.txt) file is still used by the full tester for custom testing
- Hardcoded defaults serve as fallbacks when configuration files are missing

## Adding New Languages

To add support for a new language:

1. Edit `uni_text_processor/config/system_prompts.json`
2. Add a new entry under the "default" section with the language code as key
3. Provide the translated system prompt as the value

Example:
```json
{
  "default": {
    "en": "English content...",
    "ru": "Russian content...",
    "fr": "French content..."  // New language
  }
}
```

## Testing

The full test suite verifies the configuration system:

1. **Integration Testing**: The full_test.py script uses the configuration system
2. **Language Testing**: Verifies correct loading of different language prompts
3. **Fallback Testing**: Ensures proper fallback behavior for unsupported languages

The [system_content_to_test_AI.txt](file:///opt/taiger/uni_text_processor/test/system_content_to_test_AI.txt) file remains for custom testing scenarios where users want to test with different system content.

## Implementation Details

### UniversalAIProcessor Class

The `UniversalAIProcessor` class has been updated with:

1. **Configuration Loading**: `_load_default_system_prompt(language)` method
2. **Caching**: Caches loaded prompts for performance
3. **Error Handling**: Graceful fallback to hardcoded defaults
4. **Multilingual Support**: Supports multiple languages with fallback

### File Structure

```
uni_text_processor/
├── config/
│   └── system_prompts.json     # Shared configuration file
├── universal_processor.py      # Updated processor with config support
└── test/
    ├── full_test.py            # Full test script (unchanged)
    ├── system_content_to_test_AI.txt  # Custom test content (preserved)
    └── user_content_to_test_AI.txt    # User test content (preserved)
```

## Usage Examples

### Basic Usage
```python
from uni_text_processor.universal_processor import UniversalAIProcessor

processor = UniversalAIProcessor()
# Get English prompt (default)
english_prompt = processor.get_default_system_prompt()
# Get Russian prompt
russian_prompt = processor.get_default_system_prompt("ru")
```

### In Forms (Advanced Users)
```python
# Pre-fill form with user's preferred language
def prefill_form(user_language="en"):
    processor = UniversalAIProcessor()
    system_prompt = processor.get_default_system_prompt(user_language)
    return {
        "system_prompt": system_prompt,
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 500
    }
```

## Benefits

1. **Centralized Management**: All system prompts in one place
2. **Easy Localization**: Simple to add new languages
3. **Flexible Testing**: Supports both default and custom testing scenarios
4. **Performance**: Caching reduces file I/O
5. **Reliability**: Multiple fallback mechanisms
6. **Maintainability**: Clear separation of configuration and code