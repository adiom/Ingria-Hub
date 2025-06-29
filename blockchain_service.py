import hashlib
import json
from typing import Optional
from sqlalchemy.orm import Session
from db import Memory

class BlockchainService:
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_hash(self, memory_text: str, previous_hash: str = "", timestamp: str = "") -> str:
        """Вычисляет хеш для блока памяти"""
        # Создаем строку для хеширования
        block_string = f"{memory_text}{previous_hash}{timestamp}"
        # Вычисляем SHA-256 хеш
        return hashlib.sha256(block_string.encode('utf-8')).hexdigest()
    
    def get_last_memory(self) -> Optional[Memory]:
        """Получает последнее воспоминание для вычисления previous_hash"""
        return self.db.query(Memory).order_by(Memory.id.desc()).first()
    
    def get_last_hash(self) -> str:
        """Получает хеш последнего блока"""
        last_memory = self.get_last_memory()
        if last_memory and last_memory.hash:
            return last_memory.hash
        return "0000000000000000000000000000000000000000000000000000000000000000"  # Genesis hash
    
    def create_memory_block(self, memory_text: str, memory_id: int, timestamp: str) -> tuple[str, str]:
        """Создает новый блок памяти с хешем"""
        previous_hash = self.get_last_hash()
        hash_value = self.calculate_hash(memory_text, previous_hash, timestamp)
        return hash_value, previous_hash
    
    def verify_chain_integrity(self) -> dict:
        """Проверяет целостность всей цепочки воспоминаний"""
        memories = self.db.query(Memory).order_by(Memory.id).all()
        
        if not memories:
            return {"valid": True, "message": "Цепочка пуста", "corrupted_blocks": []}
        
        corrupted_blocks = []
        previous_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        
        for memory in memories:
            # Проверяем, что хеш соответствует содержимому
            expected_hash = self.calculate_hash(
                memory.memory_text, 
                memory.previous_hash or previous_hash,
                memory.created_at.isoformat()
            )
            
            if memory.hash != expected_hash:
                corrupted_blocks.append({
                    "id": memory.id,
                    "expected_hash": expected_hash,
                    "actual_hash": memory.hash,
                    "created_at": memory.created_at.isoformat()
                })
            
            previous_hash = memory.hash or expected_hash
        
        is_valid = len(corrupted_blocks) == 0
        
        return {
            "valid": is_valid,
            "total_blocks": len(memories),
            "corrupted_blocks": corrupted_blocks,
            "message": f"Цепочка {'валидна' if is_valid else 'повреждена'}"
        }
    
    def repair_chain(self) -> dict:
        """Восстанавливает целостность цепочки, пересчитывая хеши"""
        memories = self.db.query(Memory).order_by(Memory.id).all()
        
        if not memories:
            return {"repaired": True, "message": "Нет блоков для восстановления"}
        
        repaired_count = 0
        previous_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        
        for memory in memories:
            # Вычисляем правильный хеш
            correct_hash = self.calculate_hash(
                memory.memory_text,
                memory.previous_hash or previous_hash,
                memory.created_at.isoformat()
            )
            
            # Если хеш неправильный, исправляем
            if memory.hash != correct_hash:
                memory.hash = correct_hash
                memory.previous_hash = memory.previous_hash or previous_hash
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
            "genesis_hash": "0000000000000000000000000000000000000000000000000000000000000000"
        } 