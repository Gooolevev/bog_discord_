# Discord Bot — простой бот на discord.py

Минимальный рабочий Discord-бот на Python с нейронкой, надо брать с опенроутора свой API-ключ и закинуть в .env . Всё в одном файле `bot.py` — легко запустить и проверить.

## Структура

```
bot_discord/
├── bot.py              # весь бот: запуск, slash-команды, нейронка
├── requirements.txt    # зависимости
├── .env.example        # пример переменных окружения
└── .env                # токены (в git не попадает)
```

## Запуск

```bash
source venv/bin/activate.fish   # fish; в bash: source venv/bin/activate
cp .env.example .env            # вставь токен бота в .env
python bot.py
```

Если видишь `✅ Бот запущен: ...` — всё работает. Проверь в Discord: `/ping`.

## Команды (slash)

Все команды — через `/` (слэш-команды Discord), с меню автодополнения и описаниями:

| Команда | Описание |
|---------|----------|
| `/ping` | задержка бота |
| `/hello` | приветствие |
| `/roll [грани]` | кубик, по умолчанию d6 |
| `/coin` | монетка |
| `/choose варианты` | случайный выбор (через запятую) |
| `/server` | статус майнкрафт-сервера (айпи в `.env`, `MC_SERVER`) |
| `/ai вопрос` | вопрос к нейронке (OpenRouter → Pollinations) |

Упомяни бота в сообщении — ответит нейронкой; пустой пинг — пошлёт.

## Настройка в Discord Developer Portal

1. Создай приложение и бота: https://discord.com/developers/applications
2. В разделе **Bot** включи **MESSAGE CONTENT INTENT**
3. Пригласи бота на сервер (URL Generator, scope `bot`)
