import re
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timedelta
from db import Memory, IngriaRequest, User
from blockchain_service import BlockchainService

class MemoryService:
    def __init__(self, db: Session):
        self.db = db
        self.blockchain_service = BlockchainService(db)
    
    def extract_memory_from_response(self, response_text: str) -> Optional[str]:
        """Извлекает секцию memory из ответа Ингрии"""
        # Более гибкое регулярное выражение для поиска секции memory
        memory_patterns = [
            r'memory:\s*(.*?)(?=\n\n|\n[A-Z]|$)',
            r'memory\s*:\s*(.*?)(?=\n\n|\n[A-Z]|$)',
            r'память\s*:\s*(.*?)(?=\n\n|\n[A-Z]|$)',
            r'воспоминание\s*:\s*(.*?)(?=\n\n|\n[A-Z]|$)'
        ]
        
        for pattern in memory_patterns:
            match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
            if match:
                memory_text = match.group(1).strip()
                if memory_text:  # Проверяем, что текст не пустой
                    print(f"[MemoryService] Найдена секция memory: {memory_text[:100]}...")
                    return memory_text
        
        print(f"[MemoryService] Секция memory не найдена в ответе")
        return None
    
    def save_memory(self, 
                   memory_text: str, 
                   request_id: Optional[int] = None,
                   user_id: Optional[int] = None,
                   context: Optional[str] = None,
                   memory_type: Optional[str] = None) -> Memory:
        """Сохраняет новое воспоминание в БД с блокчейн-защитой"""
        
        # Анализируем важность воспоминания
        importance_score = self._calculate_importance(memory_text)
        
        # Извлекаем эмоции
        emotions = self._extract_emotions(memory_text)
        
        # Создаем объект памяти
        memory = Memory(
            request_id=request_id,
            user_id=user_id,
            memory_text=memory_text,
            context=context,
            emotions=emotions,
            importance_score=importance_score,
            memory_type=memory_type
        )
        
        # Добавляем в БД для получения ID
        self.db.add(memory)
        self.db.flush()  # Получаем ID без коммита
        
        # Создаем блокчейн-хеши
        timestamp = memory.created_at.isoformat()
        hash_value, previous_hash = self.blockchain_service.create_memory_block(
            memory_text, memory.id, timestamp
        )
        
        # Устанавливаем хеши
        memory.hash = hash_value
        memory.previous_hash = previous_hash
        
        # Коммитим изменения
        self.db.commit()
        self.db.refresh(memory)
        
        print(f"[Blockchain] Сохранено воспоминание #{memory.id} с хешем: {hash_value[:16]}...")
        return memory
    
    def get_relevant_memories(self, 
                            user_id: Optional[int] = None,
                            limit: int = 10,
                            min_importance: int = 3) -> List[Memory]:
        """Получает релевантные воспоминания для контекста"""
        
        print(f"[MemoryService] Поиск воспоминаний: user_id={user_id}, limit={limit}, min_importance={min_importance}")
        
        # Сначала получаем важные воспоминания
        important_memories = []
        query = self.db.query(Memory).filter(
            Memory.importance_score >= min_importance
        )
        
        if user_id:
            query = query.filter(Memory.user_id == user_id)
            print(f"[MemoryService] Фильтруем по user_id: {user_id}")
        else:
            print(f"[MemoryService] user_id не указан, ищем все воспоминания")
        
        important_memories = query.order_by(
            desc(Memory.importance_score),
            desc(Memory.last_accessed)
        ).limit(limit // 2).all()
        
        print(f"[MemoryService] Найдено важных воспоминаний: {len(important_memories)}")
        
        # Затем получаем недавние воспоминания
        recent_memories = []
        recent_query = self.db.query(Memory)
        if user_id:
            recent_query = recent_query.filter(Memory.user_id == user_id)
        
        recent_memories = recent_query.order_by(
            desc(Memory.created_at)
        ).limit(limit // 2).all()
        
        print(f"[MemoryService] Найдено недавних воспоминаний: {len(recent_memories)}")
        
        # Объединяем и убираем дубликаты
        all_memories = []
        seen_ids = set()
        
        # Сначала добавляем важные
        for memory in important_memories:
            if memory.id not in seen_ids:
                all_memories.append(memory)
                seen_ids.add(memory.id)
        
        # Затем добавляем недавние, если есть место
        for memory in recent_memories:
            if memory.id not in seen_ids and len(all_memories) < limit:
                all_memories.append(memory)
                seen_ids.add(memory.id)
        
        # Если все еще мало воспоминаний, добавляем любые
        if len(all_memories) < limit // 2:
            print(f"[MemoryService] Мало воспоминаний, добавляем любые...")
            any_query = self.db.query(Memory)
            if user_id:
                any_query = any_query.filter(Memory.user_id == user_id)
            
            any_memories = any_query.order_by(
                desc(Memory.created_at)
            ).limit(limit).all()
            
            for memory in any_memories:
                if memory.id not in seen_ids and len(all_memories) < limit:
                    all_memories.append(memory)
                    seen_ids.add(memory.id)
        
        print(f"[MemoryService] Итого воспоминаний для контекста: {len(all_memories)}")
        
        # Обновляем счетчики доступа
        for memory in all_memories:
            memory.access_count += 1
            memory.last_accessed = datetime.utcnow()
        
        self.db.commit()
        return all_memories
    
    def get_memories_by_type(self, 
                           memory_type: str,
                           user_id: Optional[int] = None,
                           limit: int = 20) -> List[Memory]:
        """Получает воспоминания определенного типа"""
        query = self.db.query(Memory).filter(Memory.memory_type == memory_type)
        
        if user_id:
            query = query.filter(Memory.user_id == user_id)
        
        return query.order_by(desc(Memory.created_at)).limit(limit).all()
    
    def search_memories(self, 
                       search_text: str,
                       user_id: Optional[int] = None,
                       limit: int = 20) -> List[Memory]:
        """Поиск воспоминаний по тексту"""
        query = self.db.query(Memory).filter(
            Memory.memory_text.ilike(f'%{search_text}%')
        )
        
        if user_id:
            query = query.filter(Memory.user_id == user_id)
        
        return query.order_by(desc(Memory.importance_score)).limit(limit).all()
    
    def get_memory_summary(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Получает статистику воспоминаний"""
        query = self.db.query(Memory)
        
        if user_id:
            query = query.filter(Memory.user_id == user_id)
        
        total_memories = query.count()
        recent_memories = query.filter(
            Memory.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        avg_importance = self.db.query(func.avg(Memory.importance_score)).scalar() or 0
        
        return {
            'total_memories': total_memories,
            'recent_memories': recent_memories,
            'average_importance': round(avg_importance, 2)
        }
    
    def _calculate_importance(self, memory_text: str) -> int:
        """Вычисляет важность воспоминания на основе ключевых слов"""
        importance_keywords = {
            'важно': 3, 'критично': 5, 'супер': 4, 'невероятно': 4,
            'первый раз': 4, 'никогда': 4, 'всегда': 3, 'любимый': 3,
            'страшно': 4, 'опасно': 5, 'счастлив': 3, 'грустно': 2,
            'создатель': 5, 'Тимур': 4, 'память': 3, 'обучение': 3
        }
        
        score = 1
        memory_lower = memory_text.lower()
        
        for keyword, points in importance_keywords.items():
            if keyword in memory_lower:
                score += points
        
        return min(score, 10)  # Максимум 10
    
    def _extract_emotions(self, memory_text: str) -> Optional[str]:
        """Извлекает эмоции из текста воспоминания"""
        emotions = []
        emotion_keywords = {
            'радость': ['рад', 'счастлив', 'весело', 'улыбка', 'смех'],
            'грусть': ['грустно', 'печаль', 'тоска', 'плач'],
            'страх': ['страшно', 'боюсь', 'опасно', 'тревога'],
            'удивление': ['удивительно', 'неожиданно', 'вау', 'ого'],
            'любовь': ['люблю', 'нежность', 'тепло', 'забота'],
            'любопытство': ['интересно', 'любопытно', 'хочу знать'],
            'волнение': ['волнуюсь', 'волнительно', 'энергия']
        }
        
        memory_lower = memory_text.lower()
        for emotion, keywords in emotion_keywords.items():
            if any(keyword in memory_lower for keyword in keywords):
                emotions.append(emotion)
        
        return ', '.join(emotions) if emotions else None
    
    def format_memories_for_context(self, memories: List[Memory]) -> str:
        """Форматирует воспоминания для включения в контекст Ингрии"""
        if not memories:
            return ""
        
        context_parts = ["\n\nМои воспоминания (важные события из моей жизни):"]
        
        # Группируем воспоминания по важности
        important_memories = [m for m in memories if m.importance_score >= 7]
        regular_memories = [m for m in memories if m.importance_score < 7]
        
        # Сначала добавляем важные воспоминания
        if important_memories:
            context_parts.append("\n🔥 ВАЖНЫЕ ВОСПОМИНАНИЯ:")
            for memory in important_memories:
                date_str = memory.created_at.strftime("%d.%m.%Y")
                context_parts.append(f"\n- {date_str} ({memory.memory_type}): {memory.memory_text}")
                if memory.emotions:
                    context_parts.append(f"  Эмоции: {memory.emotions}")
        
        # Затем добавляем обычные воспоминания
        if regular_memories:
            context_parts.append("\n📝 ОБЫЧНЫЕ ВОСПОМИНАНИЯ:")
            for memory in regular_memories:
                date_str = memory.created_at.strftime("%d.%m.%Y")
                context_parts.append(f"\n- {date_str} ({memory.memory_type}): {memory.memory_text}")
        
        context_parts.append("\n💡 Используй эти воспоминания, чтобы отвечать более осмысленно и помнить наш общий опыт!")
        
        return '\n'.join(context_parts)
    
    def get_today_memories(self, 
                          user_id: Optional[int] = None,
                          limit: int = 20) -> List[Memory]:
        """Получает воспоминания, созданные сегодня"""
        today = datetime.utcnow().date()
        
        query = self.db.query(Memory).filter(
            func.date(Memory.created_at) == today
        )
        
        if user_id:
            query = query.filter(Memory.user_id == user_id)
        
        memories = query.order_by(
            desc(Memory.importance_score),
            desc(Memory.created_at)
        ).limit(limit).all()
        
        print(f"[MemoryService] Найдено воспоминаний за сегодня: {len(memories)}")
        return memories 