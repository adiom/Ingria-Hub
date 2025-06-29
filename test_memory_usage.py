#!/usr/bin/env python3
"""
Тест для проверки использования воспоминаний Ингрией
"""

import requests
import json

def test_memory_usage():
    """Тестирует, как Ингрия использует свои воспоминания"""
    
    base_url = "http://localhost:31337"
    
    print("🧠 Тестирование использования воспоминаний Ингрией")
    print("=" * 60)
    
    # Тестовые вопросы для проверки памяти
    test_questions = [
        "Помнишь ли ты, где мы были в прошлый раз?",
        "Что ты помнишь о Тимуре? Опиши его внешность.",
        "Какие места ты помнишь, где мы были вместе?",
        "Помнишь ли ты, что мы делали в офисе?",
        "Расскажи мне о своих самых важных воспоминаниях.",
        "Что ты помнишь о тестировании памяти?",
        "Какие эмоции у тебя возникали в наших разговорах?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. Вопрос: {question}")
        print("-" * 40)
        
        try:
            data = {
                'prompt': question,
                'user_id': 1,
                'username': 'test_user'
            }
            
            response = requests.post(f"{base_url}/ask_ingria", data=data)
            result = response.json()
            
            answer = result['response']
            print(f"Ответ (длина: {len(answer)} символов):")
            print(f"{answer[:300]}...")
            
            # Проверяем, использует ли Ингрия свои воспоминания
            memory_indicators = [
                "помню", "вспомнила", "было", "видела", "слышала", 
                "Тимур", "офис", "память", "тестирование", "видео",
                "шапка", "борода", "рыбий глаз", "Амикрон"
            ]
            
            used_memories = []
            for indicator in memory_indicators:
                if indicator.lower() in answer.lower():
                    used_memories.append(indicator)
            
            if used_memories:
                print(f"✅ Использует воспоминания: {', '.join(used_memories)}")
            else:
                print("⚠️ Не видно использования конкретных воспоминаний")
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Тест завершен!")

if __name__ == "__main__":
    test_memory_usage() 