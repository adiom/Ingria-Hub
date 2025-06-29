#!/usr/bin/env python3
"""
Тест для проверки работы голосового режима с воспоминаниями
"""

import requests
import time

def test_voice_memory():
    """Тестирует голосовой режим с воспоминаниями"""
    
    print("🎤 Тестирование голосового режима с воспоминаниями")
    print("=" * 60)
    
    # Проверяем, что сервер работает
    try:
        response = requests.get("http://localhost:31337/memories/stats")
        stats = response.json()
        print(f"✅ Сервер работает. Воспоминаний в БД: {stats['total_memories']}")
    except Exception as e:
        print(f"❌ Сервер не отвечает: {e}")
        return
    
    print("\n📋 Инструкции для тестирования голосового режима:")
    print("1. Запустите live режим: python live.py --user-id 1")
    print("2. Говорите с Ингрией голосом:")
    print("   - 'Привет, помнишь ли ты Тимура?'")
    print("   - 'Где мы были в прошлый раз?'")
    print("   - 'Что ты помнишь о тестировании памяти?'")
    print("   - 'Расскажи о своих самых важных воспоминаниях'")
    print("3. Проверьте в логах:")
    print("   - [Memory] Обновлен контекст: X воспоминаний")
    print("   - [Memory] Сохранено новое воспоминание: ...")
    print("   - [Memory] Обновляем контекст после X поворотов...")
    
    print("\n🔍 Текущие воспоминания для контекста:")
    
    # Проверяем существующие воспоминания
    try:
        response = requests.get("http://localhost:31337/memories?limit=10")
        memories = response.json()['memories']
        print(f"   Всего воспоминаний: {len(memories)}")
        
        # Группируем по важности
        important = [m for m in memories if m['importance_score'] >= 7]
        regular = [m for m in memories if m['importance_score'] < 7]
        
        print(f"   🔥 Важных воспоминаний: {len(important)}")
        print(f"   📝 Обычных воспоминаний: {len(regular)}")
        
        if important:
            print("   Примеры важных воспоминаний:")
            for i, memory in enumerate(important[:3], 1):
                print(f"   {i}. {memory['memory_text'][:80]}...")
                
    except Exception as e:
        print(f"   ❌ Ошибка получения воспоминаний: {e}")
    
    print("\n⚙️ Настройки голосового режима:")
    print("   - Обновление контекста каждые 30 секунд")
    print("   - Обновление после каждых 5 поворотов")
    print("   - Загрузка 15 воспоминаний при старте")
    print("   - Загрузка 10 воспоминаний при обновлении")
    
    print("\n🚀 Готово к тестированию голосового режима!")
    print("Запустите: python live.py --user-id 1")
    print("И говорите с Ингрией голосом!")

if __name__ == "__main__":
    test_voice_memory() 