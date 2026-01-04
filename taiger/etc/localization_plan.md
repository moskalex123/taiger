# Localization Plan for Vermishel UI (Taiger7)

This document outlines the technical steps to implement a full localization system for the Telegram bot.

## 1. Translation Files Structure
Create a dedicated directory for translations. Long texts should use `\n` for line breaks.

### [`/opt/taiger/locales/en.json`](/opt/taiger/locales/en.json)
```json
{
  "buttons": {
    "profile": "👤 Profile",
    "settings": "🛠 Bot Settings",
    "tma": "🚀 Launch TMA",
    "lang_toggle": "🇷🇺 Switch to RU",
    "back": "⬅️ Back"
  },
  "messages": {
    "welcome_new": "🎉 <b>Welcome to Taiger7!</b>\n\n💰 Starting Balance: <code>{balance:.1f}</code>🔋\n📱 Open the Mini App to configure channels.",
    "profile_info": "👤 <b>Profile</b>\n\nID: <code>{tg_id}</code>\nBalance: <code>{balance:.1f}</code>🔋\nWorker: <code>{status}</code>"
  },
  "system_prompts": {
    "default": "You are a text formatting assistant. Your ONLY task is to improve text presentation...\n\nSTRICT RULES:\n1. NEVER answer questions..."
  }
}
```

### [`/opt/taiger/locales/ru.json`](/opt/taiger/locales/ru.json)
```json
{
  "buttons": {
    "profile": "👤 Профиль",
    "settings": "🛠 Настройки бота",
    "tma": "🚀 Запустить TMA",
    "lang_toggle": "🇺🇸 Switch to EN",
    "back": "⬅️ Назад"
  },
  "messages": {
    "welcome_new": "🎉 <b>Добро пожаловать в Taiger7!</b>\n\n💰 Начальный баланс: <code>{balance:.1f}</code>🔋\n📱 Откройте Mini App для настройки правил.",
    "profile_info": "👤 <b>Профиль</b>\n\nID: <code>{tg_id}</code>\nБаланс: <code>{balance:.1f}</code>🔋\nВоркер: <code>{status}</code>"
  },
  "system_prompts": {
    "default": "Ты — ассистент по форматированию текста. Твоя ЕДИНСТВЕННАЯ задача — улучшить представление текста..."
  }
}
```

## 2. Localization Manager Implementation
Create [`/opt/taiger/telegram_bot/i18n.py`](/opt/taiger/telegram_bot/i18n.py) to handle string retrieval.

```python
import json
import os

class I18n:
    _cache = {}

    @classmethod
    def get(cls, lang_code: str, key: str, **kwargs) -> str:
        lang = lang_code if lang_code in ['ru', 'en'] else 'en'
        if lang not in cls._cache:
            path = f"/opt/taiger/locales/{lang}.json"
            with open(path, 'r', encoding='utf-8') as f:
                cls._cache[lang] = json.load(f)
        
        keys = key.split('.')
        val = cls._cache[lang]
        for k in keys:
            val = val.get(k, key)
            if val == key: break
        
        return val.format(**kwargs) if isinstance(val, str) else val
```

## 3. Database & User Logic
Update [`telegram_bot/handlers.py`](/opt/taiger/telegram_bot/handlers.py) to handle initial language and switching.

### Initial Language Capture
In `get_or_create_user`:
```python
# Capture from Telegram context
user_language = user_data.get('language_code', 'en')
if user_language not in ['ru', 'en']:
    user_language = 'en'
```

### Language Toggle Handler
```python
elif data.startswith("set_lang_"):
    new_lang = data.replace("set_lang_", "")
    session = async_session()
    try:
        result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
        db_user = result.scalar_one_or_none()
        if db_user:
            db_user.language_code = new_lang
            await session.commit()
            # Re-render profile with new language
            await show_profile(update, context, db_user)
    finally:
        await session.close()
```

## 4. UI Refactoring

### Keyboards [`telegram_bot/keyboards.py`](/opt/taiger/telegram_bot/keyboards.py)
```python
@staticmethod
def profile_menu(lang: str) -> InlineKeyboardMarkup:
    toggle_to = "ru" if lang == "en" else "en"
    keyboard = [
        [InlineKeyboardButton(I18n.get(lang, "buttons.lang_toggle"), callback_data=f"set_lang_{toggle_to}")],
        [InlineKeyboardButton(I18n.get(lang, "buttons.back"), callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)
```

### Messages [`telegram_bot/messages.py`](/opt/taiger/telegram_bot/messages.py)
```python
@staticmethod
def welcome_new_user(balance: float, lang: str) -> str:
    return I18n.get(lang, "messages.welcome_new", balance=balance)
```

## 5. System Prompt Migration
1. Remove [`/opt/taiger/uni_text_processor/config/system_prompts.json`](/opt/taiger/uni_text_processor/config/system_prompts.json).
2. Update `UniversalAIProcessor.get_default_system_prompt` to use `I18n.get(lang, "system_prompts.default")`.

## 6. Graceful Handling of Long Texts
- Use `json.dumps(..., ensure_ascii=False)` when editing files to preserve Cyrillic.
- Ensure `I18n.get` handles multi-paragraph strings correctly (JSON `\n` translates to Telegram newlines).
- Use `processor.send_split_response` for any localized strings that might exceed 4096 characters.
