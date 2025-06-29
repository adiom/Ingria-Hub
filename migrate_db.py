#!/usr/bin/env python3
"""
Скрипт для создания таблиц в PostgreSQL базе данных
"""

import os
from sqlalchemy import create_engine, text
from db import Base

def create_tables():
    """Создает все таблицы в базе данных"""
    
    # URL подключения к PostgreSQL
    DATABASE_URL = "postgresql+psycopg2://ingria_user:tyutyikh6tRFH@10.0.1.105:5432/ingria_hub"
    
    try:
        # Создаем движок
        engine = create_engine(DATABASE_URL)
        
        print("Подключение к базе данных...")
        
        # Создаем все таблицы
        Base.metadata.create_all(bind=engine)
        
        print("✅ Все таблицы успешно созданы!")
        print("\nСозданные таблицы:")
        print("- users")
        print("- ingria_requests") 
        print("- memories")
        print("- files")
        print("- ingria_errors")
        
    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        return False
    
    return True

def check_connection():
    """Проверяет подключение к базе данных"""
    
    DATABASE_URL = "postgresql+psycopg2://ingria_user:tyutyikh6tRFH@10.0.1.105:5432/ingria_hub"
    
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ Подключение к PostgreSQL успешно!")
            print(f"Версия: {version}")
            return True
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        return False

if __name__ == "__main__":
    print("=== Миграция базы данных Ingria Hub ===\n")
    
    # Проверяем подключение
    if not check_connection():
        print("\nПроверьте настройки подключения к базе данных.")
        exit(1)
    
    print("\nСоздание таблиц...")
    
    # Создаем таблицы
    if create_tables():
        print("\n🎉 Миграция завершена успешно!")
        print("\nТеперь вы можете:")
        print("1. Запустить сервер: python main.py")
        print("2. Открыть веб-интерфейс: http://localhost:8000/ui")
        print("3. Просмотреть воспоминания: http://localhost:8000/memories-ui")
    else:
        print("\n❌ Миграция не удалась!")
        exit(1) 