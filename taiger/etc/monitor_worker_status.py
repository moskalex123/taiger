#!/usr/bin/env python3
"""
Мониторинг статуса воркеров в реальном времени
"""

import asyncio
import requests
import time
from datetime import datetime

async def monitor_worker_status():
    """Мониторинг статуса воркеров"""
    print("=== МОНИТОРИНГ СТАТУСА ВОРКЕРОВ ===")
    print("Запустите воркер через интерфейс и наблюдайте за изменениями...")
    print("Нажмите Ctrl+C для остановки\n")
    
    previous_status = None
    
    try:
        while True:
            try:
                # Получаем статус сервиса
                response = requests.get("http://localhost:8000/api/queue/service-status", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    
                    current_status = {
                        'active': len(data['active_workers']),
                        'starting': len(data['starting_workers']),
                        'queue': len(data['queue']),
                        'active_list': data['active_workers'],
                        'starting_list': data['starting_workers'],
                        'queue_list': data['queue']
                    }
                    
                    # Показываем изменения
                    if current_status != previous_status:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] ИЗМЕНЕНИЕ СТАТУСА:")
                        print(f"  📊 Активных: {current_status['active']} {current_status['active_list']}")
                        print(f"  🔄 Запускающихся: {current_status['starting']} {current_status['starting_list']}")
                        print(f"  ⏳ В очереди: {current_status['queue']} {current_status['queue_list']}")
                        
                        if data.get('worker_vips'):
                            print(f"  🎖️ VIP уровни: {data['worker_vips']}")
                        
                        print()
                        previous_status = current_status
                    
                else:
                    print(f"❌ Ошибка API: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Ошибка запроса: {e}")
            
            await asyncio.sleep(2)  # Проверяем каждые 2 секунды
            
    except KeyboardInterrupt:
        print("\n✅ Мониторинг остановлен")

if __name__ == "__main__":
    asyncio.run(monitor_worker_status())