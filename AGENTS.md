# AGENTS.md — discord-bot

## О проекте
Простой Discord-бот на Python (`discord.py` v2, async). Весь бот сейчас в `bot.py` — намеренно минимальный, для проверки работы.

## Структура
- `bot.py` — точка входа и все команды (префикс `!`).
- `cogs/`, `utils/`, `data/`, `logs/`, `tests/` — пустые пакеты для будущего роста (коги, хелперы, JSON-хранилища, логи, тесты).

## Конвенции
- Код и комментарии — на русском языке.
- Команды — через `@bot.command()` с докстрингом (он показывается в справке).
- Токен только из `.env` (`DISCORD_TOKEN`), см. `.env.example`.

## Когда команд станет много
Вынести их в коги: `cogs/<имя>.py` (класс `commands.Cog` + `async def setup(bot)`),
загрузка через `await bot.load_extension("cogs.<имя>")` в `setup_hook`.

## Запуск
```bash
source venv/bin/activate.fish
python bot.py
```
