import os
import aiohttp
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db import Base, User

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_API_KEY")
API_URL = os.getenv("INGRIA_API_URL", "http://localhost:31337/ask_ingria")

DATABASE_URL = "sqlite:///ingria.db"
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

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
    # Сохраняем пользователя в БД (если его ещё нет)
    db = SessionLocal()
    try:
        tg_id = str(message.from_user.id)
        username = message.from_user.username
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        if not user:
            user = User(telegram_id=tg_id, username=username)
            db.add(user)
            db.commit()
        user_id = user.id
    finally:
        db.close()
    # Добавляем user_id и username в form-data
    data['user_id'] = str(user_id)
    data['username'] = username or ''
    # Caption или текст
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
    if message.video:
        file = await bot.get_file(message.video.file_id)
        file_path = file.file_path
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        print(f"[TG] Видео: {file_url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                video_bytes = await resp.read()
                mime = message.video.mime_type or 'video/mp4'
                files['video_file'] = ('video.mp4', video_bytes, mime)
    if message.video_note:
        file = await bot.get_file(message.video_note.file_id)
        file_path = file.file_path
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        print(f"[TG] Видеосообщение: {file_url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                video_bytes = await resp.read()
                files['video_file'] = ('video_note.mp4', video_bytes, 'video/mp4')
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
                        response_text = result.get('response', 'Нет ответа от Ingria.')
                        # Разбить длинный ответ на части по 4000 символов и отправлять как Markdown
                        for chunk in [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]:
                            await message.answer(chunk, parse_mode="Markdown")
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