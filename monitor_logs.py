#!/usr/bin/env python3
"""
Мониторинг логов воркера в реальном времени
"""

import time
import os
from datetime import datetime

def monitor_worker_logs(user_id: int):
    """Мониторинг логов воркера"""
    
    log_file = f"logs/worker_{user_id}_stderr.log"
    
    if not os.path.exists(log_file):
        print(f"❌ Лог файл {log_file} не найден")
        return
    
    print(f"🔍 Мониторинг логов воркера {user_id}")
    print(f"📁 Файл: {log_file}")
    print("=" * 60)
    print("⏰ Ожидание новых записей... (Ctrl+C для выхода)")
    print()
    
    # Получить текущий размер файла
    last_size = os.path.getsize(log_file)
    
    try:
        while True:
            current_size = os.path.getsize(log_file)
            
            if current_size > last_size:
                # Файл увеличился, читаем новые строки
                with open(log_file, 'r', encoding='utf-8') as f:
                    f.seek(last_size)
                    new_lines = f.read()
                    
                    if new_lines.strip():
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] {new_lines.strip()}")
                        print("-" * 40)
                
                last_size = current_size
            
            time.sleep(1)  # Проверяем каждую секунду
            
    except KeyboardInterrupt:
        print("\n👋 Мониторинг остановлен")

if __name__ == "__main__":
    user_id = 12  # ID пользователя
    monitor_worker_logs(user_id)