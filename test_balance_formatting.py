#!/usr/bin/env python3
"""
Test script to verify balance formatting is working correctly.
"""

import sys
sys.path.append('/opt/taiger')

from telegram_bot.handlers import format_balance

def test_format_balance():
    """Test the format_balance function"""
    print("🧪 Testing balance formatting function...")

    test_cases = [
        (64.99999999999997, "65"),  # Should round to 65
        (65.0, "65"),              # Should show as 65
        (65.5, "65.5"),            # Should show as 65.5
        (65.55, "65.5"),           # Should round to 65.5 (correct rounding)
        (65.555, "65.6"),          # Should round to 65.6
        (0.0, "0"),                # Should show as 0
        (0.5, "0.5"),              # Should show as 0.5
        (1.234, "1.2"),            # Should round to 1.2
        (99.99, "100"),            # Should round to 100
        (100.0, "100"),            # Should show as 100
        (100.1, "100.1"),          # Should show as 100.1
    ]

    all_passed = True

    for value, expected in test_cases:
        result = format_balance(value)
        if result == expected:
            print(f"   ✅ {value} -> {result} (expected: {expected})")
        else:
            print(f"   ❌ {value} -> {result} (expected: {expected})")
            all_passed = False

    if all_passed:
        print("✅ All formatting tests PASSED!")
        return True
    else:
        print("❌ Some formatting tests FAILED!")
        return False

if __name__ == "__main__":
    success = test_format_balance()
    sys.exit(0 if success else 1)