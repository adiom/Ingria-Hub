#!/usr/bin/env python3
"""
Тест блокчейн-функциональности памяти Ингрии
"""

import requests
import json

def test_blockchain():
    """Тестирует блокчейн-функциональность"""
    
    print("🔗 Тестирование блокчейн-функциональности")
    print("=" * 60)
    
    # Проверяем, что сервер работает
    try:
        response = requests.get("http://localhost:31337/memories/stats")
        stats = response.json()
        print(f"✅ Сервер работает. Воспоминаний в БД: {stats['total_memories']}")
    except Exception as e:
        print(f"❌ Сервер не отвечает: {e}")
        return
    
    # Тестируем информацию о блокчейне
    print("\n📊 Информация о блокчейне:")
    try:
        response = requests.get("http://localhost:31337/blockchain/info")
        info = response.json()
        print(f"   Всего блоков: {info['total_blocks']}")
        print(f"   Последний блок ID: {info['last_block_id']}")
        print(f"   Хеш последнего блока: {info['last_block_hash'][:16]}...")
        print(f"   Цепочка валидна: {'✅' if info['chain_valid'] else '❌'}")
        print(f"   Поврежденных блоков: {info['corrupted_blocks']}")
    except Exception as e:
        print(f"❌ Ошибка получения информации: {e}")
    
    # Тестируем проверку целостности
    print("\n🔍 Проверка целостности:")
    try:
        response = requests.get("http://localhost:31337/blockchain/verify")
        verify = response.json()
        print(f"   Статус: {verify['message']}")
        print(f"   Всего блоков: {verify['total_blocks']}")
        print(f"   Поврежденных блоков: {len(verify['corrupted_blocks'])}")
        
        if verify['corrupted_blocks']:
            print("   ❌ Найдены поврежденные блоки:")
            for block in verify['corrupted_blocks'][:3]:  # Показываем первые 3
                print(f"     - Блок #{block['id']}: {block['actual_hash'][:16]}...")
        else:
            print("   ✅ Все блоки целы")
            
    except Exception as e:
        print(f"❌ Ошибка проверки целостности: {e}")
    
    # Тестируем получение воспоминаний с хешами
    print("\n📋 Последние воспоминания с хешами:")
    try:
        response = requests.get("http://localhost:31337/memories?limit=3")
        memories = response.json()['memories']
        
        for i, memory in enumerate(memories):
            print(f"   {i+1}. ID: {memory['id']}")
            print(f"      Текст: {memory['memory_text'][:50]}...")
            print(f"      Хеш: {memory.get('hash', 'НЕТ')[:16]}...")
            print(f"      Предыдущий хеш: {memory.get('previous_hash', 'НЕТ')[:16]}...")
            print()
            
    except Exception as e:
        print(f"❌ Ошибка получения воспоминаний: {e}")
    
    print("🎉 Тестирование завершено!")

if __name__ == "__main__":
    test_blockchain() 