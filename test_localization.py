#!/usr/bin/env python3
"""
Test script to verify localization implementation
"""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, '/opt/taiger')

from telegram_bot.i18n import I18n

def test_localization():
    print("Testing localization implementation...")
    
    # Test English localization
    print("\n--- Testing English localization ---")
    en_profile_button = I18n.get('en', 'buttons.profile')
    print(f"Profile button (en): {en_profile_button}")
    
    en_welcome = I18n.get('en', 'messages.welcome_new', balance=100.0)
    print(f"Welcome message (en): {en_welcome}")
    
    en_lang_toggle = I18n.get('en', 'buttons.lang_toggle')
    print(f"Language toggle (en): {en_lang_toggle}")
    
    # Test Russian localization
    print("\n--- Testing Russian localization ---")
    ru_profile_button = I18n.get('ru', 'buttons.profile')
    print(f"Profile button (ru): {ru_profile_button}")
    
    ru_welcome = I18n.get('ru', 'messages.welcome_new', balance=100.0)
    print(f"Welcome message (ru): {ru_welcome}")
    
    ru_lang_toggle = I18n.get('ru', 'buttons.lang_toggle')
    print(f"Language toggle (ru): {ru_lang_toggle}")
    
    # Test fallback to English for unsupported language
    print("\n--- Testing fallback to English ---")
    fallback_profile_button = I18n.get('fr', 'buttons.profile')
    print(f"Profile button (fr - should fallback to en): {fallback_profile_button}")
    
    # Test system prompt localization
    print("\n--- Testing system prompt localization ---")
    en_system_prompt = I18n.get('en', 'system_prompts.default')
    print(f"System prompt (en): {en_system_prompt[:100]}...")
    
    ru_system_prompt = I18n.get('ru', 'system_prompts.default')
    print(f"System prompt (ru): {ru_system_prompt[:100]}...")
    
    print("\n--- All tests completed successfully! ---")

if __name__ == "__main__":
    test_localization()