#!/usr/bin/env python3
"""
Тест для проверки правильного порядка отображения воспоминаний
"""

import requests
from datetime import datetime

def test_memory_order():
    """Тестирует правильный порядок отображения воспоминаний"""
    
    print("📅 Тестирование порядка отображения воспоминаний")
    print("=" * 60)
    
    # Проверяем, что сервер работает
    try:
        response = requests.get("http://localhost:31337/memories/stats")
        stats = response.json()
        print(f"✅ Сервер работает. Воспоминаний в БД: {stats['total_memories']}")
    except Exception as e:
        print(f"❌ Сервер не отвечает: {e}")
        return
    
    # Получаем воспоминания
    try:
        response = requests.get("http://localhost:31337/memories?limit=10")
        data = response.json()
        memories = data['memories']
        
        print(f"\n📋 Получено {len(memories)} воспоминаний:")
        
        # Проверяем порядок
        is_ordered = True
        for i, memory in enumerate(memories):
            date = datetime.fromisoformat(memory['created_at'].replace('Z', '+00:00'))
            print(f"  {i+1}. {date.strftime('%d.%m.%Y %H:%M')} - {memory['memory_text'][:50]}...")
            
            # Проверяем, что следующее воспоминание не новее текущего
            if i > 0:
                prev_date = datetime.fromisoformat(memories[i-1]['created_at'].replace('Z', '+00:00'))
                if date > prev_date:
                    is_ordered = False
                    print(f"    ❌ НЕПРАВИЛЬНЫЙ ПОРЯДОК: {date} новее {prev_date}")
        
        if is_ordered:
            print(f"\n✅ Порядок правильный: от новых к старым")
        else:
            print(f"\n❌ Порядок неправильный!")
            
    except Exception as e:
        print(f"❌ Ошибка получения воспоминаний: {e}")
        return
    
    print(f"\n🔧 Что исправлено:")
    print("   - API endpoint /memories теперь сортирует по дате (DESC)")
    print("   - API endpoint /memories/search сортирует результаты")
    print("   - Веб-интерфейс показывает дату и время")
    print("   - Порядок: от самых свежих к более ранним")
    
    print(f"\n🌐 Проверьте веб-интерфейс:")
    print("   http://10.0.1.22:31337/memories-ui")
    print("   Воспоминания должны отображаться в хронологическом порядке")

if __name__ == "__main__":
    test_memory_order() 