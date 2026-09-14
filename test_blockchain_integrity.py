#!/usr/bin/env python3
"""Автономные проверки цепочки: python test_blockchain_integrity.py.

Используют unittest и SQLite в памяти; сервер, ключи API и рабочая БД не нужны.
"""

import hashlib
import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from blockchain_service import BlockchainService
from db import Base, Memory
from memory_service import MemoryService


GENESIS_HASH = "0" * 64


def stored_hash(memory):
    payload = f"{memory.memory_text}{memory.previous_hash}{memory.created_at.isoformat()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class BlockchainIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, autoflush=False)()
        self.chain = BlockchainService(self.db)
        self.memories = MemoryService(self.db)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def seed_chain(self):
        # Пропуски ID допустимы; фикстура не использует проверяемое создание блоков.
        rows = []
        previous_hash = GENESIS_HASH
        for index, memory_id in enumerate((10, 20, 30)):
            memory = Memory(
                id=memory_id,
                memory_text=f"Воспоминание {index}",
                created_at=datetime(2026, 1, 1) + timedelta(seconds=index),
                previous_hash=previous_hash,
            )
            memory.hash = stored_hash(memory)
            previous_hash = memory.hash
            self.db.add(memory)
            rows.append(memory)
        self.db.commit()
        return rows

    def assert_linked(self):
        self.db.expire_all()
        previous_hash = GENESIS_HASH
        for memory in self.db.query(Memory).order_by(Memory.id).all():
            self.assertEqual(memory.previous_hash, previous_hash)
            self.assertEqual(memory.hash, stored_hash(memory))
            previous_hash = memory.hash
        self.assertTrue(self.chain.verify_chain_integrity()["valid"])

    def test_empty_chain(self):
        result = self.chain.verify_chain_integrity()
        self.assertTrue(result["valid"])
        self.assertEqual(result["total_blocks"], 0)
        self.assertEqual(result["corrupted_blocks"], [])
        self.assertEqual(self.chain.repair_chain()["repaired_blocks"], 0)

    def test_saved_memories_link_to_predecessor_after_flush(self):
        with redirect_stdout(io.StringIO()):
            for index in range(3):
                self.memories.save_memory(f"Новое воспоминание {index}")
        self.assertEqual(self.db.query(Memory).count(), 3)
        self.assert_linked()

    def test_create_block_excludes_current_and_later_rows(self):
        rows = self.seed_chain()
        for index, memory in enumerate(rows):
            with self.subTest(memory_id=memory.id):
                hash_value, previous_hash = self.chain.create_memory_block(
                    memory.memory_text, memory.id, memory.created_at.isoformat()
                )
                expected_previous = rows[index - 1].hash if index else GENESIS_HASH
                self.assertEqual(previous_hash, expected_previous)
                self.assertEqual(hash_value, memory.hash)

    def test_valid_chain_with_id_gaps(self):
        self.seed_chain()
        self.assert_linked()
        info = self.chain.get_chain_info()
        self.assertTrue(info["chain_valid"])
        self.assertEqual(info["total_blocks"], 3)
        self.assertEqual(info["last_block_id"], 30)

    def test_changed_content_timestamp_or_hash_is_detected(self):
        middle = self.seed_chain()[1]
        changes = {
            "memory_text": "Изменённое воспоминание",
            "created_at": datetime(2026, 2, 1),
            "hash": "f" * 64,
        }
        for field, value in changes.items():
            with self.subTest(field=field):
                original = getattr(middle, field)
                setattr(middle, field, value)
                self.db.commit()
                result = self.chain.verify_chain_integrity()
                self.assertFalse(result["valid"])
                self.assertIn(middle.id, [row["id"] for row in result["corrupted_blocks"]])
                setattr(middle, field, original)
                self.db.commit()

    def test_self_consistent_wrong_link_is_detected_without_writes(self):
        first, middle, _ = self.seed_chain()
        middle.previous_hash = GENESIS_HASH
        middle.hash = stored_hash(middle)
        self.db.commit()
        before = (middle.hash, middle.previous_hash)
        result = self.chain.verify_chain_integrity()
        self.assertFalse(result["valid"])
        broken = next(row for row in result["corrupted_blocks"] if row["id"] == middle.id)
        self.assertEqual(broken["expected_previous_hash"], first.hash)
        self.assertEqual(broken["actual_previous_hash"], GENESIS_HASH)
        self.assertFalse(self.db.dirty)
        self.db.expire_all()
        self.assertEqual((middle.hash, middle.previous_hash), before)

    def test_missing_previous_hash_is_not_silently_substituted(self):
        rows = self.seed_chain()
        for memory in rows:
            original = memory.previous_hash
            for missing in (None, ""):
                with self.subTest(memory_id=memory.id, previous_hash=missing):
                    memory.previous_hash = missing
                    self.db.commit()
                    result = self.chain.verify_chain_integrity()
                    self.assertFalse(result["valid"])
                    self.assertIn(memory.id, [row["id"] for row in result["corrupted_blocks"]])
            memory.previous_hash = original
            self.db.commit()

    def test_deleting_first_block_is_detected(self):
        first, middle, _ = self.seed_chain()
        self.db.delete(first)
        self.db.commit()
        result = self.chain.verify_chain_integrity()
        self.assertFalse(result["valid"])
        self.assertEqual(result["corrupted_blocks"][0]["id"], middle.id)

    def test_deleting_middle_block_is_detected_and_repair_relinks(self):
        _, middle, last = self.seed_chain()
        self.db.delete(middle)
        self.db.commit()
        result = self.chain.verify_chain_integrity()
        self.assertFalse(result["valid"])
        self.assertEqual(result["corrupted_blocks"][0]["id"], last.id)
        self.assertEqual(self.chain.repair_chain()["repaired_blocks"], 1)
        self.assert_linked()

    def test_repair_rebuilds_legacy_links_and_is_idempotent(self):
        rows = self.seed_chain()
        for memory in rows:
            memory.previous_hash = GENESIS_HASH
            memory.hash = stored_hash(memory)
        self.db.commit()
        self.assertFalse(self.chain.verify_chain_integrity()["valid"])
        self.assertEqual(self.chain.repair_chain()["repaired_blocks"], 2)
        self.assert_linked()
        self.assertEqual(self.chain.repair_chain()["repaired_blocks"], 0)

    def test_repair_propagates_changed_hash_and_preserves_content(self):
        rows = self.seed_chain()
        rows[0].memory_text = "Изменённое содержимое первого блока"
        self.db.commit()
        before = [(row.id, row.memory_text, row.created_at) for row in rows]
        self.assertEqual(self.chain.repair_chain()["repaired_blocks"], 3)
        self.assert_linked()
        self.assertEqual([(row.id, row.memory_text, row.created_at) for row in rows], before)

    def test_repair_restores_missing_link_even_if_hash_is_correct(self):
        first = self.seed_chain()[0]
        original_hash = first.hash
        first.previous_hash = None
        self.db.commit()
        self.assertEqual(self.chain.repair_chain()["repaired_blocks"], 1)
        self.assert_linked()
        self.assertEqual(first.hash, original_hash)

    def test_repair_initializes_unhashed_memories(self):
        for memory in self.seed_chain():
            memory.hash = None
            memory.previous_hash = None
        self.db.commit()
        self.assertFalse(self.chain.verify_chain_integrity()["valid"])
        self.assertEqual(self.chain.repair_chain()["repaired_blocks"], 3)
        self.assert_linked()


if __name__ == "__main__":
    unittest.main(verbosity=2)
