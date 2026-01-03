#!/bin/bash

echo "🔐 Настройка SSL сертификатов для taiger.pro..."

# Устанавливаем certbot если не установлен
if ! command -v certbot &> /dev/null; then
    echo "📦 Устанавливаем certbot..."
    apt update
    apt install -y certbot python3-certbot-nginx
fi

# Останавливаем nginx если запущен
systemctl stop nginx 2>/dev/null || true

# Получаем SSL сертификат
echo "🔑 Получаем SSL сертификат для taiger.pro..."
certbot certonly --standalone \
    --email admin@taiger.pro \
    --agree-tos \
    --no-eff-email \
    -d taiger.pro \
    -d www.taiger.pro

if [ $? -eq 0 ]; then
    echo "✅ SSL сертификат успешно получен!"
    
    # Настраиваем автообновление
    echo "⚙️ Настраиваем автообновление сертификата..."
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --deploy-hook 'systemctl restart nginx'") | crontab -
    
    echo "🎉 SSL настроен успешно!"
else
    echo "❌ Ошибка получения SSL сертификата"
    exit 1
fi