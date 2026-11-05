# AGENTS.md — discord-bot

## О проекте
Discord-бот на Python (`discord.py` v2, async) для майнкрафт-сообщества: slash-команды, дерзкая нейронка (Pollinations, бесплатно), статус MC-сервера, автопостройка сервера.

## Структура
- `__main__.py` — точка входа: создание `commands.Bot`, список `COGS`, загрузка когов, синхронизация slash-команд в `on_ready`, ретраи подключения (сеть режет gateway).
- `bot/cogs/` — коги (модули команд):
  - `general.py` — /ping /hello /roll /coin /choose
  - `minecraft.py` — /server (mcstatus)
  - `ai.py` — /ai + listener `on_message` (упоминания → нейронка, пустой пинг → «Пошёл нахуй»)
  - `builder.py` — /построй (только админы): роли/категории/каналы из dataclass-конфигов
- `bot/utils/ai.py` — SYSTEM_PROMPT, SHORT_PERSONA, ROAST_COMEBACKS, `ask_pollinations` (лимит 1 ответ/45с на IP, парсинг «wait N seconds» из 402), `ask_ai` (отказ → роаст).

## Конвенции
- Код и комментарии — на русском.
- Команды — `@app_commands.command` внутри когов; описания параметров — `@app_commands.describe` (кириллица допустима).
- Каждый ког: класс `commands.Cog` + `async def setup(bot): await bot.add_cog(...)`.
- Новый ког добавлять в список `COGS` в `__main__.py`.
- Токены только из `.env` (`DISCORD_TOKEN`, `MC_SERVER`).

## Запуск
```bash
./venv/bin/python __main__.py
```
Проверка кода: `./venv/bin/ruff check .`
