# План реализации сквозного переключения языка в TMA и боте

## Обзор
Необходимо реализовать систему сквозного переключения языка между русским (ru) и английским (en) в Telegram Mini App (TMA) и Telegram боте. Язык пользователя хранится в поле `users.language_code` в базе данных. По умолчанию используется английский язык при любых ошибках.

## Архитектура решения

### 1. База данных
- Поле `users.language_code` уже существует (согласно миграции `e8fc55773acd_add_language_code_to_users.py`)
- Значения: 'ru' или 'en'
- По умолчанию: 'en'

### 2. Определение начального языка
При первом запуске бота:
- Получить язык из окружения Telegram клиента
- Сохранить в `users.language_code`
- Использовать этот язык для всех последующих взаимодействий

### 3. Механизмы изменения языка
- **В боте**: Кнопка "Switch to RU"/"Switch to EN" в разделе "Профиль"
- **В TMA**: Селектор языка в шапке приложения

## Детальный план реализации

### Фаза 1: Backend API

#### 1.1 Обновление модели User
```python
# models.py
class User(Base):
    # ... существующие поля ...
    language_code = Column(String(2), default='en', nullable=False)
```

#### 1.2 API эндпоинты для языка
```python
# api/users.py
@router.get("/me/language")
async def get_user_language(current_user: User = Depends(get_current_user)):
    return {"language_code": current_user.language_code}

@router.put("/me/language")
async def update_user_language(
    language_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    language_code = language_data.get("language_code")
    if language_code not in ['ru', 'en']:
        raise HTTPException(status_code=400, detail="Invalid language code")
    
    current_user.language_code = language_code
    db.commit()
    return {"language_code": current_user.language_code}
```

### Фаза 2: Локализация в боте

#### 2.1 Определение языка при первом запуске
```python
# tg_worker.py или основной обработчик бота
async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = get_or_create_user(db, user.id, user.username)
    
    # Если язык не установлен, берем из Telegram клиента
    if not db_user.language_code or db_user.language_code == 'en':  # предполагаем, что по умолчанию пустое или 'en'
        # Получить язык из update
        language_code = update.effective_user.language_code or 'en'
        if language_code.startswith('ru'):
            db_user.language_code = 'ru'
        else:
            db_user.language_code = 'en'
        db.commit()
    
    # Отправить приветственное сообщение на нужном языке
    await send_localized_message(context, user.id, "welcome_message", db_user.language_code)
```

#### 2.2 Раздел профиля с переключателем языка
```python
# В обработчике профиля
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db_user = get_user_by_id(db, user_id)
    
    keyboard = [
        [InlineKeyboardButton(
            "Switch to RU" if db_user.language_code == 'en' else "Switch to EN",
            callback_data="switch_lang"
        )]
    ]
    
    text = get_localized_text("profile_text", db_user.language_code)
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_language_switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    db_user = get_user_by_id(db, user_id)
    
    new_lang = 'ru' if db_user.language_code == 'en' else 'en'
    db_user.language_code = new_lang
    db.commit()
    
    await query.answer(f"Language switched to {new_lang.upper()}")
    # Обновить сообщение профиля
    await show_profile(update, context)
```

### Фаза 3: Локализация в TMA

#### 3.1 Сервис для работы с языком
```typescript
// frontend/src/services/language.ts
export class LanguageService {
  private static instance: LanguageService;
  private currentLanguage: string = 'en';

  static getInstance(): LanguageService {
    if (!LanguageService.instance) {
      LanguageService.instance = new LanguageService();
    }
    return LanguageService.instance;
  }

  async getUserLanguage(): Promise<string> {
    try {
      const response = await api.get('/users/me/language');
      this.currentLanguage = response.data.language_code;
      return this.currentLanguage;
    } catch (error) {
      console.error('Failed to get user language:', error);
      return 'en'; // fallback
    }
  }

  async setUserLanguage(languageCode: string): Promise<void> {
    try {
      await api.put('/users/me/language', { language_code: languageCode });
      this.currentLanguage = languageCode;
    } catch (error) {
      console.error('Failed to set user language:', error);
      throw error;
    }
  }

  getCurrentLanguage(): string {
    return this.currentLanguage;
  }
}
```

#### 3.2 Компонент селектора языка в шапке
```vue
<!-- frontend/src/components/LanguageSelector.vue -->
<template>
  <div class="language-selector">
    <select v-model="selectedLanguage" @change="changeLanguage">
      <option value="en">EN</option>
      <option value="ru">RU</option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { LanguageService } from '@/services/language';

const languageService = LanguageService.getInstance();
const selectedLanguage = ref('en');

onMounted(async () => {
  selectedLanguage.value = await languageService.getUserLanguage();
});

const changeLanguage = async () => {
  try {
    await languageService.setUserLanguage(selectedLanguage.value);
    // Перезагрузить приложение или обновить все тексты
    window.location.reload();
  } catch (error) {
    console.error('Failed to change language:', error);
  }
};
</script>
```

#### 3.3 Интеграция селектора в главный компонент
```vue
<!-- frontend/src/App.vue -->
<template>
  <div id="app">
    <header>
      <LanguageSelector />
      <!-- остальной header -->
    </header>
    <main>
      <!-- основное содержимое -->
    </main>
  </div>
</template>

<script setup lang="ts">
import LanguageSelector from '@/components/LanguageSelector.vue';
// ...
</script>
```

### Фаза 4: Система локализации

#### 4.1 Файлы переводов
```json
// frontend/src/locales/en.json
{
  "welcome": "Welcome to Taiger!",
  "profile": "Profile",
  "switch_language": "Switch Language"
}
```

```json
// frontend/src/locales/ru.json
{
  "welcome": "Добро пожаловать в Taiger!",
  "profile": "Профиль",
  "switch_language": "Переключить язык"
}
```

#### 4.2 Сервис локализации
```typescript
// frontend/src/services/localization.ts
import en from '@/locales/en.json';
import ru from '@/locales/ru.json';

const translations = { en, ru };

export class LocalizationService {
  private static instance: LocalizationService;
  private currentLanguage: string = 'en';

  static getInstance(): LocalizationService {
    if (!LocalizationService.instance) {
      LocalizationService.instance = new LocalizationService();
    }
    return LocalizationService.instance;
  }

  setLanguage(language: string): void {
    this.currentLanguage = language;
  }

  t(key: string): string {
    const lang = translations[this.currentLanguage] || translations['en'];
    return lang[key] || key;
  }
}
```

#### 4.3 Использование в компонентах
```vue
<!-- Пример использования -->
<template>
  <div>
    <h1>{{ $t('welcome') }}</h1>
    <button>{{ $t('switch_language') }}</button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { LocalizationService } from '@/services/localization';
import { LanguageService } from '@/services/language';

const localization = LocalizationService.getInstance();
const language = LanguageService.getInstance();

const $t = (key: string) => localization.t(key);

// Синхронизация языка
language.getUserLanguage().then(lang => {
  localization.setLanguage(lang);
});
</script>
```

### Фаза 5: Синхронизация между ботом и TMA

#### 5.1 Обновление языка в реальном времени
```typescript
// frontend/src/services/language.ts
export class LanguageService {
  // ... существующие методы ...

  subscribeToLanguageChanges(callback: (language: string) => void): void {
    // Реализовать подписку на изменения языка
    // Можно использовать WebSocket или polling
  }
}
```

#### 5.2 Обработка ошибок и fallback
```python
# Везде где используется язык
def get_safe_language(user_language: str) -> str:
    return user_language if user_language in ['ru', 'en'] else 'en'
```
