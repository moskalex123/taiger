#!/usr/bin/env python3
"""
Test script to verify keyboard localization
"""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, '/opt/taiger')

from telegram_bot.keyboards import BotKeyboards

def test_keyboard_localization():
    print("Testing keyboard localization...")
    
    # Test English keyboard
    print("\n--- Testing English keyboard ---")
    en_keyboard = BotKeyboards.profile_menu('en')
    print(f"English keyboard buttons: {[btn.text for row in en_keyboard.inline_keyboard for btn in row]}")
    
    en_reply_keyboard = BotKeyboards.reply_keyboard('en')
    print(f"English reply keyboard buttons: {[btn.text for row in en_reply_keyboard.keyboard for btn in row]}")
    
    # Test Russian keyboard
    print("\n--- Testing Russian keyboard ---")
    ru_keyboard = BotKeyboards.profile_menu('ru')
    print(f"Russian keyboard buttons: {[btn.text for row in ru_keyboard.inline_keyboard for btn in row]}")
    
    ru_reply_keyboard = BotKeyboards.reply_keyboard('ru')
    print(f"Russian reply keyboard buttons: {[btn.text for row in ru_reply_keyboard.keyboard for btn in row]}")
    
    print("\n--- Keyboard localization tests completed successfully! ---")

if __name__ == "__main__":
    test_keyboard_localization()