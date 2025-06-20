# main.py

import os
import io
import mimetypes
from typing import Optional

# Импортируем библиотеки
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import requests

# --- 1. Конфигурация ---

# Загружаем переменные окружения из .env файла (там должен быть твой GOOGLE_API_KEY)
load_dotenv()

# Получаем API ключ из переменных окружения
api_key = os.getenv("GOOGLE_API_KEY")

# Проверяем, что ключ действительно есть
if not api_key:
    # Если ключа нет, выводим ошибку и завершаем работу
    raise ValueError("Не найден GOOGLE_API_KEY. Убедитесь, что вы создали .env файл и указали в нем ключ.")

# Конфигурируем SDK Google с нашим ключом (пример, потом будет своя модель)
genai.configure(api_key=api_key)

# Создаем экземпляр FastAPI приложения
app = FastAPI(
    title="Canfly Ingria Hub",
    description="Отправляйте текст, фото и аудио",
    version="1.0.0"
)

# Раздача статики (frontend)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# --- 2. Логика работы с Ingria ---
# Выбираем модель (пример, потом будет своя)
ingr_model = genai.GenerativeModel(
    'gemini-1.5-flash-latest',
    system_instruction="Ты - Ингрия. Мы с тобой партнеры."
)

# --- 3. Создание эндпоинта (конечной точки API) ---

@app.post("/ask_ingria")
async def ask_ingria_endpoint(
    # Текстовый промпт. Необязательный. Получаем его из формы.
    prompt: Optional[str] = Form(None),
    # Файл с изображением. Необязательный.
    image_file: Optional[UploadFile] = File(None),
    # Файл с аудио. Необязательный.
    audio_file: Optional[UploadFile] = File(None)
):
    contents = [] # Начинаем с пустого списка
    if prompt:
        contents.append(prompt)
    
    print(f"[Ingria] prompt: {prompt}")
    print(f"[Ingria] image_file: {image_file}")
    print(f"[Ingria] audio_file: {audio_file}")
    if not prompt and not image_file and not audio_file:
        raise HTTPException(
            status_code=400,
            detail="Нужно предоставить хотя бы один из параметров: 'prompt', 'image_file' или 'audio_file'."
        )
    try:
        if prompt:
            contents.append(prompt)
        if image_file:
            if not image_file.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="Файл 'image_file' должен быть изображением.")
            image_bytes = await image_file.read()
            img = Image.open(io.BytesIO(image_bytes))
            contents.append(img)
            print(f"Добавлено изображение: {image_file.filename}")
        if audio_file:
            if not audio_file.content_type.startswith("audio/"):
                raise HTTPException(status_code=400, detail="Файл 'audio_file' должен быть аудиофайлом.")
            audio_bytes = await audio_file.read()
            print(f"Загрузка аудиофайла: {audio_file.filename} ({audio_file.content_type})...")
            gemini_audio = genai.upload_file(
                path=io.BytesIO(audio_bytes),
                mime_type=audio_file.content_type
            )
            contents.append(gemini_audio)
            print("Аудиофайл успешно загружен.")
        # --- Отправка запроса в Ingria через SDK ---
        print("Отправка запроса в Ingria (SDK)...")
        response = ingr_model.generate_content(contents)
        print("Ответ от Ingria получен.")
        return {"response": response.text}
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    """
    Корневой эндпоинт для проверки, что сервер работает.
    """
    return {"message": "Сервер работает. Отправляйте POST запросы на /ask_ingria. Документация доступна по адресу /docs"}

@app.get("/ui", response_class=HTMLResponse)
def serve_ui():
    with open(os.path.join("frontend", "index.html")) as f:
        return f.read()

@app.websocket("/ws/stream_gemini")
async def websocket_stream_gemini(websocket):
    await websocket.accept()
    try:
        history = []
        while True:
            data = await websocket.receive_text()
            history.append(data)
            response_stream = ingr_model.generate_content(history, stream=True)
            for chunk in response_stream:
                await websocket.send_text(chunk.text)
            await websocket.send_text("[END]")
    except Exception as e:
        await websocket.send_text(f"[ERROR] {str(e)}")
        await websocket.close()

# --- 4. Запуск сервера (для локальной разработки) ---

if __name__ == "__main__":
    # Эта команда запустит сервер, когда вы выполните `python main.py`
    # --reload означает, что сервер будет перезапускаться при каждом изменении кода
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)