#!/usr/bin/env python3
"""
Скрипт для получения chat_id из Telegram бота.
Запустите этот скрипт и отправьте любое сообщение боту @taiger_pro_bot
"""

import asyncio
import aiohttp
import os
import json

async def get_chat_id():
    """Получить chat_id из обновлений бота"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        return None
    
    print(f"🔑 Используем bot token: {bot_token[:10]}...")
    print("📱 Отправьте любое сообщение боту @taiger_pro_bot и нажмите Enter...")
    input("Нажмите Enter после отправки сообщения боту...")
    
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('ok'):
                    updates = data.get('result', [])
                    print(f"📊 Найдено {len(updates)} обновлений")
                    
                    if updates:
                        print("\n📝 Последние обновления:")
                        for update in updates[-5:]:  # Показываем последние 5
                            if 'message' in update:
                                message = update['message']
                                chat_id = message.get('chat', {}).get('id')
                                from_user = message.get('from', {})
                                text = message.get('text', '')
                                
                                print(f"   Chat ID: {chat_id}")
                                print(f"   От: {from_user.get('first_name', '')} {from_user.get('last_name', '')} (@{from_user.get('username', 'нет')})")
                                print(f"   Текст: {text}")
                                print(f"   ---")
                        
                        # Берем chat_id из последнего сообщения
                        last_message = updates[-1]
                        if 'message' in last_message:
                            chat_id = last_message['message'].get('chat', {}).get('id')
                            print(f"\n✅ Найден Chat ID: {chat_id}")
                            return chat_id
                    else:
                        print("❌ Обновлений не найдено. Убедитесь, что вы отправили сообщение боту.")
                        return None
                else:
                    print(f"❌ Telegram API error: {data.get('description')}")
                    return None
            else:
                print(f"❌ HTTP error: {response.status}")
                return None

if __name__ == "__main__":
    chat_id = asyncio.run(get_chat_id())
    if chat_id:
        print(f"\n🎉 Добавьте эту строку в ваш .env файл:")
        print(f"TELEGRAM_CHAT_ID={chat_id}")