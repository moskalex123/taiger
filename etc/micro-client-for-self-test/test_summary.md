# Comprehensive Model Testing Report

## Test Overview
- **Total Test Texts Processed**: 10
- **Total Responses Collected**: 106
- **Successful Responses**: 92
- **Error Responses**: 14
- **Models That Responded**: 14

## Test Texts
1. "Завтра в нашем магазине скидка 20% на все."
2. "Ребята, какой ноутбук посоветуете для учебы? Бюджет до 50к."
3. "В общем, такая ситуация, пришел я сегодня на работу..."
4. "Чтобы настроить программу, вам нужно сначала открыть ее..."
5. "Митап по маркетингу в субботу, 15 числа..."
6. "Мы делаем сайты под ключ. Качественно и недорого..."
7. "ВАЩЕ КЛАССНАЯ АКЦИЯ У НАС ВСЕ ТОВАРЫ СО СКИДКОЙ 50 ПРОЦЕНТОВ..."
8. "Настоящим уведомляем о проведении технических работ..."
9. "Что вы думаете о новой функции?"
10. "Сегодня видел, как ворона каталась на скейте..."

## Models and Performance

### Fastest Models (Average Response Time)
1. **meta-llama/llama-3.3-8b-instruct:free**: 1.43s
2. **meta-llama/llama-4-maverick:free**: 2.22s
3. **mistralai/mistral-small-3.2-24b-instruct:free**: 7.25s
4. **meta-llama/llama-3.3-70b-instruct:free**: 7.27s
5. **mistralai/mistral-nemo:free**: 6.64s

### Slowest Models (Average Response Time)
1. **google/gemini-2.0-flash-exp:free**: 20.84s
2. **tngtech/deepseek-r1t2-chimera:free**: 17.63s
3. **minimax/minimax-m2:free**: 10.82s
4. **deepseek/deepseek-r1-distill-llama-70b:free**: 10.02s
5. **qwen/qwen3-30b-a3b:free**: 9.61s

## Responses per Test Text
- Text 1: 7 responses
- Text 2: 14 responses
- Text 3: 12 responses
- Text 4: 11 responses
- Text 5: 4 responses
- Text 6: 12 responses
- Text 7: 13 responses
- Text 8: 10 responses
- Text 9: 10 responses
- Text 10: 13 responses

## Error Analysis
- **Rate Limit Errors**: 14 responses (13.2% of total)
- **Affected Models**: 
  - deepseek/deepseek-chat-v3-0324:free
  - google/gemini-2.0-flash-exp:free

## Conclusion
The testing successfully processed all 10 methodology texts through the Telegram bot in test mode, collecting responses from 14 different AI models. The fastest models were the Llama 8B variants, while the slowest were the Gemini and DeepSeek models. Some rate limiting issues were observed with certain models, which is expected in a test environment with free-tier access.