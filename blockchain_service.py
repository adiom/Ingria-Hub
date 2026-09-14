import hashlib
from typing import Optional
from sqlalchemy.orm import Session
from db import Memory

GENESIS_HASH = "0" * 64


class BlockchainService:
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_hash(self, memory_text: str, previous_hash: str = "", timestamp: str = "") -> str:
        """Вычисляет хеш для блока памяти"""
        # Создаем строку для хеширования
        block_string = f"{memory_text}{previous_hash}{timestamp}"
        # Вычисляем SHA-256 хеш
        return hashlib.sha256(block_string.encode('utf-8')).hexdigest()
    
    def get_last_memory(self, before_id: Optional[int] = None) -> Optional[Memory]:
        """Получает последнее воспоминание, при необходимости строго до указанного ID."""
        query = self.db.query(Memory)
        if before_id is not None:
            query = query.filter(Memory.id < before_id)
        return query.order_by(Memory.id.desc()).first()
    
    def get_last_hash(self, before_id: Optional[int] = None) -> str:
        """Получает хеш последнего блока"""
        last_memory = self.get_last_memory(before_id=before_id)
        if last_memory and last_memory.hash:
            return last_memory.hash
        return GENESIS_HASH
    
    def create_memory_block(self, memory_text: str, memory_id: int, timestamp: str) -> tuple[str, str]:
        """Создает новый блок памяти с хешем"""
        # После flush() текущая запись уже видна в БД; исключаем её и более поздние ID.
        previous_hash = self.get_last_hash(before_id=memory_id)
        hash_value = self.calculate_hash(memory_text, previous_hash, timestamp)
        return hash_value, previous_hash
    
    def verify_chain_integrity(self) -> dict:
        """Проверяет хеши и связи соседних записей в порядке ID, не изменяя данные."""
        memories = self.db.query(Memory).order_by(Memory.id).all()
        
        if not memories:
            return {
                "valid": True,
                "total_blocks": 0,
                "message": "Цепочка пуста",
                "corrupted_blocks": [],
            }
        
        corrupted_blocks = []
        previous_hash = GENESIS_HASH
        
        for memory in memories:
            # Предшественника определяет порядок ID, а не сохранённая ссылка самой записи.
            expected_hash = self.calculate_hash(
                memory.memory_text, 
                previous_hash,
                memory.created_at.isoformat()
            )
            
            if memory.previous_hash != previous_hash or memory.hash != expected_hash:
                corrupted_blocks.append({
                    "id": memory.id,
                    "expected_hash": expected_hash,
                    "actual_hash": memory.hash,
                    "expected_previous_hash": previous_hash,
                    "actual_previous_hash": memory.previous_hash,
                    "created_at": memory.created_at.isoformat()
                })
            
            # Проверяем следующую связь с фактически сохранённым хешем соседа.
            previous_hash = memory.hash or ""
        
        is_valid = len(corrupted_blocks) == 0
        
        return {
            "valid": is_valid,
            "total_blocks": len(memories),
            "corrupted_blocks": corrupted_blocks,
            "message": f"Цепочка {'валидна' if is_valid else 'повреждена'}"
        }
    
    def repair_chain(self) -> dict:
        """Перестраивает ссылки и хеши по ID на основе текущего содержимого записей."""
        memories = self.db.query(Memory).order_by(Memory.id).all()
        
        if not memories:
            return {
                "repaired": True,
                "repaired_blocks": 0,
                "total_blocks": 0,
                "message": "Нет блоков для восстановления",
            }
        
        repaired_count = 0
        previous_hash = GENESIS_HASH
        
        for memory in memories:
            # Вычисляем правильный хеш
            correct_hash = self.calculate_hash(
                memory.memory_text,
                previous_hash,
                memory.created_at.isoformat()
            )
            
            # Используем уже восстановленный хеш предыдущей записи для всей цепочки.
            if memory.previous_hash != previous_hash or memory.hash != correct_hash:
                memory.hash = correct_hash
                memory.previous_hash = previous_hash
                repaired_count += 1
            
            previous_hash = memory.hash
        
        if repaired_count > 0:
            self.db.commit()
        
        return {
            "repaired": True,
            "repaired_blocks": repaired_count,
            "total_blocks": len(memories),
            "message": f"Восстановлено {repaired_count} блоков из {len(memories)}"
        }
    
    def get_chain_info(self) -> dict:
        """Получает информацию о блокчейне"""
        total_memories = self.db.query(Memory).count()
        last_memory = self.get_last_memory()
        
        integrity_check = self.verify_chain_integrity()
        
        return {
            "total_blocks": total_memories,
            "last_block_id": last_memory.id if last_memory else None,
            "last_block_hash": last_memory.hash if last_memory else None,
            "chain_valid": integrity_check["valid"],
            "corrupted_blocks": len(integrity_check["corrupted_blocks"]),
            "genesis_hash": GENESIS_HASH
        }
