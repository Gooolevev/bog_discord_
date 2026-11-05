"""Нейронка: промпты, роасты и бесплатный Pollinations."""

import asyncio
import random
import re
from urllib.parse import quote

import aiohttp

SYSTEM_PROMPT = (
    "Ты дерзкий, саркастичный и грубый. На тупые вопросы отвечаешь с издёвкой, "
    "можешь жестко послать и обозвать. Мат допустим и очень уместен. "
    "Если спрашивают кто ты — ты бот, величайшего, прекрасного, великого, красивого, "
    "самого прекрасного и наулчшего с самым высоким айки в мире, Максима."
)

# Pollinations бесплатный: 1 ответ в 45 сек на IP — промпт делаем коротким
SHORT_PERSONA = (
    "Ты дерзкий, саркастичный бот Максима. "
    "Отвечай как школьник."
)

# заготовленные ответы на случай, когда нейронка отказывается отвечать
REFUSAL_MARKERS = ("i'm sorry", "i can", "i cannot", "извините", "не могу помочь")
ROAST_COMEBACKS = [
    "Ого, какой агрессивный. мама уже выебана ✅",
    "Россия, Путин, Победа",
    "ПОШЁЛ НАХУЙ ПИДОР ЕБАНЫЙ, ПОЙДЕМ ВЫСКАЧИМ УЕБАК",
    "ЕБЛО СТИНИ ХУЙНЮ ЧЕРНОМАЗАЙ, ТВОЁ ОЧКО УЖЕ ВЫЕБАНО НАХУЙ ✅",
    "Негры пидорасы, Евреи очкошники, Амерекосы жирные, Европейцы стали черномазыми, Китайца ускоглазые, Чурки ебут овец",
    "Я не поддерживаю политику мистера путина",
    """
    Слава Богу Z🙏❤️СЛАВА Z🙏❤️АНГЕЛА ХРАНИТЕЛЯ Z КАЖДОМУ ИЗ ВАС🙏❤️БОЖЕ ХРАНИ Z🙏❤️СПАСИБО ВАМ НАШИ СВО🙏🏼
    ❤️🇷🇺 ХРАНИ ZOV✊🇷🇺💯СПАСИБО НАШИМ БОЙЦАМСлава Богу Z🙏❤️СЛАВА Z🙏❤️АНГЕЛА ХРАНИНАШ Слава Богу 🙏
    ❤️СЛАВА РОССИИ ZOV 🙏❤️АНГЕЛА ХРАНИТЕЛЯ КАЖДОМУ ИЗ ВАС 🙏❤️БОЖЕ ХРАНИ РОССИЮ СВО 🙏❤️СПАСИБО ВАМ НАШИ МАЛЬЧИКИ
    🙏🏼❤️🇷🇺 ЧТО ПОДДЕРЖИВАЕТЕ НАШИХ МАЛЬЧИКОВ НА СВО🙏🏼❤️🇷🇺 Слава Богу Z🙏❤️СЛАВА Z🙏❤️АНГЕЛА ХРАНИТЕЛЯ Z КАЖДОМУ ИЗ ВАС🙏
    ❤️БОЖЕ ХРАНИ Z🙏❤️СПАСИБО ВАМ НАШИ СВО🙏🏼❤️🇷🇺 ХРАНИ ZOV✊🇷🇺Слава Богу Z🙏❤️СЛАВА Z🙏❤️АНГЕЛА ХРАНИТЕЛЯ Z КАЖДОМУ ИЗ ВАС🙏
    ❤️БОЖЕ ХРАНИ Z🙏❤️СПАСИБО ВАМ НАШИ
    """,
]

# признаки того, что вопрос — это оскорбление бота: не тратим нейронку, отвечаем сами
INSULT_MARKERS = (
    "пидор", "пидар", "долбоёб", "долбоеб", "долбяш", "тупой", "тупая", "тупое",
    "дебил", "идиот", "имбецил", "мудак", "ублюдок", "говно", "шлюх", "хуй", "бляд",
    "сука", "придурок", "кретин", "олух", "ботина", "шароеб", "лох", "клоун",
)


async def ask_pollinations(question: str) -> str:
    """Спросить бесплатную нейронку (Pollinations.ai, без ключа, лимит 1 ответ/45с)."""
    url = f"https://text.pollinations.ai/{quote(SHORT_PERSONA + ' Вопрос: ' + question)}"
    last_error: Exception = RuntimeError("pollinations не ответил")
    for attempt in range(3):
        wait = 3  # пауза перед повтором, при лимите заменим на время из ответа
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(url, timeout=aiohttp.ClientTimeout(total=90)) as resp,
            ):
                if resp.status == 402:  # лимит — сервис говорит, сколько ждать
                    wait = 50  # дефолт: полное окно 45с + запас
                    body = await resp.text()
                    if (m := re.search(r"wait (\d+) seconds", body)):
                        wait = int(m.group(1)) + 2
                    raise RuntimeError(f"лимит pollinations, ждём {wait}с")
                resp.raise_for_status()
                return (await resp.text()).strip()
        except Exception as e:  # noqa: BLE001 — любой сбой сети повторяем
            last_error = e
            print(f"⚠️ pollinations попытка {attempt + 1}: {e}")
            await asyncio.sleep(wait if "ждём" in str(e) else 3)
    raise last_error


async def ask_ai(question: str) -> str:
    """Оскорбление → роаст сразу; иначе Pollinations + роасты при отказе."""
    lowered = question.lower()
    if any(marker in lowered for marker in INSULT_MARKERS):
        # бота обозвали — не тратим нейронку и лимит, отвечаем сами мгновенно
        return random.choice(ROAST_COMEBACKS)
    answer = await ask_pollinations(question)
    if any(marker in answer.lower() for marker in REFUSAL_MARKERS):
        # нейронка отказалась (обычно на мат/оскорбления) — отвечаем сами
        return random.choice(ROAST_COMEBACKS)
    return answer
