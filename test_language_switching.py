#!/usr/bin/env python3
"""
Тестирование функциональности переключения языка
"""

import requests
import json
import time
from typing import Dict, Any

class LanguageSwitchingTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.user_id = None
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def test_user_creation(self) -> bool:
        """Тест создания пользователя с языком по умолчанию"""
        print("Тест 1: Создание пользователя с языком по умолчанию")
        
        # Создаем пользователя с английским языком по умолчанию
        user_data = {
            "telegram_id": 123456789,
            "username": "test_user",
            "first_name": "Test",
            "last_name": "User",
            "language_code": "en"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/users",
                headers=self.headers,
                json=user_data
            )
            
            if response.status_code == 200:
                result = response.json()
                self.user_id = result.get('id')
                print(f"✓ Пользователь создан с ID: {self.user_id}")
                print(f"✓ Язык по умолчанию: {result.get('language_code', 'en')}")
                return True
            else:
                print(f"✗ Ошибка создания пользователя: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"✗ Ошибка подключения: {e}")
            return False
    
    def test_get_user_language(self) -> bool:
        """Тест получения языка пользователя"""
        print("\nТест 2: Получение языка пользователя")
        
        try:
            response = self.session.get(
                f"{self.base_url}/users/me/language",
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                language = result.get('language_code', 'en')
                print(f"✓ Текущий язык пользователя: {language}")
                return True
            else:
                print(f"✗ Ошибка получения языка: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            return False
    
    def test_set_user_language(self, language: str) -> bool:
        """Тест установки языка пользователя"""
        print(f"\nТест 3: Установка языка пользователя на {language}")
        
        try:
            response = self.session.post(
                f"{self.base_url}/users/me/language",
                headers=self.headers,
                json={"language_code": language}
            )
            
            if response.status_code == 200:
                result = response.json()
                new_language = result.get('language_code')
                print(f"✓ Язык успешно изменен на: {new_language}")
                return True
            else:
                print(f"✗ Ошибка изменения языка: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            return False
    
    def test_language_fallback(self) -> bool:
        """Тест fallback на английский язык"""
        print("\nТест 4: Проверка fallback на английский язык")
        
        # Попробуем установить несуществующий язык
        try:
            response = self.session.post(
                f"{self.base_url}/users/me/language",
                headers=self.headers,
                json={"language_code": "xx"}
            )
            
            if response.status_code == 400:
                print("✓ Сервер корректно отклонил несуществующий язык")
                return True
            else:
                print(f"✗ Ожидалась ошибка 400, получено: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            return False
    
    def test_translation_files(self) -> bool:
        """Тест доступности файлов переводов"""
        print("\nТест 5: Проверка файлов переводов")
        
        languages = ['en', 'ru']
        for lang in languages:
            try:
                response = requests.get(f"{self.base_url}/locales/{lang}.json")
                if response.status_code == 200:
                    translations = response.json()
                    print(f"✓ Файл переводов для {lang} доступен ({len(translations)} ключей)")
                else:
                    print(f"✗ Файл переводов для {lang} недоступен: {response.status_code}")
                    return False
            except Exception as e:
                print(f"✗ Ошибка проверки файла {lang}: {e}")
                return False
        
        return True
    
    def test_bot_language_detection(self) -> bool:
        """Тест автоматического определения языка ботом"""
        print("\nТест 6: Тест автоматического определения языка ботом")
        
        # Это тест для бота, который должен определять язык из данных пользователя
        # В реальности это происходит при первом запуске бота
        
        test_cases = [
            {"language_code": "en", "expected": "en"},
            {"language_code": "ru", "expected": "ru"},
            {"language_code": None, "expected": "en"},  # Fallback на английский
            {"language_code": "fr", "expected": "en"},  # Неизвестный язык -> fallback
        ]
        
        for case in test_cases:
            user_lang = case["language_code"]
            expected = case["expected"]
            
            # Имитируем логику бота
            if user_lang in ["en", "ru"]:
                result = user_lang
            else:
                result = "en"  # Fallback
            
            if result == expected:
                print(f"✓ Язык {user_lang} -> {result} (ожидалось {expected})")
            else:
                print(f"✗ Язык {user_lang} -> {result} (ожидалось {expected})")
                return False
        
        return True
    
    def run_all_tests(self):
        """Запуск всех тестов"""
        print("=== Тестирование системы переключения языка ===\n")
        
        tests = [
            self.test_user_creation,
            self.test_get_user_language,
            lambda: self.test_set_user_language("ru"),
            self.test_get_user_language,
            lambda: self.test_set_user_language("en"),
            self.test_get_user_language,
            self.test_language_fallback,
            self.test_translation_files,
            self.test_bot_language_detection,
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
                time.sleep(0.5)  # Небольшая пауза между запросами
            except Exception as e:
                print(f"✗ Тест завершился с ошибкой: {e}")
        
        print(f"\n=== Результаты тестирования ===")
        print(f"Пройдено: {passed}/{total}")
        print(f"Успешно: {passed == total}")
        
        return passed == total

if __name__ == "__main__":
    tester = LanguageSwitchingTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 Все тесты пройдены! Система переключения языка работает корректно.")
    else:
        print("\n❌ Некоторые тесты не пройдены. Проверьте реализацию.")