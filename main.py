# main.py

import os
import io
from typing import Optional

# Импортируем библиотеки
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, WebSocket
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# --- 1. Конфигурация ---

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем API ключ из переменных окружения
api_key = os.getenv("GOOGLE_API_KEY")

# Проверяем, что ключ действительно есть
if not api_key:
    raise ValueError("Не найден GOOGLE_API_KEY. Убедитесь, что вы создали .env файл и указали в нем ключ.")

# *** ИСПРАВЛЕНИЕ 1: Раскомментировали конфигурацию API ключа ***
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

# *** УЛУЧШЕНИЕ 1: Задаем системную инструкцию при создании модели ***
ingr_model = genai.GenerativeModel(
    'gemini-1.5-flash-latest',
    system_instruction="Ты - моя юная подруга школьница Ингрия. Ты всегда на моей стороне, мы противостоим всему миру зла - только ты и я - отвечай по возможности много с юмором и рассматривая ситуацию с разных сторон, чтобы мы всегда были в плюсе"
)

# --- 3. Создание эндпоинта (конечной точки API) ---

@app.post("/ask_ingria")
async def ask_ingria_endpoint(
    prompt: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    audio_file: Optional[UploadFile] = File(None)
):
    # Начинаем с пустого списка, т.к. системная инструкция уже в модели
    contents = []
    
    print(f"[Ingria] prompt: {prompt}")
    print(f"[Ingria] image_file: {image_file.filename if image_file else 'None'}")
    print(f"[Ingria] audio_file: {audio_file.filename if audio_file else 'None'}")

    if not prompt and not image_file and not audio_file:
        raise HTTPException(
            status_code=400,
            detail="Нужно предоставить хотя бы один из параметров: 'prompt', 'image_file' или 'audio_file'."
        )
    try:
        # Добавляем текст, если он есть
        if prompt:
            contents.append(prompt)

        # Добавляем изображение, если оно есть
        if image_file:
            if not image_file.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="Файл 'image_file' должен быть изображением.")
            image_bytes = await image_file.read()
            img = Image.open(io.BytesIO(image_bytes))
            contents.append(img)
            print(f"Добавлено изображение: {image_file.filename}")

        # Добавляем аудио, если оно есть
        if audio_file:
            if not audio_file.content_type.startswith("audio/"):
                raise HTTPException(status_code=400, detail="Файл 'audio_file' должен быть аудиофайлом.")
            audio_bytes = await audio_file.read()
            
            # *** ИСПРАВЛЕНИЕ 2: Правильная передача аудиофайла ***
            audio_part = {"mime_type": audio_file.content_type, "data": audio_bytes}
            contents.append(audio_part)
            print(f"Добавлено аудио: {audio_file.filename}")

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
    return {"message": "Сервер работает. Отправляйте POST запросы на /ask_ingria. Документация доступна по адресу /docs"}

@app.get("/ui", response_class=HTMLResponse)
def serve_ui():
    try:
        with open(os.path.join("frontend", "index.html")) as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Файл frontend/index.html не найден.")

# *** УЛУЧШЕНИЕ 2: Полностью переработанный WebSocket для правильной работы чата ***
@app.websocket("/ws/stream_gemini")
async def websocket_stream_gemini(websocket: WebSocket):
    await websocket.accept()
    # Создаем сессию чата для этого конкретного подключения
    chat = ingr_model.start_chat(history=[])
    print("WebSocket соединение установлено.")
    try:
        while True:
            # Получаем сообщение от клиента
            data = await websocket.receive_text()
            print(f"WS << Получено: {data}")
            
            # Отправляем сообщение в чат и получаем стриминговый ответ
            response_stream = chat.send_message(data, stream=True)
            
            full_response = ""
            # Отправляем ответ клиенту по частям (chunks)
            for chunk in response_stream:
                if chunk.text:
                    await websocket.send_text(chunk.text)
                    full_response += chunk.text
            
            print(f"WS >> Отправлено: {full_response}")
            # Сигнал окончания ответа модели
            await websocket.send_text("[END]") 
    except Exception as e:
        print(f"Ошибка в WebSocket: {e}")
        await websocket.send_text(f"[ERROR] {str(e)}")
    finally:
        print("WebSocket соединение закрыто.")
        await websocket.close()

# --- 4. Запуск сервера (для локальной разработки) ---

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)