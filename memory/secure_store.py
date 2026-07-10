# memory/secure_store.py
"""
Secure Memory Store – SQLite (development) & PostgreSQL (production) backend.
Now with connection pooling, retry logic, and dual backend support.
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from datetime import datetime

# Try importing PostgreSQL drivers
try:
    import psycopg2
    from psycopg2 import pool, OperationalError, sql
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

# SQLite (fallback)
import sqlite3

from config.secure_config import AppConfig

logger = logging.getLogger(__name__)


class SecureMemoryStore:
    """
    Dual‑backend memory store with automatic retry on contention.
    Uses PostgreSQL if configured and available, otherwise SQLite.
    """

    def __init__(self, db_path: str = "data/memory.db", use_postgres: Optional[bool] = None):
        """
        Initialize the memory store.
        If use_postgres is None, reads PG_USE_POSTGRES from environment.
        """
        self.db_path = db_path
        self._use_postgres = self._determine_backend(use_postgres)
        self._connection_pool = None
        self._init_backend()

    def _determine_backend(self, use_postgres: Optional[bool]) -> bool:
        if use_postgres is not None:
            return use_postgres
        # Read from environment
        env_val = os.getenv("PG_USE_POSTGRES", "false").lower()
        return env_val in ("true", "1", "yes")

    def _init_backend(self):
        if self._use_postgres:
            if not PSYCOPG2_AVAILABLE:
                logger.warning("psycopg2 not installed. Falling back to SQLite.")
                self._use_postgres = False
                self._init_sqlite()
                return
            self._init_postgres()
        else:
            self._init_sqlite()

    # ---------- PostgreSQL Backend ----------
    def _init_postgres(self):
        """Initialize PostgreSQL connection pool."""
        try:
            self._connection_pool = pool.SimpleConnectionPool(
                1,  # min connections
                20,  # max connections
                host=os.getenv("PG_HOST", "localhost"),
                port=os.getenv("PG_PORT", 5432),
                database=os.getenv("PG_DATABASE", "jarvis"),
                user=os.getenv("PG_USER", "jarvis_user"),
                password=os.getenv("PG_PASSWORD", ""),
            )
            logger.info("[SecureMemoryStore] PostgreSQL connection pool established.")
            self._create_postgres_tables()
        except Exception as e:
            logger.error(f"[SecureMemoryStore] PostgreSQL init failed: {e}. Falling back to SQLite.")
            self._use_postgres = False
            self._init_sqlite()

    def _create_postgres_tables(self):
        """Create memory table in PostgreSQL if not exists."""
        with self._get_postgres_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS memory (
                        id SERIAL PRIMARY KEY,
                        text TEXT NOT NULL,
                        metadata JSONB,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_text ON memory(text);")
                conn.commit()

    @contextmanager
    def _get_postgres_connection(self):
        """Get a connection from the pool with retry logic."""
        if self._connection_pool is None:
            raise RuntimeError("PostgreSQL connection pool not initialized.")
        conn = None
        for attempt in range(5):
            try:
                conn = self._connection_pool.getconn()
                yield conn
                return
            except OperationalError as e:
                if "could not connect" in str(e).lower() or "timeout" in str(e).lower():
                    wait = (2 ** attempt) * 0.1
                    logger.warning(f"PostgreSQL connection failed (attempt {attempt+1}), retrying in {wait:.2f}s")
                    time.sleep(wait)
                    continue
                raise
            finally:
                if conn:
                    self._connection_pool.putconn(conn)

    def _execute_postgres(self, query: str, params: tuple = (), retries: int = 3) -> Any:
        """Execute a PostgreSQL query with retry on serialization/deadlock errors."""
        for attempt in range(retries):
            try:
                with self._get_postgres_connection() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute(query, params)
                        if query.strip().upper().startswith("SELECT"):
                            return cur.fetchall()
                        conn.commit()
                        return cur.rowcount
            except OperationalError as e:
                if "deadlock detected" in str(e).lower() or "serialization failure" in str(e).lower():
                    wait = (2 ** attempt) * 0.1
                    logger.warning(f"Retrying PostgreSQL query (attempt {attempt+1}) after {wait:.2f}s")
                    time.sleep(wait)
                    continue
                raise
        raise RuntimeError(f"PostgreSQL query failed after {retries} retries.")

    # ---------- SQLite Backend ----------
    def _init_sqlite(self):
        """Initialize SQLite with WAL mode and retry logic."""
        self._sqlite_conn = None
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA cache_size=-20000;")  # 20 MB cache
            self._sqlite_conn = conn
            self._create_sqlite_tables()
            logger.info("[SecureMemoryStore] SQLite initialized with WAL mode.")
        except Exception as e:
            logger.error(f"[SecureMemoryStore] SQLite init failed: {e}")
            raise

    def _create_sqlite_tables(self):
        with self._sqlite_conn:
            self._sqlite_conn.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    metadata TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            self._sqlite_conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_text ON memory(text);")

    def _execute_sqlite(self, query: str, params: tuple = (), retries: int = 3) -> Any:
        """Execute SQLite query with retry on 'database is locked'."""
        for attempt in range(retries):
            try:
                with self._sqlite_conn:
                    cursor = self._sqlite_conn.execute(query, params)
                    if query.strip().upper().startswith("SELECT"):
                        return cursor.fetchall()
                    return cursor.rowcount
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower():
                    wait = (2 ** attempt) * 0.1
                    logger.warning(f"SQLite locked, retrying (attempt {attempt+1}) after {wait:.2f}s")
                    time.sleep(wait)
                    continue
                raise
        raise RuntimeError(f"SQLite query failed after {retries} retries.")

    # ---------- Unified Public API ----------
    def insert(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Insert a new record. Returns the ID."""
        if metadata is None:
            metadata = {}
        if self._use_postgres:
            result = self._execute_postgres(
                "INSERT INTO memory (text, metadata) VALUES (%s, %s) RETURNING id;",
                (text, json.dumps(metadata))
            )
            return result[0]["id"]
        else:
            result = self._execute_sqlite(
                "INSERT INTO memory (text, metadata) VALUES (?, ?);",
                (text, json.dumps(metadata))
            )
            # Get last inserted id
            last_id = self._execute_sqlite("SELECT last_insert_rowid();")[0][0]
            return last_id

    def search_by_text(self, search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for records containing search_term (case‑insensitive)."""
        if self._use_postgres:
            results = self._execute_postgres(
                "SELECT id, text, metadata, timestamp FROM memory WHERE text ILIKE %s ORDER BY timestamp DESC LIMIT %s;",
                (f"%{search_term}%", limit)
            )
            return [
                {
                    "id": r["id"],
                    "text": r["text"],
                    "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
                    "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
                }
                for r in results
            ]
        else:
            rows = self._execute_sqlite(
                "SELECT id, text, metadata, timestamp FROM memory WHERE text LIKE ? ORDER BY timestamp DESC LIMIT ?;",
                (f"%{search_term}%", limit)
            )
            return [
                {
                    "id": row[0],
                    "text": row[1],
                    "metadata": json.loads(row[2]) if row[2] else {},
                    "timestamp": row[3],
                }
                for row in rows
            ]

    def delete_by_id(self, record_id: int) -> bool:
        """Delete a record by ID."""
        if self._use_postgres:
            rows_affected = self._execute_postgres(
                "DELETE FROM memory WHERE id = %s;", (record_id,)
            )
            return rows_affected > 0
        else:
            rows_affected = self._execute_sqlite(
                "DELETE FROM memory WHERE id = ?;", (record_id,)
            )
            return rows_affected > 0

    def get_all(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all records (for migration, debugging)."""
        if self._use_postgres:
            results = self._execute_postgres(
                "SELECT id, text, metadata, timestamp FROM memory ORDER BY timestamp DESC LIMIT %s;", (limit,)
            )
            return [
                {
                    "id": r["id"],
                    "text": r["text"],
                    "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
                    "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
                }
                for r in results
            ]
        else:
            rows = self._execute_sqlite(
                "SELECT id, text, metadata, timestamp FROM memory ORDER BY timestamp DESC LIMIT ?;", (limit,)
            )
            return [
                {
                    "id": row[0],
                    "text": row[1],
                    "metadata": json.loads(row[2]) if row[2] else {},
                    "timestamp": row[3],
                }
                for row in rows
            ]

    def close(self):
        """Close database connections."""
        if self._use_postgres and self._connection_pool:
            self._connection_pool.closeall()
            logger.info("[SecureMemoryStore] PostgreSQL connection pool closed.")
        elif self._sqlite_conn:
            self._sqlite_conn.close()
            logger.info("[SecureMemoryStore] SQLite connection closed.")

    def __del__(self):
        self.close()
