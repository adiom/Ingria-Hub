#!/usr/bin/env python3
"""
Тест для проверки работы live режима с воспоминаниями
"""

import asyncio
import subprocess
import time
import requests

def test_live_memory():
    """Тестирует live режим с воспоминаниями"""
    
    print("🎤 Тестирование Live режима с воспоминаниями")
    print("=" * 50)
    
    # Проверяем, что сервер работает
    try:
        response = requests.get("http://localhost:31337/memories/stats")
        stats = response.json()
        print(f"✅ Сервер работает. Воспоминаний в БД: {stats['total_memories']}")
    except Exception as e:
        print(f"❌ Сервер не отвечает: {e}")
        return
    
    print("\n📋 Инструкции для тестирования:")
    print("1. Запустите live режим: python live.py --user-id 1")
    print("2. Задайте Ингрии вопросы:")
    print("   - 'Помнишь ли ты Тимура?'")
    print("   - 'Где мы были в прошлый раз?'")
    print("   - 'Что ты помнишь о тестировании памяти?'")
    print("3. Проверьте, что Ингрия:")
    print("   - Отвечает с учетом воспоминаний")
    print("   - Создает секцию memory в ответах")
    print("   - Сохраняет новые воспоминания")
    
    print("\n🔍 Проверка перед запуском live режима:")
    
    # Проверяем существующие воспоминания
    try:
        response = requests.get("http://localhost:31337/memories?limit=5")
        memories = response.json()['memories']
        print(f"   Последние воспоминания: {len(memories)}")
        
        for i, memory in enumerate(memories[:3], 1):
            print(f"   {i}. {memory['memory_text'][:80]}...")
            
    except Exception as e:
        print(f"   ❌ Ошибка получения воспоминаний: {e}")
    
    print("\n🚀 Готово к тестированию live режима!")
    print("Запустите: python live.py --user-id 1")

if __name__ == "__main__":
    test_live_memory() 