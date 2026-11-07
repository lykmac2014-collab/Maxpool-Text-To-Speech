import asyncio
import os
import tempfile

import edge_tts
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import FSInputFile, Message

TOKEN = os.environ["BOT_TOKEN"]
# Необязательно: свой Telegram ID, чтобы бот отвечал только тебе
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

VOICES = {
    "svetlana": "ru-RU-SvetlanaNeural",  # женский
    "dmitry": "ru-RU-DmitryNeural",      # мужской
}
user_voice: dict[int, str] = {}

bot = Bot(TOKEN)
dp = Dispatcher()


def allowed(message: Message) -> bool:
    return OWNER_ID == 0 or message.from_user.id == OWNER_ID


@dp.message(CommandStart())
async def start(message: Message):
    if not allowed(message):
        return
    await message.answer(
        "Пришли текст — отвечу голосовым.\n"
        "Сменить голос: /voice svetlana или /voice dmitry"
    )


@dp.message(Command("voice"))
async def set_voice(message: Message):
    if not allowed(message):
        return
    parts = (message.text or "").split()
    name = parts[1].lower() if len(parts) > 1 else ""
    if name not in VOICES:
        await message.answer("Доступно: svetlana, dmitry")
        return
    user_voice[message.from_user.id] = VOICES[name]
    await message.answer(f"Голос: {name}")


@dp.message(F.text)
async def tts(message: Message):
    if not allowed(message):
        return
    text = message.text.strip()
    if len(text) > 4000:
        await message.answer("Слишком длинный текст (максимум 4000 символов).")
        return

    await bot.send_chat_action(message.chat.id, "record_voice")
    voice = user_voice.get(message.from_user.id, VOICES["svetlana"])

    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        await edge_tts.Communicate(text, voice).save(path)
        await message.answer_voice(FSInputFile(path))
    except Exception as e:
        await message.answer(f"Не получилось озвучить: {e}")
    finally:
        os.remove(path)


async def health(request):
    return web.Response(text="ok")


async def main():
    # Мини веб-сервер, чтобы бесплатные хостинги считали сервис живым
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "8080"))).start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
