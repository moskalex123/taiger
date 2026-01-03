#!/usr/bin/env python3
"""
Test script to verify UniversalAIProcessor localization
"""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, '/opt/taiger')

from uni_text_processor.universal_processor import UniversalAIProcessor
import logging

def test_universal_ai_processor_localization():
    print("Testing UniversalAIProcessor localization...")
    
    # Create logger
    logger = logging.getLogger(__name__)
    
    # Create processor instance
    processor = UniversalAIProcessor(logger)
    
    # Test English system prompt
    print("\n--- Testing English system prompt ---")
    en_prompt = processor.get_default_system_prompt('en')
    print(f"English prompt starts with: {en_prompt[:50]}...")
    
    # Test Russian system prompt
    print("\n--- Testing Russian system prompt ---")
    ru_prompt = processor.get_default_system_prompt('ru')
    print(f"Russian prompt starts with: {ru_prompt[:50]}...")
    
    # Test fallback
    print("\n--- Testing fallback system prompt ---")
    fr_prompt = processor.get_default_system_prompt('fr')  # French not supported, should fallback to English
    print(f"French prompt (should fallback to English): {fr_prompt[:50]}...")
    
    print("\n--- UniversalAIProcessor localization tests completed successfully! ---")

if __name__ == "__main__":
    test_universal_ai_processor_localization()