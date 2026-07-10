import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional

# Configure logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecureMemoryStore:
    """
    Thread-safe (ish) memory store. Always uses ? placeholders.
    Never concatenates strings into SQL.
    """
    def __init__(self, db_path: str = "data/memory.db"):
        # Ensure the data directory exists
        import os
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Creates the memory table if it doesn't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    metadata TEXT,  -- Stored as JSON string
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create an index for faster text searches
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_text ON memory(text)")
            conn.commit()
            logger.info("[MEMORY] Database initialized at %s", self.db_path)

    def _get_connection(self):
        """Returns a connection with row factory for dict-like access."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Allows accessing columns by name
        return conn

    def insert(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Inserts a new memory. Metadata is automatically JSON-serialized.
        Returns the new row ID.
        """
        if metadata is None:
            metadata = {}
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # USING ? PLACEHOLDERS - SAFE
            cursor.execute(
                "INSERT INTO memory (text, metadata) VALUES (?, ?)",
                (text, json.dumps(metadata))
            )
            conn.commit()
            new_id = cursor.lastrowid
            logger.info("[MEMORY] Inserted record ID %d", new_id)
            return new_id

    def search_by_text(self, search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Searches for memories containing the search_term.
        SAFE: Uses ? for the LIKE pattern.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # The % wildcards are passed INSIDE the tuple, not the SQL string.
            cursor.execute(
                "SELECT id, text, metadata, timestamp FROM memory WHERE text LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{search_term}%", limit)
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append({
                    "id": row["id"],
                    "text": row["text"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "timestamp": row["timestamp"]
                })
            return results

    def delete_by_id(self, record_id: int) -> bool:
        """Deletes a record by ID. Returns True if deleted."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memory WHERE id = ?", (record_id,))
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info("[MEMORY] Deleted record ID %d", record_id)
            return deleted

    def close(self):
        """Closes any lingering connections (if using persistent conn, but we use context managers)."""
        # Since we use `with`, connections close automatically.
        pass

# Example usage:
if __name__ == "__main__":
    store = SecureMemoryStore("data/test_memory.db")
    
    # Insert safely
    store.insert("User said hello", {"user_id": 123, "session": "abc"})
    
    # Search safely
    results = store.search_by_text("hello")
    print(f"Found {len(results)} records: {results}")
    
    # Cleanup
    import os
    os.remove("data/test_memory.db")