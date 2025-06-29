#!/usr/bin/env python3

from blockchain_service import BlockchainService
from db import Memory
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Используем реальные параметры подключения к PostgreSQL
PG_URL = 'postgresql+psycopg2://ingria_user:tyutyikh6tRFH@10.0.1.105:5432/ingria_hub'

def debug_blockchain():
    """Отладочная функция для проверки блокчейна (PostgreSQL)"""
    engine = create_engine(PG_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    blockchain_service = BlockchainService(db)
    
    print("=== ОТЛАДКА БЛОКЧЕЙНА (PostgreSQL) ===")
    
    # Получаем все воспоминания
    memories = db.query(Memory).order_by(Memory.id).all()
    
    print(f"Всего блоков: {len(memories)}")
    print()
    
    # Проверяем блоки начиная с 100
    for i, memory in enumerate(memories[-10:], 1):  # Последние 10 блоков
        print(f"Блок #{memory.id}:")
        print(f"  Хеш: {memory.hash}")
        print(f"  Previous hash: {memory.previous_hash}")
        print(f"  Создан: {memory.created_at}")
        print(f"  Текст: {memory.memory_text[:50]}...")
        
        # Проверяем правильность хеша
        expected_hash = blockchain_service.calculate_hash(
            memory.memory_text,
            memory.previous_hash or "0000000000000000000000000000000000000000000000000000000000000000",
            memory.created_at.isoformat()
        )
        
        if memory.hash == expected_hash:
            print(f"  ✓ Хеш корректен")
        else:
            print(f"  ✗ Хеш НЕКОРРЕКТЕН!")
            print(f"    Ожидался: {expected_hash}")
            print(f"    Фактический: {memory.hash}")
        
        print()
    
    # Проверяем логику get_last_hash
    print("=== ПРОВЕРКА get_last_hash ===")
    for i in range(100, 106):
        memory = db.query(Memory).filter(Memory.id == i).first()
        if memory:
            print(f"Блок {i}: hash = {memory.hash}")
    
    last_hash = blockchain_service.get_last_hash()
    print(f"get_last_hash() возвращает: {last_hash}")
    
    # Проверяем, что должно быть previous_hash для блока 103
    block_102 = db.query(Memory).filter(Memory.id == 102).first()
    if block_102:
        print(f"Блок 102 hash: {block_102.hash}")
        print(f"Блок 103 должен иметь previous_hash = {block_102.hash}")
    
    print()
    print("=== ПРОВЕРКА create_memory_block ===")
    
    # Симулируем создание нового блока
    test_text = "Тестовое воспоминание для отладки"
    test_timestamp = "2025-06-29T12:00:00"
    
    hash_value, previous_hash = blockchain_service.create_memory_block(
        test_text, 999, test_timestamp
    )
    
    print(f"Создан тестовый блок:")
    print(f"  Хеш: {hash_value}")
    print(f"  Previous hash: {previous_hash}")
    
    # Проверяем, что previous_hash равен хешу последнего блока
    last_memory = blockchain_service.get_last_memory()
    if last_memory:
        print(f"Последний блок в БД: #{last_memory.id}, hash: {last_memory.hash}")
        if previous_hash == last_memory.hash:
            print("✓ Previous hash корректен")
        else:
            print("✗ Previous hash НЕКОРРЕКТЕН!")
    
    db.close()

if __name__ == "__main__":
    debug_blockchain() 