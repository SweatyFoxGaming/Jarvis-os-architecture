import sqlite3
import os
import datetime

class MemorySystem:
    def __init__(self, db_path="data/memory.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Episodic Memory: Specific interactions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                prompt TEXT,
                response TEXT,
                reflection TEXT,
                tags TEXT,
                success_score INTEGER,
                consolidated INTEGER DEFAULT 0
            )
        ''')
        # Semantic Memory: Learned facts and lessons
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                key TEXT,
                value TEXT,
                last_updated TEXT
            )
        ''')
        self.conn.commit()

    def add_episode(self, prompt, response, reflection=None, score=0, tags=None):
        cursor = self.conn.cursor()
        timestamp = datetime.datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO episodic_memory (timestamp, prompt, response, reflection, tags, success_score) VALUES (?, ?, ?, ?, ?, ?)",
            (timestamp, prompt, response, reflection, tags, score)
        )
        self.conn.commit()

    def add_fact(self, category, key, value):
        cursor = self.conn.cursor()
        timestamp = datetime.datetime.now().isoformat()
        cursor.execute(
            "INSERT OR REPLACE INTO semantic_memory (category, key, value, last_updated) VALUES (?, ?, ?, ?)",
            (category, key, value, timestamp)
        )
        self.conn.commit()

    def search_episodes(self, query, limit=5):
        cursor = self.conn.cursor()
        # Enhanced search using tags if possible, fallback to keyword
        cursor.execute(
            """SELECT prompt, response, reflection FROM episodic_memory
               WHERE tags LIKE ? OR prompt LIKE ? OR response LIKE ?
               ORDER BY id DESC LIMIT ?""",
            (f'%{query}%', f'%{query}%', f'%{query}%', limit)
        )
        return cursor.fetchall()

    def get_recent_lessons(self, limit=10):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT reflection FROM episodic_memory WHERE reflection IS NOT NULL AND reflection != '' ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return [row[0] for row in cursor.fetchall()]

    def get_semantic_knowledge(self, limit=20):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT value FROM semantic_memory ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return [row[0] for row in cursor.fetchall()]

if __name__ == "__main__":
    mem = MemorySystem()
    mem.add_fact("system", "os_name", "Phoenix OS")
    print("Memory system initialized and test fact added.")
