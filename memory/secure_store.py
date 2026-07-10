"""
Secure Memory Store – PostgreSQL (production) with SQLite fallback.
Supports user isolation via `user_id` column.
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from datetime import datetime

# ---------- PostgreSQL ----------
try:
    import psycopg2
    from psycopg2 import pool, OperationalError, sql
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

# ---------- pgvector ----------
try:
    from pgvector.psycopg2 import register_vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False

# ---------- SQLite ----------
import sqlite3

# ---------- Embedding ----------
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    SentenceTransformer = None

from config.secure_config import AppConfig

logger = logging.getLogger(__name__)


class SecureMemoryStore:
    """
    Dual‑backend memory store with PostgreSQL as primary.
    Supports user isolation via `user_id` column.
    """

    def __init__(self, db_path: str = "data/memory.db", use_postgres: Optional[bool] = None, embed_model: str = "all-MiniLM-L6-v2"):
        self.db_path = db_path
        self._use_postgres = self._determine_backend(use_postgres)
        self._embed_model = None
        self._connection_pool = None
        self._sqlite_conn = None

        # Load embedding model (if available)
        if EMBEDDING_AVAILABLE:
            try:
                self._embed_model = SentenceTransformer(embed_model)
                logger.info(f"[SecureMemoryStore] Embedding model '{embed_model}' loaded.")
            except Exception as e:
                logger.warning(f"[SecureMemoryStore] Failed to load embedding model: {e}")
                self._embed_model = None

        self._init_backend()

    def _determine_backend(self, use_postgres: Optional[bool]) -> bool:
        if use_postgres is not None:
            return use_postgres
        env_val = os.getenv("PG_USE_POSTGRES", "false").lower()
        return env_val in ("true", "1", "yes")

    def _init_backend(self):
        if self._use_postgres and PSYCOPG2_AVAILABLE:
            self._init_postgres()
        else:
            if self._use_postgres and not PSYCOPG2_AVAILABLE:
                logger.warning("psycopg2 not installed. Falling back to SQLite.")
            self._use_postgres = False
            self._init_sqlite()

    # ---------- PostgreSQL ----------
    def _init_postgres(self):
        try:
            self._connection_pool = pool.SimpleConnectionPool(
                int(os.getenv("PG_POOL_MIN", "1")),
                int(os.getenv("PG_POOL_MAX", "20")),
                host=os.getenv("PG_HOST", "localhost"),
                port=os.getenv("PG_PORT", 5432),
                database=os.getenv("PG_DATABASE", "jarvis"),
                user=os.getenv("PG_USER", "jarvis_user"),
                password=os.getenv("PG_PASSWORD", ""),
            )
            if PGVECTOR_AVAILABLE:
                with self._get_postgres_connection() as conn:
                    register_vector(conn)
                    with conn.cursor() as cur:
                        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                        conn.commit()
                        logger.info("[SecureMemoryStore] pgvector extension enabled.")
            self._create_postgres_tables()
            logger.info("[SecureMemoryStore] PostgreSQL connection pool established.")
        except Exception as e:
            logger.error(f"[SecureMemoryStore] PostgreSQL init failed: {e}. Falling back to SQLite.")
            self._use_postgres = False
            self._init_sqlite()

    def _create_postgres_tables(self):
        with self._get_postgres_connection() as conn:
            with conn.cursor() as cur:
                if PGVECTOR_AVAILABLE:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS memory (
                            id SERIAL PRIMARY KEY,
                            user_id TEXT NOT NULL DEFAULT 'default',
                            text TEXT NOT NULL,
                            metadata JSONB,
                            embedding vector(384),
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                else:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS memory (
                            id SERIAL PRIMARY KEY,
                            user_id TEXT NOT NULL DEFAULT 'default',
                            text TEXT NOT NULL,
                            metadata JSONB,
                            embedding JSONB,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                # Add column if not exists (for migrations)
                try:
                    cur.execute("ALTER TABLE memory ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'default';")
                except Exception:
                    pass
                cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_user_id ON memory(user_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_text ON memory(text);")
                if PGVECTOR_AVAILABLE:
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_embedding ON memory USING ivfflat (embedding vector_cosine_ops);")
                conn.commit()

    @contextmanager
    def _get_postgres_connection(self):
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

    def _execute_postgres(self, query: str, params: tuple = (), retries: int = 3):
        for attempt in range(retries):
            try:
                with self._get_postgres_connection() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute(query, params)
                        if query.strip().upper().startswith("SELECT") or "RETURNING" in query.upper():
                            return cur.fetchall()
                        conn.commit()
                        return cur.rowcount
            except OperationalError as e:
                if "deadlock" in str(e).lower() or "serialization" in str(e).lower():
                    wait = (2 ** attempt) * 0.1
                    logger.warning(f"Retrying PostgreSQL query (attempt {attempt+1}) after {wait:.2f}s")
                    time.sleep(wait)
                    continue
                raise
        raise RuntimeError(f"PostgreSQL query failed after {retries} retries.")

    # ---------- SQLite Fallback ----------
    def _init_sqlite(self):
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._sqlite_conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._sqlite_conn.execute("PRAGMA journal_mode=WAL;")
            self._sqlite_conn.execute("PRAGMA synchronous=NORMAL;")
            self._sqlite_conn.execute("PRAGMA cache_size=-20000;")
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
                    user_id TEXT NOT NULL DEFAULT 'default',
                    text TEXT NOT NULL,
                    metadata TEXT,
                    embedding TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            try:
                self._sqlite_conn.execute("ALTER TABLE memory ADD COLUMN user_id TEXT NOT NULL DEFAULT 'default';")
            except Exception:
                pass
            self._sqlite_conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_user_id ON memory(user_id);")
            self._sqlite_conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_text ON memory(text);")

    def _execute_sqlite(self, query: str, params: tuple = (), retries: int = 3):
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

    # ---------- Embedding Helpers ----------
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        if self._embed_model is None:
            return None
        try:
            if len(text) > 10000:
                text = text[:10000]
            embedding = self._embed_model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")
            return None

    def _embedding_to_json(self, embedding: Optional[List[float]]) -> Optional[str]:
        if embedding is None:
            return None
        return json.dumps(embedding)

    def _json_to_embedding(self, json_str: Optional[str]) -> Optional[List[float]]:
        if not json_str:
            return None
        try:
            return json.loads(json_str)
        except:
            return None

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x*y for x,y in zip(a,b))
        return max(0.0, min(1.0, dot))

    # ---------- Public API with user_id ----------
    def insert(self, text: str, metadata: Optional[Dict] = None, user_id: str = "default") -> int:
        if metadata is None:
            metadata = {}
        embedding = self._get_embedding(text)
        embedding_json = self._embedding_to_json(embedding)

        if self._use_postgres:
            if PGVECTOR_AVAILABLE and embedding is not None:
                result = self._execute_postgres(
                    "INSERT INTO memory (user_id, text, metadata, embedding) VALUES (%s, %s, %s, %s) RETURNING id;",
                    (user_id, text, json.dumps(metadata), embedding)
                )
                return result[0]["id"]
            else:
                result = self._execute_postgres(
                    "INSERT INTO memory (user_id, text, metadata, embedding) VALUES (%s, %s, %s, %s) RETURNING id;",
                    (user_id, text, json.dumps(metadata), embedding_json)
                )
                return result[0]["id"]
        else:
            result = self._execute_sqlite(
                "INSERT INTO memory (user_id, text, metadata, embedding) VALUES (?, ?, ?, ?);",
                (user_id, text, json.dumps(metadata), embedding_json)
            )
            last_id = self._execute_sqlite("SELECT last_insert_rowid();")[0][0]
            return last_id

    def search_by_text(self, search_term: str, limit: int = 10, user_id: str = "default") -> List[Dict[str, Any]]:
        if self._use_postgres:
            results = self._execute_postgres(
                "SELECT id, user_id, text, metadata, timestamp FROM memory WHERE user_id = %s AND text ILIKE %s ORDER BY timestamp DESC LIMIT %s;",
                (user_id, f"%{search_term}%", limit)
            )
            return [
                {
                    "id": r["id"],
                    "user_id": r["user_id"],
                    "text": r["text"],
                    "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
                    "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
                }
                for r in results
            ]
        else:
            rows = self._execute_sqlite(
                "SELECT id, user_id, text, metadata, timestamp FROM memory WHERE user_id = ? AND text LIKE ? ORDER BY timestamp DESC LIMIT ?;",
                (user_id, f"%{search_term}%", limit)
            )
            return [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "text": row[2],
                    "metadata": json.loads(row[3]) if row[3] else {},
                    "timestamp": row[4],
                }
                for row in rows
            ]

    def search_semantic(self, query: str, limit: int = 5, threshold: float = 0.6, user_id: str = "default") -> List[Dict[str, Any]]:
        if self._embed_model is None:
            return self.search_by_text(query, limit, user_id)
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            return self.search_by_text(query, limit, user_id)

        if self._use_postgres and PGVECTOR_AVAILABLE:
            results = self._execute_postgres(
                """
                SELECT id, user_id, text, metadata, timestamp, 1 - (embedding <=> %s::vector) as similarity
                FROM memory
                WHERE user_id = %s AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                (query_embedding, user_id, query_embedding, limit)
            )
            return [
                {
                    "id": r["id"],
                    "user_id": r["user_id"],
                    "text": r["text"],
                    "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
                    "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
                    "similarity": r["similarity"],
                }
                for r in results if r["similarity"] >= threshold
            ]
        else:
            # Manual computation
            if self._use_postgres:
                rows = self._execute_postgres(
                    "SELECT id, user_id, text, metadata, embedding, timestamp FROM memory WHERE user_id = %s AND embedding IS NOT NULL;",
                    (user_id,)
                )
            else:
                rows = self._execute_sqlite(
                    "SELECT id, user_id, text, metadata, embedding, timestamp FROM memory WHERE user_id = ? AND embedding IS NOT NULL;",
                    (user_id,)
                )

            results = []
            for row in rows:
                if self._use_postgres:
                    emb_json = row.get("embedding")
                    if isinstance(emb_json, str):
                        emb = json.loads(emb_json)
                    else:
                        emb = emb_json
                    record = {
                        "id": row["id"],
                        "user_id": row["user_id"],
                        "text": row["text"],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                        "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
                    }
                else:
                    emb = self._json_to_embedding(row[4])
                    record = {
                        "id": row[0],
                        "user_id": row[1],
                        "text": row[2],
                        "metadata": json.loads(row[3]) if row[3] else {},
                        "timestamp": row[5],
                    }
                if emb is None:
                    continue
                sim = self._cosine_similarity(query_embedding, emb)
                if sim >= threshold:
                    record["similarity"] = sim
                    results.append(record)
            results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            return results[:limit]

    def delete_by_id(self, record_id: int, user_id: str = "default") -> bool:
        if self._use_postgres:
            rows_affected = self._execute_postgres(
                "DELETE FROM memory WHERE id = %s AND user_id = %s;", (record_id, user_id)
            )
            return rows_affected > 0
        else:
            rows_affected = self._execute_sqlite(
                "DELETE FROM memory WHERE id = ? AND user_id = ?;", (record_id, user_id)
            )
            return rows_affected > 0

    def get_all(self, limit: int = 1000, user_id: str = "default") -> List[Dict[str, Any]]:
        if self._use_postgres:
            results = self._execute_postgres(
                "SELECT id, user_id, text, metadata, timestamp FROM memory WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s;",
                (user_id, limit)
            )
            return [
                {
                    "id": r["id"],
                    "user_id": r["user_id"],
                    "text": r["text"],
                    "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
                    "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
                }
                for r in results
            ]
        else:
            rows = self._execute_sqlite(
                "SELECT id, user_id, text, metadata, timestamp FROM memory WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?;",
                (user_id, limit)
            )
            return [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "text": row[2],
                    "metadata": json.loads(row[3]) if row[3] else {},
                    "timestamp": row[4],
                }
                for row in rows
            ]

    def close(self):
        if self._use_postgres and self._connection_pool:
            self._connection_pool.closeall()
            logger.info("[SecureMemoryStore] PostgreSQL connection pool closed.")
        elif self._sqlite_conn:
            self._sqlite_conn.close()
            logger.info("[SecureMemoryStore] SQLite connection closed.")

    def __del__(self):
        self.close()

