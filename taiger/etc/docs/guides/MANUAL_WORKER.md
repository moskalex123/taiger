# Руководство по ручному запуску воркера на VPS

Это руководство описывает как вручную запустить воркер для конкретного пользователя на VPS с автоматическим подтягиванием сессии из S3.

## 📋 Созданные файлы

1. **`run_worker_vps.ps1`** - PowerShell скрипт для запуска с локальной машины
2. **`run_worker_vps_manual.py`** - Python скрипт для запуска на VPS
3. **`start_worker_manual.sh`** - Bash скрипт для удобного запуска на VPS

## 🚀 Способы запуска

### Способ 1: Через PowerShell с локальной машины

```powershell
# Запуск с выводом логов в реальном времени
.\run_worker_vps.ps1 -UserId 1

# Запуск в режиме отладки
.\.\run_worker_vps.ps1 -UserId 1 -DebugMode

# Запуск в фоновом режиме (без логов)
.\run_worker_vps.ps1 -UserId 1 -NoLogs
```

### Способ 2: Прямо на VPS через SSH

```bash
# Подключаемся к VPS
ssh vps

# Переходим в директорию проекта
cd /opt/taiger

# Запускаем через bash скрипт
./start_worker_manual.sh 1

# Или с отладкой
./start_worker_manual.sh 1 debug

# Или напрямую через Python
python3 run_worker_vps_manual.py 1
python3 run_worker_vps_manual.py 1 --debug
```

### Способ 3: Одной командой с локальной машины

```powershell
# Запуск воркера для пользователя 1
ssh vps "cd /opt/taiger && ./start_worker_manual.sh 1"

# С отладкой
ssh vps "cd /opt/taiger && ./start_worker_manual.sh 1 debug"
```

## 🔧 Настройка окружения

### Необходимые переменные окружения на VPS:

```bash
# Telegram API
TELEGRAM_API_ID=21118124
TELEGRAM_API_HASH=491b6a7118ccbf3738bebc959ea14e4d

# AWS S3 для сессий
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
S3_BUCKET_NAME=your_bucket_name

# База данных
DATABASE_URL=postgresql://...
```

Эти переменные должны быть в файле `.env.prod` или `.env` на VPS.

## 📦 Как работает подтягивание сессии из S3

1. **Проверка локальной сессии**: Скрипт сначала проверяет есть ли файл `sessions/{user_id}.session` локально

2. **Загрузка из S3**: Если локальной сессии нет, загружает из S3 bucket

3. **Подключение к Telegram**: Использует сессию для подключения

4. **Сохранение обновлений**: После успешного подключения сохраняет обновленную сессию обратно в S3

5. **Финальное сохранение**: При завершении работы сохраняет финальное состояние сессии в S3

## 🔍 Диагностика проблем

### Проблема: "Сессия не найдена в S3"

```bash
# Проверяем содержимое S3 bucket
aws s3 ls s3://your-bucket-name/sessions/

# Загружаем сессию вручную (если есть локально)
aws s3 cp sessions/1.session s3://your-bucket-name/sessions/1.session
```

### Проблема: "AuthKeyUnregistered"

```bash
# Удаляем старую сессию
rm sessions/{user_id}.session
aws s3 rm s3://your-bucket-name/sessions/{user_id}.session

# Запускаем заново - будет создана новая сессия
./start_worker_manual.sh {user_id}
```

### Проблема: "Переменные окружения не найдены"

```bash
# Проверяем .env файл
cat .env.prod

# Загружаем переменные вручную
source .env.prod

# Или экспортируем
export $(cat .env.prod | grep -v '^#' | xargs)
```

## 📊 Мониторинг работы

### Просмотр логов в реальном времени:

```bash
# Если запущен через PowerShell скрипт в фоне
ssh vps 'tail -f /tmp/worker_{user_id}.log'

# Логи Docker контейнера
ssh vps 'cd /opt/taiger && docker-compose -f docker-compose.prod.yml logs -f app'
```

### Остановка воркера:

```bash
# Если запущен в фоне
ssh vps 'pkill -f "run_worker_vps_manual.py {user_id}"'

# Или по PID (если известен)
ssh vps 'kill {pid}'
```

## 🎯 Примеры использования

### Запуск для пользователя 1 с полными логами:

```powershell
.\run_worker_vps.ps1 -UserId 1
```

### Запуск в фоне для пользователя 15:

```powershell
.\run_worker_vps.ps1 -UserId 15 -NoLogs
```

### Отладка проблем для пользователя 12:

```bash
ssh vps "cd /opt/taiger && ./start_worker_manual.sh 12 debug"
```

## ⚠️ Важные замечания

1. **Один воркер на пользователя**: Не запускайте несколько воркеров для одного пользователя одновременно

2. **Сессии в S3**: Убедитесь что S3 bucket настроен и доступен

3. **Права доступа**: Файл `start_worker_manual.sh` должен быть исполняемым:
   ```bash
   chmod +x start_worker_manual.sh
   ```

4. **Переменные окружения**: Все необходимые переменные должны быть настроены в `.env.prod`

5. **SSH ключи**: Убедитесь что SSH подключение к VPS настроено (алиас `vps` в SSH config)

## 🔗 Связанные файлы

- `deploy.ps1` - Основной скрипт деплоя
- `run_worker_for_user.py` - Базовый скрипт запуска воркера
- `s3_session_manager.py` - Менеджер сессий S3
- `telegram_worker/worker.py` - Основной класс воркера