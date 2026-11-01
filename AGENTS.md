# AGENTS.md — discord-bot

## О проекте
Простой Discord-бот на Python (`discord.py` v2, async). Весь бот сейчас в `bot.py` — намеренно минимальный, для проверки работы.

## Структура
- `bot.py` — точка входа и весь функционал (намеренно однофайловый). Команды — slash-команды (`@bot.tree.command`), синхронизация на каждом сервере в `on_ready`.

## Конвенции
- Код и комментарии — на русском языке.
- Команды — через `@bot.tree.command(name=..., description=...)`; описание параметров — через `@app_commands.describe`. Префиксных команд нет.
- Токен только из `.env` (`DISCORD_TOKEN`), см. `.env.example`.

## Запуск
```bash
source venv/bin/activate.fish
python bot.py
```
