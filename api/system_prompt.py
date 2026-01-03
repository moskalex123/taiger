from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import sys
from pathlib import Path

# Add uni_text_processor to path
sys.path.append(str(Path(__file__).parent.parent / 'uni_text_processor'))

from uni_text_processor.universal_processor import UniversalAIProcessor
import logging

router = APIRouter()

# Initialize processor
processor = UniversalAIProcessor()

@router.get("/default-system-prompt")
async def get_default_system_prompt(language: str = "en"):
    """
    Get the default system prompt from project settings.
    
    Args:
        language: Language code (default: "en")
        
    Returns:
        Dictionary with system prompt
    """
    try:
        prompt = processor.get_default_system_prompt(language)
        return {
            "system_prompt": prompt,
            "language": language
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting system prompt: {str(e)}")

@router.get("/supported-languages")
async def get_supported_languages():
    """
    Get list of supported languages for system prompts.
    
    Returns:
        Dictionary with supported languages
    """
    # For now, we support English and Russian
    return {
        "supported_languages": ["en", "ru"]
    }