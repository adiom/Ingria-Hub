#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы воспоминаний
"""

import requests
import json

def test_memory_context():
    """Тестирует систему воспоминаний"""
    
    base_url = "http://localhost:31337"
    
    print("🧪 Тестирование системы воспоминаний Ингрии")
    print("=" * 50)
    
    # 1. Проверяем статистику
    print("\n1. Проверяем статистику воспоминаний:")
    try:
        response = requests.get(f"{base_url}/memories/stats")
        stats = response.json()
        print(f"   Всего воспоминаний: {stats['total_memories']}")
        print(f"   За неделю: {stats['recent_memories']}")
        print(f"   Средняя важность: {stats['average_importance']}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # 2. Получаем существующие воспоминания
    print("\n2. Получаем существующие воспоминания:")
    try:
        response = requests.get(f"{base_url}/memories?limit=5")
        memories = response.json()['memories']
        print(f"   Найдено воспоминаний: {len(memories)}")
        
        for i, memory in enumerate(memories[:3], 1):
            print(f"   {i}. {memory['memory_text'][:100]}...")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # 3. Отправляем тестовый запрос
    print("\n3. Отправляем тестовый запрос к Ингрии:")
    try:
        data = {
            'prompt': 'Привет! Помнишь ли ты что-нибудь о Тимуре?',
            'user_id': 1,
            'username': 'test_user'
        }
        
        response = requests.post(f"{base_url}/ask_ingria", data=data)
        result = response.json()
        
        print(f"   ✅ Ответ получен (длина: {len(result['response'])} символов)")
        print(f"   Ответ: {result['response'][:200]}...")
        
        # Проверяем, есть ли секция memory
        if 'memory:' in result['response'].lower():
            print("   ✅ Секция memory найдена в ответе")
        else:
            print("   ⚠️ Секция memory не найдена в ответе")
            
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # 4. Проверяем обновленную статистику
    print("\n4. Проверяем обновленную статистику:")
    try:
        response = requests.get(f"{base_url}/memories/stats")
        stats = response.json()
        print(f"   Всего воспоминаний: {stats['total_memories']}")
        print(f"   За неделю: {stats['recent_memories']}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Тест завершен!")

if __name__ == "__main__":
    test_memory_context() 