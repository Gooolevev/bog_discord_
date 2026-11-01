# Discord Bot — простой бот на discord.py

Минимальный рабочий Discord-бот на Python. Всё в одном файле `bot.py` — легко запустить и проверить.

## Структура

```
bot_discord/
├── bot.py              # весь бот: запуск и команды (!ping, !hello)
├── requirements.txt    # зависимости
├── .env.example        # пример переменных окружения
├── cogs/               # сюда потом можно вынести команды (модули)
├── utils/              # вспомогательные функции
├── data/               # JSON-файлы с данными
├── logs/               # логи
└── tests/              # тесты
```

## Запуск

```bash
source venv/bin/activate.fish   # fish; в bash: source venv/bin/activate
cp .env.example .env            # вставь токен бота в .env
python bot.py
```

Если видишь `✅ Бот запущен: ...` — всё работает. Проверь в Discord: `!ping`.

## Команды

| Команда | Описание |
|---------|----------|
| `!ping` | задержка бота |
| `!hello` | приветствие |
| `!roll [грани]` | кубик, по умолчанию d6 |
| `!coin` | монетка |
| `!choose а, б, в` | случайный выбор |
| `!server` | статус майнкрафт-сервера (айпи в `.env`, `MC_SERVER`) |
| `!ai вопрос` (алиасы `!нейро`, `!спроси`) | вопрос к нейронке (Pollinations.ai, без ключа) |

Упомяни бота в сообщении — ответит нейронкой; пустой пинг — пошлёт.

## Настройка в Discord Developer Portal

1. Создай приложение и бота: https://discord.com/developers/applications
2. В разделе **Bot** включи **MESSAGE CONTENT INTENT**
3. Пригласи бота на сервер (URL Generator, scope `bot`)

## Куда расти

Когда команд станет много, вынеси их в коги (`cogs/`):
создай `cogs/fun.py` с классом `commands.Cog` и загрузи его в `bot.py`
через `await bot.load_extension("cogs.fun")`.
