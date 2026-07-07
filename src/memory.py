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
                embedding BLOB,
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
                embedding BLOB,
                last_updated TEXT
            )
        ''')
        self.conn.commit()

    def add_episode(self, prompt, response, reflection=None, score=0, tags=None, embedding=None):
        import pickle
        cursor = self.conn.cursor()
        timestamp = datetime.datetime.now().isoformat()
        emb_blob = pickle.dumps(embedding) if embedding else None
        cursor.execute(
            "INSERT INTO episodic_memory (timestamp, prompt, response, reflection, tags, embedding, success_score) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (timestamp, prompt, response, reflection, tags, emb_blob, score)
        )
        self.conn.commit()

    def add_fact(self, category, key, value, embedding=None):
        import pickle
        cursor = self.conn.cursor()
        timestamp = datetime.datetime.now().isoformat()
        emb_blob = pickle.dumps(embedding) if embedding else None
        cursor.execute(
            "INSERT OR REPLACE INTO semantic_memory (category, key, value, embedding, last_updated) VALUES (?, ?, ?, ?, ?)",
            (category, key, value, emb_blob, timestamp)
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

    def semantic_search(self, query_embedding, table="semantic_memory", limit=5):
        import pickle
        import numpy as np

        cursor = self.conn.cursor()
        cursor.execute(f"SELECT value, embedding FROM {table} WHERE embedding IS NOT NULL")
        rows = cursor.fetchall()

        if not rows:
            return []

        results = []
        q_vec = np.array(query_embedding)

        for value, emb_blob in rows:
            vec = np.array(pickle.loads(emb_blob))
            # Cosine similarity
            score = np.dot(q_vec, vec) / (np.linalg.norm(q_vec) * np.linalg.norm(vec))
            results.append((value, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:limit]]

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
