# src/memory/secure_store.py (minimal SQLite version)
import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

class SecureMemoryStore:
    def __init__(self, db_path="data/memory.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_text ON memory(text)")

    def insert(self, text: str, metadata: Optional[Dict] = None):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO memory (text, metadata) VALUES (?, ?)", (text, json.dumps(metadata or {})))
        self.conn.commit()
        return cur.lastrowid

    def search_by_text(self, search_term: str, limit=10):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, text, metadata, timestamp FROM memory WHERE text LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (f"%{search_term}%", limit)
        )
        rows = cur.fetchall()
        return [
            {"id": r[0], "text": r[1], "metadata": json.loads(r[2]) if r[2] else {}, "timestamp": r[3]}
            for r in rows
        ]

    def delete_by_id(self, record_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM memory WHERE id = ?", (record_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def close(self):
        self.conn.close()
