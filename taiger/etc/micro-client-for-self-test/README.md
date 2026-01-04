# Telegram Micro-Client for Promo Mode Testing

This micro-client is designed to test the promo mode functionality of the @taiger_pro_bot using user session 7.

## Overview

The promo mode (second mode) of the project processes all incoming user messages through multiple AI models and returns the processed results. This micro-client allows testing this functionality directly from the console.

## Features

- **Automated Testing**: Send predefined test messages and analyze responses
- **Interactive Mode**: Manual testing with custom messages
- **Media Support**: Test with photo/video descriptions
- **Response Analysis**: Detailed logging of bot responses
- **Session Management**: Uses existing user session 7
- **S3 Session Loading**: Automatically loads Telegram sessions from S3 storage (Yandex Cloud)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

3. Required environment variables:
```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
SESSION_NAME=micro_client
BOT_USERNAME=@taiger_pro_bot
TEST_USER_ID=7
```

4. S3 Configuration (Optional):
For S3 session loading from Yandex Cloud:
```env
YC_ACCESS_KEY_ID=your_access_key
YC_SECRET_ACCESS_KEY=your_secret_key
BUCKET_NAME=your_bucket_name
YC_REGION=ru-central1
YC_ENDPOINT_URL=https://storage.yandexcloud.net
```

If S3 is not configured, the client will fall back to local session files.

## Usage

### Quick Test
```bash
python quick_test.py
```

### Full Interactive Testing
```bash
python micro_client.py
```

### Interactive Mode Commands
- Type your message and press Enter to send to bot
- Type `quit` to exit
- Messages are processed through all configured AI models

## Expected Behavior

In promo mode, the bot should:
1. Process each message through multiple AI models (configured in TEST_MODELS)
2. Send separate responses for each model
3. Include model ID in each response
4. Handle text, photo captions, and other media types

## Testing Scenarios

1. **Simple Text**: "Привет! Тестирую промо-режим бота."
2. **Media Description**: Text with emojis and descriptions
3. **Long Text**: Test message length limits
4. **Special Characters**: Test Unicode and special symbols

## Debugging

Check logs for:
- Bot connection status
- Message sending confirmation
- Response reception timing
- Error messages and stack traces

## Files

- `micro_client.py`: Main client implementation
- `quick_test.py`: Quick automated test
- `requirements.txt`: Dependencies
- `README.md`: This documentation