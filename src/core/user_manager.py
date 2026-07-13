from typing import List, Dict, Optional, Any
"""
User Management – handles user registration, authentication, and API key management.
"""

import os
import hashlib
import secrets
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# We'll use SQLite/PostgreSQL for user storage via SecureMemoryStore or separate table.
# For simplicity, we'll store users in a separate table in the same database.
# But we need direct DB access. We'll create a UserManager that uses psycopg2/sqlite3 directly.

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

import sqlite3

class UserManager:
    def __init__(self, db_path="data/memory.db", use_postgres=None):
        self.db_path = db_path
        self.use_postgres = use_postgres
        if use_postgres is None:
            use_postgres = os.getenv("PG_USE_POSTGRES", "false").lower() in ("true", "1", "yes")
        self.use_postgres = use_postgres and PSYCOPG2_AVAILABLE
        self._init_tables()

    def _get_connection(self):
        if self.use_postgres:
            import psycopg2
            conn = psycopg2.connect(
                host=os.getenv("PG_HOST", "localhost"),
                port=os.getenv("PG_PORT", 5432),
                database=os.getenv("PG_DATABASE", "jarvis"),
                user=os.getenv("PG_USER", "jarvis_user"),
                password=os.getenv("PG_PASSWORD", ""),
            )
            return conn
        else:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            return sqlite3.connect(self.db_path)

    def _init_tables(self):
        conn = self._get_connection()
        try:
            if self.use_postgres:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            username TEXT UNIQUE NOT NULL,
                            password_hash TEXT NOT NULL,
                            api_key TEXT UNIQUE NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    conn.commit()
            else:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        api_key TEXT UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
        finally:
            conn.close()

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        return salt + ":" + hashlib.sha256((salt + password).encode()).hexdigest()

    def _verify_password(self, password_hash: str, password: str) -> bool:
        salt, hash_val = password_hash.split(":")
        return hash_val == hashlib.sha256((salt + password).encode()).hexdigest()

    def _generate_api_key(self) -> str:
        return secrets.token_hex(32)

    def create_user(self, username: str, password: str) -> Optional[str]:
        """Create a new user and return their API key."""
        if not username or not password:
            return None
        try:
            api_key = self._generate_api_key()
            password_hash = self._hash_password(password)
            conn = self._get_connection()
            try:
                if self.use_postgres:
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO users (username, password_hash, api_key) VALUES (%s, %s, %s) RETURNING api_key;",
                            (username, password_hash, api_key)
                        )
                        result = cur.fetchone()
                        conn.commit()
                        return result[0]
                else:
                    cur = conn.execute(
                        "INSERT INTO users (username, password_hash, api_key) VALUES (?, ?, ?);",
                        (username, password_hash, api_key)
                    )
                    conn.commit()
                    return api_key
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"User creation failed: {e}")
            return None

    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        """Authenticate and return the user's API key."""
        try:
            conn = self._get_connection()
            try:
                if self.use_postgres:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute(
                            "SELECT password_hash, api_key FROM users WHERE username = %s;",
                            (username,)
                        )
                        row = cur.fetchone()
                else:
                    cur = conn.execute(
                        "SELECT password_hash, api_key FROM users WHERE username = ?;",
                        (username,)
                    )
                    row = cur.fetchone()
                if not row:
                    return None
                if self.use_postgres:
                    password_hash = row["password_hash"]
                    api_key = row["api_key"]
                else:
                    password_hash, api_key = row
                if self._verify_password(password_hash, password):
                    return api_key
                return None
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

    def get_user_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Get user info by API key."""
        try:
            conn = self._get_connection()
            try:
                if self.use_postgres:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute(
                            "SELECT id, username, api_key, created_at FROM users WHERE api_key = %s;",
                            (api_key,)
                        )
                        row = cur.fetchone()
                        return dict(row) if row else None
                else:
                    cur = conn.execute(
                        "SELECT id, username, api_key, created_at FROM users WHERE api_key = ?;",
                        (api_key,)
                    )
                    row = cur.fetchone()
                    if row:
                        return {"id": row[0], "username": row[1], "api_key": row[2], "created_at": row[3]}
                    return None
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"User lookup error: {e}")
            return None

    def list_users(self) -> List[Dict[str, Any]]:
        """List all users (admin only)."""
        try:
            conn = self._get_connection()
            try:
                if self.use_postgres:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute("SELECT id, username, api_key, created_at FROM users;")
                        rows = cur.fetchall()
                        return [dict(row) for row in rows]
                else:
                    cur = conn.execute("SELECT id, username, api_key, created_at FROM users;")
                    rows = cur.fetchall()
                    return [{"id": r[0], "username": r[1], "api_key": r[2], "created_at": r[3]} for r in rows]
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"List users error: {e}")
            return []
