# Система переключения языка

Этот документ описывает реализацию системы переключения языка между русским (ru) и английским (en) в Telegram Mini App (TMA) и Telegram боте.

## Обзор

Система переключения языка позволяет пользователям выбирать предпочитаемый язык интерфейса. Все настройки языка хранятся в базе данных в поле `users.language_code` с английским языком в качестве fallback.

## Архитектура

### База данных

Поле `language_code` в таблице `users`:
- Тип: String
- Значения: 'en', 'ru'
- По умолчанию: 'en'

### API эндпоинты

#### Получение языка пользователя
```http
GET /users/me/language
```
Возвращает текущий язык пользователя.

#### Установка языка пользователя
```http
POST /users/me/language
Content-Type: application/json

{
  "language_code": "en" | "ru"
}
```

### Telegram бот

#### Автоматическое определение языка
При первом запуске бот определяет язык пользователя:
1. Проверяет `language_code` из данных Telegram
2. Если язык поддерживается (en/ru), устанавливает его
3. Иначе устанавливает английский как fallback

#### Переключение языка в боте
- Команда `/profile` - отображает профиль с выбором языка
- Callback-кнопки для выбора языка
- Автоматическое обновление языка в базе данных

### Frontend (TMA)

#### Сервисы

**LanguageService** (`frontend/src/services/language.ts`)
- Управление языком пользователя
- API интеграция
- WebSocket поддержка

**LocalizationService** (`frontend/src/services/localization.ts`)
- Загрузка переводов
- Обработка ошибок и fallback
- Поддержка вложенных ключей

**LanguageSyncService** (`frontend/src/services/languageSync.ts`)
- Синхронизация языка между ботом и TMA
- Периодическая проверка изменений
- Обновление UI темы

#### Компоненты

**LanguageSelector** в `RedesignedHeader.vue`
- Выпадающий список выбора языка
- Автоматическое сохранение выбора
- Синхронизация с сервером

### Файлы переводов

#### Структура
```
frontend/src/locales/
├── en.json  # Английские переводы
└── ru.json  # Русские переводы
```

#### Формат
```json
{
  "dashboard": "Dashboard",
  "settings": {
    "language": "Language",
    "theme": "Theme"
  }
}
```

#### Использование в компонентах
```vue
<template>
  <div>{{ $t('dashboard') }}</div>
  <div>{{ $t('settings.language') }}</div>
</template>
```

## Реализация

### 1. API эндпоинты

```python
# api/users.py
@app.get("/users/me/language")
async def get_user_language(user: User = Depends(get_current_user)):
    return {"language_code": user.language_code or "en"}

@app.post("/users/me/language")
async def set_user_language(
    request: LanguageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user.language_code = request.language_code
    await db.commit()
    return {"language_code": user.language_code}
```

### 2. Бот языковая логика

```python
# telegram_bot/handlers.py
@dp.message(Command("profile"))
async def show_profile(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    lang = user.language_code or "en"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="English", callback_data=f"lang_en")],
        [InlineKeyboardButton(text="Русский", callback_data=f"lang_ru")]
    ])
    
    await message.answer("Выберите язык:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("lang_"))
async def change_language(callback: CallbackQuery):
    new_lang = callback.data.split("_")[1]
    user = await get_user_by_telegram_id(callback.from_user.id)
    user.language_code = new_lang
    await db.commit()
    
    await callback.answer(f"Язык изменен на {new_lang}")
```

### 3. Frontend сервисы

```typescript
// frontend/src/services/language.ts
export class LanguageService {
  async getUserLanguage(): Promise<string> {
    const response = await api.get('/users/me/language');
    return response.data.language_code || 'en';
  }
  
  async setUserLanguage(language: string): Promise<void> {
    await api.post('/users/me/language', { language_code: language });
  }
}
```

### 4. Локализация в компонентах

```typescript
// frontend/src/services/localization.ts
export class LocalizationService {
  t(key: string, params?: Record<string, any>): string {
    let translation = this.getTranslation(key);
    
    if (!translation) {
      return this.getFallbackTranslation(key);
    }
    
    if (params) {
      translation = this.replaceParams(translation, params);
    }
    
    return translation;
  }
}
```

## Обработка ошибок

### Fallback на английский
1. Если перевод не найден для текущего языка
2. Если файл переводов недоступен
3. Если язык пользователя не поддерживается
4. При любых ошибках загрузки переводов

### Валидация языка
- API принимает только 'en' и 'ru'
- Бот игнорирует неизвестные языки
- Frontend использует английский как fallback

## Синхронизация между ботом и TMA

### Механизм синхронизации
1. LanguageSyncService периодически проверяет изменения
2. WebSocket уведомления о смене языка
3. Автоматическое обновление UI при изменениях

### Периодическая проверка
```typescript
// Проверка каждые 30 секунд
setInterval(async () => {
  const serverLanguage = await this.languageService.getUserLanguage();
  const storedLanguage = localStorage.getItem('preferred_language');
  
  if (storedLanguage && storedLanguage !== serverLanguage) {
    await this.languageService.setUserLanguage(storedLanguage);
  }
}, 30000);
```

## Тестирование

### Запуск тестов
```bash
python test_language_switching.py
```

### Тесты покрывают
1. Создание пользователя с языком по умолчанию
2. Получение и установка языка пользователя
3. Fallback на английский при ошибках
4. Доступность файлов переводов
5. Автоматическое определение языка ботом

## Best Practices

### Для разработчиков

1. **Всегда использовать `$t()` для текстов**
   ```vue
   <!-- Правильно -->
   <div>{{ $t('common.save') }}</div>
   
   <!-- Неправильно -->
   <div>Save</div>
   ```

2. **Использовать вложенные ключи для группировки**
   ```json
   {
     "settings": {
       "language": "Language",
       "theme": "Theme",
       "notifications": "Notifications"
     }
   }
   ```

3. **Предоставлять fallback для параметров**
   ```typescript
   this.t('welcome_message', { name: user.name || 'User' })
   ```

4. **Тестировать с обоими языками**
   - Проверять отображение на русском и английском
   - Убеждаться в корректности длинных текстов
   - Проверять RTL языки (если будут добавлены)

### Для переводчиков

1. **Сохранять структуру JSON**
2. **Не изменять ключи**
3. **Учитывать контекст использования**
4. **Проверять длину текстов в интерфейсе**

## Миграция

### Существующие пользователи
- Все существующие пользователи получат английский язык по умолчанию
- При первом входе в бота язык будет определен автоматически
- В TMA язык можно будет изменить в настройках

### Новые пользователи
- Язык определяется автоматически из данных Telegram
- Fallback на английский при неизвестном языке
- Возможность изменения языка в профиле

## Future Enhancements

1. **Дополнительные языки**
   - Добавление поддержки других языков
   - Динамическая загрузка переводов

2. **Контекстная локализация**
   - Разные переводы в зависимости от контекста
   - Пользовательские шаблоны сообщений

3. **Административная панель**
   - Управление переводами через админку
   - Превью переводов в реальном времени

4. **Мультиязычные уведомления**
   - Отправка уведомлений на языке пользователя
   - Локализация email и push уведомлений