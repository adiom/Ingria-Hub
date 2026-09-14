#!/usr/bin/env python3
"""
Скрипт для проверки воспоминаний в базе данных
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Memory, IngriaRequest
from memory_service import MemoryService

load_dotenv()

def check_memories():
    """Проверяет воспоминания в базе данных"""

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set. Add it to the .env file.")

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    memory_service = MemoryService(db)
    
    try:
        # Проверяем общее количество воспоминаний
        total_memories = db.query(Memory).count()
        print(f"📊 Всего воспоминаний в базе: {total_memories}")
        
        if total_memories == 0:
            print("❌ Воспоминаний пока нет!")
            return
        
        # Показываем последние 5 воспоминаний
        recent_memories = db.query(Memory).order_by(Memory.created_at.desc()).limit(5).all()
        
        print(f"\n🕒 Последние {len(recent_memories)} воспоминаний:")
        for i, memory in enumerate(recent_memories, 1):
            print(f"\n{i}. ID: {memory.id}")
            print(f"   Дата: {memory.created_at}")
            print(f"   Тип: {memory.memory_type}")
            print(f"   Важность: {memory.importance_score}/10")
            print(f"   Эмоции: {memory.emotions}")
            print(f"   Текст: {memory.memory_text[:200]}...")
        
        # Проверяем релевантные воспоминания
        print(f"\n🔍 Тестируем получение релевантных воспоминаний:")
        relevant_memories = memory_service.get_relevant_memories(limit=3)
        print(f"Найдено релевантных: {len(relevant_memories)}")
        
        for memory in relevant_memories:
            print(f"  - {memory.memory_text[:100]}...")
        
        # Проверяем форматирование для контекста
        print(f"\n📝 Тестируем форматирование для контекста:")
        context = memory_service.format_memories_for_context(relevant_memories)
        print(f"Длина контекста: {len(context)} символов")
        print(f"Контекст: {context[:300]}...")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_memories() 