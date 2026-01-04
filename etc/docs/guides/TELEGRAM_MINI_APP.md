# Telegram Mini App Integration Setup Guide

## Overview

This guide walks through setting up the Telegram Mini App (TMA) integration for the taiger7 service, enabling users to access the service directly through Telegram with automatic authentication and worker controls.

## Prerequisites

1. **Telegram Bot**: Create a bot using [@BotFather](https://t.me/botfather)
2. **Domain**: HTTPS domain for webhook and Mini App hosting
3. **SSL Certificate**: Required for Telegram webhooks
4. **Existing taiger7 setup**: Working installation with database

## Step 1: Create Telegram Bot

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` command
3. Choose a name and username for your bot
4. Save the bot token provided by BotFather
5. Send `/setcommands` to BotFather and set these commands:
   ```
   start - Main dashboard and balance
   balance - Check current balance  
   worker - Worker control panel
   logs - View recent activity
   help - Show help message
   ```

## Step 2: Environment Configuration

Add these variables to your `.env` file:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/api/telegram/webhook
TELEGRAM_BOT_SECRET=your_secure_webhook_secret
TELEGRAM_WEBAPP_URL=https://yourdomain.com
DEFAULT_STARTING_BALANCE=1.0
```

## Step 3: Database Migration

Run the database migration to add language_code support:

```bash
# Apply the migration
alembic upgrade head
```

This adds the `language_code` column to support user language preferences from Telegram.

## Step 4: Install Dependencies

```bash
# Install new Python dependencies
pip install -r requirements.txt

# Install frontend dependencies (if not already done)
cd frontend && npm install
```

## Step 5: Configure Mini App with BotFather

1. Send `/setmenubutton` to [@BotFather](https://t.me/botfather)
2. Select your bot
3. Provide these details:
   - **Button text**: "Open App" or "📱 Open App"
   - **Web App URL**: `https://yourdomain.com`

## Step 6: Set Webhook

After deployment, set the webhook URL:

```bash
# Option 1: Use the API endpoint (recommended)
curl -X POST "https://yourdomain.com/api/telegram/set-webhook" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Option 2: Use Telegram Bot API directly
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourdomain.com/api/telegram/webhook",
    "secret_token": "your_webhook_secret"
  }'
```

## Step 7: Test the Integration

1. **Find your bot** on Telegram by username
2. **Send `/start`** - should show welcome message with inline keyboard
3. **Click "📱 Open Mini App"** - should open the web interface in Telegram
4. **Test authentication** - should automatically log in without credentials
5. **Test worker controls** - use bot commands or Mini App interface

## Step 8: Production Deployment

### Docker Deployment

The existing Dockerfile already includes the new dependencies. Just rebuild:

```bash
# Build new image
docker build -t taiger7:tma .

# Run with updated environment
docker run -d \
  --name taiger7-tma \
  -p 8000:8000 \
  --env-file .env \
  taiger7:tma
```

### Manual Deployment

```bash
# Update dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Build frontend
cd frontend && npm run build

# Start server
python main.py
```

## Security Considerations

1. **Webhook Secret**: Always use `TELEGRAM_BOT_SECRET` in production
2. **HTTPS Only**: Telegram requires HTTPS for webhooks and Mini Apps
3. **JWT Security**: Ensure `JWT_SECRET_KEY` is secure and unique
4. **Bot Token**: Keep `TELEGRAM_BOT_TOKEN` secure and never expose it

## API Endpoints

The integration adds these new endpoints:

- `POST /api/telegram/webhook` - Telegram webhook handler
- `POST /api/telegram/auth` - TMA authentication
- `GET /api/telegram/user` - Get current TMA user
- `POST /api/telegram/set-webhook` - Set webhook URL
- `DELETE /api/telegram/webhook` - Remove webhook
- `GET /api/telegram/bot-info` - Get bot information

## Troubleshooting

### Bot Not Responding
- Check `TELEGRAM_BOT_TOKEN` is correct
- Verify webhook is set correctly: `/api/telegram/set-webhook`
- Check server logs for webhook processing errors

### Mini App Not Loading
- Ensure `TELEGRAM_WEBAPP_URL` points to your domain
- Verify HTTPS certificate is valid
- Check that frontend builds include TMA styles

### Authentication Failing
- Verify `TELEGRAM_BOT_TOKEN` matches the bot used for WebApp
- Check that init data validation is working
- Ensure system time is synchronized (±5 minutes tolerance)

### Worker Controls Not Working
- Check database connectivity
- Verify worker manager integration
- Test worker API endpoints directly

## Features Available

### Bot Commands
- `/start` - Dashboard with balance and recent activity
- `/balance` - Quick balance check with top-up options
- `/worker` - Worker start/stop/status controls
- `/logs` - Recent activity logs (last 10 entries)
- `/help` - Available commands and Mini App info

### Mini App Features
- **Auto-authentication** via Telegram credentials
- **Full web interface** with responsive mobile design
- **Worker controls** via Telegram Main Button
- **Balance management** with Telegram theme integration
- **Real-time updates** via existing WebSocket connection

### New User Flow
1. User discovers bot via link or search
2. `/start` creates account with default balance
3. Mini App provides full configuration interface
4. Worker can be controlled via bot or Mini App

## Monitoring

Monitor the integration through:

1. **Server logs** - webhook processing and authentication
2. **Database** - new user registrations via `created_via` field
3. **Bot analytics** - available through [@BotFather](https://t.me/botfather)
4. **Health check** - `/health` endpoint includes Telegram status

## Next Steps

After successful deployment:

1. **User onboarding** - Share bot link with existing users
2. **Documentation** - Update user guides with Telegram access
3. **Analytics** - Monitor TMA usage vs web interface
4. **Features** - Consider additional Telegram-specific features
5. **Support** - Handle user questions about Telegram access

## Support

For issues with this integration:

1. Check server logs in `/app/logs`
2. Verify all environment variables are set
3. Test webhook with Telegram's webhook test tools
4. Check database for user creation and authentication logs