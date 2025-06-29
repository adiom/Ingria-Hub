#!/usr/bin/env python3
"""
Миграция для добавления блокчейн-функциональности в БД
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from db import Base

# Конфигурация БД
DATABASE_URL = "postgresql+psycopg2://ingria_user:tyutyikh6tRFH@10.0.1.105:5432/ingria_hub"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def migrate_blockchain():
    """Добавляет блокчейн-поля в таблицу memories"""
    
    print("🔗 Миграция блокчейн-функциональности")
    print("=" * 50)
    
    session = SessionLocal()
    
    try:
        # Проверяем, существуют ли уже поля
        result = session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'memories' AND column_name IN ('hash', 'previous_hash')
        """))
        
        existing_columns = [row[0] for row in result.fetchall()]
        
        if 'hash' in existing_columns and 'previous_hash' in existing_columns:
            print("✅ Блокчейн-поля уже существуют")
            return
        
        print("📝 Добавляем блокчейн-поля...")
        
        # Добавляем поле hash
        if 'hash' not in existing_columns:
            session.execute(text("ALTER TABLE memories ADD COLUMN hash VARCHAR"))
            print("   ✅ Добавлено поле 'hash'")
        
        # Добавляем поле previous_hash
        if 'previous_hash' not in existing_columns:
            session.execute(text("ALTER TABLE memories ADD COLUMN previous_hash VARCHAR"))
            print("   ✅ Добавлено поле 'previous_hash'")
        
        session.commit()
        print("✅ Миграция завершена успешно")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Ошибка миграции: {e}")
        raise
    finally:
        session.close()

def initialize_existing_memories():
    """Инициализирует блокчейн для существующих воспоминаний"""
    
    print("\n🔗 Инициализация блокчейна для существующих воспоминаний")
    print("=" * 60)
    
    session = SessionLocal()
    
    try:
        # Получаем все воспоминания без хешей
        result = session.execute(text("""
            SELECT id, memory_text, created_at 
            FROM memories 
            WHERE hash IS NULL OR previous_hash IS NULL
            ORDER BY id
        """))
        
        memories = result.fetchall()
        
        if not memories:
            print("✅ Все воспоминания уже имеют хеши")
            return
        
        print(f"📝 Найдено {len(memories)} воспоминаний для инициализации...")
        
        previous_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        
        for i, memory in enumerate(memories):
            memory_id, memory_text, created_at = memory
            
            # Вычисляем хеш
            import hashlib
            block_string = f"{memory_text}{previous_hash}{created_at.isoformat()}"
            hash_value = hashlib.sha256(block_string.encode('utf-8')).hexdigest()
            
            # Обновляем запись
            session.execute(text("""
                UPDATE memories 
                SET hash = :hash, previous_hash = :previous_hash 
                WHERE id = :id
            """), {
                "hash": hash_value,
                "previous_hash": previous_hash,
                "id": memory_id
            })
            
            previous_hash = hash_value
            
            if (i + 1) % 10 == 0:
                print(f"   ✅ Обработано {i + 1}/{len(memories)} воспоминаний")
        
        session.commit()
        print(f"✅ Инициализация завершена: {len(memories)} воспоминаний обработано")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Ошибка инициализации: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Запуск миграции блокчейн-функциональности")
    print("=" * 60)
    
    try:
        migrate_blockchain()
        initialize_existing_memories()
        
        print("\n🎉 Миграция завершена успешно!")
        print("Теперь память Ингрии защищена блокчейном!")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        exit(1) 