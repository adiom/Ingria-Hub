#!/usr/bin/env python3

from blockchain_service import BlockchainService
from db import Memory
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Используем реальные параметры подключения к PostgreSQL
PG_URL = 'postgresql+psycopg2://ingria_user:tyutyikh6tRFH@10.0.1.105:5432/ingria_hub'

def fix_blockchain_chain():
    """Исправляет цепочку блокчейна, устанавливая правильные previous_hash"""
    engine = create_engine(PG_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    blockchain_service = BlockchainService(db)
    
    print("=== ИСПРАВЛЕНИЕ ЦЕПОЧКИ БЛОКЧЕЙНА ===")
    
    # Получаем все воспоминания
    memories = db.query(Memory).order_by(Memory.id).all()
    
    print(f"Всего блоков: {len(memories)}")
    print()
    
    # Исправляем блоки 103, 104, 105
    blocks_to_fix = [103, 104, 105]
    
    for block_id in blocks_to_fix:
        # Находим блок
        memory = db.query(Memory).filter(Memory.id == block_id).first()
        if not memory:
            print(f"Блок {block_id} не найден!")
            continue
            
        # Находим предыдущий блок
        prev_memory = db.query(Memory).filter(Memory.id == block_id - 1).first()
        if not prev_memory:
            print(f"Предыдущий блок {block_id - 1} не найден!")
            continue
            
        old_previous_hash = memory.previous_hash
        new_previous_hash = prev_memory.hash
        
        print(f"Исправляем блок #{block_id}:")
        print(f"  Старый previous_hash: {old_previous_hash}")
        print(f"  Новый previous_hash: {new_previous_hash}")
        
        # Обновляем previous_hash
        memory.previous_hash = new_previous_hash
        
        # Пересчитываем хеш блока
        new_hash = blockchain_service.calculate_hash(
            memory.memory_text,
            new_previous_hash,
            memory.created_at.isoformat()
        )
        
        print(f"  Старый хеш: {memory.hash}")
        print(f"  Новый хеш: {new_hash}")
        
        memory.hash = new_hash
        print(f"  ✓ Блок {block_id} исправлен")
        print()
    
    # Коммитим изменения
    db.commit()
    print("=== ИЗМЕНЕНИЯ СОХРАНЕНЫ ===")
    
    # Проверяем результат
    print("\n=== ПРОВЕРКА РЕЗУЛЬТАТА ===")
    for block_id in blocks_to_fix:
        memory = db.query(Memory).filter(Memory.id == block_id).first()
        if memory:
            print(f"Блок #{block_id}:")
            print(f"  Хеш: {memory.hash}")
            print(f"  Previous hash: {memory.previous_hash}")
            
            # Проверяем правильность хеша
            expected_hash = blockchain_service.calculate_hash(
                memory.memory_text,
                memory.previous_hash,
                memory.created_at.isoformat()
            )
            
            if memory.hash == expected_hash:
                print(f"  ✓ Хеш корректен")
            else:
                print(f"  ✗ Хеш НЕКОРРЕКТЕН!")
            print()
    
    # Проверяем целостность всей цепочки
    integrity = blockchain_service.verify_chain_integrity()
    print(f"Целостность цепочки: {'✓ ВАЛИДНА' if integrity['valid'] else '✗ ПОВРЕЖДЕНА'}")
    print(f"Поврежденных блоков: {len(integrity['corrupted_blocks'])}")
    
    db.close()

if __name__ == "__main__":
    fix_blockchain_chain() 