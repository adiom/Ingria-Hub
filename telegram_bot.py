import os
import aiohttp
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_API_KEY")
API_URL = os.getenv("INGRIA_API_URL", "http://localhost:31337/ask_ingria")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("Привет! Пришли текст или фото — я спрошу Ingria и пришлю ответ.")

@dp.message()
async def handle_message(message: Message):
    print(f"[TG] Получено сообщение: {message}")
    data = {}
    files = {}
    if message.caption:
        data['prompt'] = message.caption
        print(f"[TG] Caption: {message.caption}")
    elif message.text:
        data['prompt'] = message.text
        print(f"[TG] Текст: {message.text}")
    if message.photo:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        file_path = file.file_path
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        print(f"[TG] Фото: {file_url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                img_bytes = await resp.read()
                files['image_file'] = ('photo.jpg', img_bytes, 'image/jpeg')
    if message.voice:
        file = await bot.get_file(message.voice.file_id)
        file_path = file.file_path
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        print(f"[TG] Голосовое сообщение: {file_url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                audio_bytes = await resp.read()
                files['audio_file'] = ('voice.ogg', audio_bytes, 'audio/ogg')
    if message.audio:
        file = await bot.get_file(message.audio.file_id)
        file_path = file.file_path
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        print(f"[TG] Аудиофайл: {file_url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                audio_bytes = await resp.read()
                mime = message.audio.mime_type or 'audio/mpeg'
                files['audio_file'] = ('audio.mp3', audio_bytes, mime)
    if not data and not files:
        await message.answer("Пришлите текст, фото или аудио.")
        print("[TG] Нет данных для отправки в endpoint")
        return
    print(f"[TG] Отправляем в endpoint: {API_URL}")
    print(f"[TG] Данные: {data}")
    print(f"[TG] Файлы: {list(files.keys())}")
    async with aiohttp.ClientSession() as session:
        form = aiohttp.FormData()
        for k, v in data.items():
            form.add_field(k, v)
        for k, v in files.items():
            form.add_field(k, v[1], filename=v[0], content_type=v[2])
        try:
            async with session.post(API_URL, data=form) as resp:
                print(f"[TG] Ответ сервера: status={resp.status}")
                text = await resp.text()
                print(f"[TG] Тело ответа: {text}")
                if resp.status == 200:
                    try:
                        result = await resp.json()
                        await message.answer(result.get('response', 'Нет ответа от Ingria.'))
                    except Exception as e:
                        await message.answer(f"Ошибка парсинга JSON: {e}\n{text}")
                else:
                    await message.answer(f"Ошибка Ingria API: {resp.status}\n{text}")
        except Exception as e:
            print(f"[TG] Ошибка при запросе: {e}")
            await message.answer(f"Ошибка: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 