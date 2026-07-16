"""
Session Manager – In-memory session storage with persistence to KnowledgeStore.
Governed by INTERACTION_MODEL.md
"""

import logging
import json
from typing import Dict, Optional, List, Any
from uuid import UUID, uuid5, NAMESPACE_DNS
from datetime import datetime

from src.interaction.models import Session, SessionState, Message, Tone

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages user sessions with persistence to SecureMemoryStore.
    """

    # Use a constant namespace for deterministic UUID generation per user
    NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

    def __init__(self, secure_memory=None):
        self._sessions: Dict[UUID, Session] = {}
        self._user_to_session: Dict[str, UUID] = {}
        self._secure_memory = secure_memory
        self._loaded = False
        logger.info("[SessionManager] Initialized (in-memory).")

    def set_secure_memory(self, secure_memory):
        """Inject secure memory for persistence."""
        self._secure_memory = secure_memory
        logger.info("[SessionManager] SecureMemoryStore attached.")

    # ---------- Persistence ----------
    def _session_key(self, session_id: UUID) -> str:
        return f"session:{session_id}"

    def _save_session(self, session: Session) -> None:
        """Save a session to the KnowledgeStore."""
        if not self._secure_memory:
            return
        try:
            data = session.model_dump(mode='json')
            self._secure_memory.insert(
                text=f"SESSION: {session.session_id}",
                metadata={
                    "type": "session",
                    "session_id": str(session.session_id),
                    "user_id": session.user_id,
                    "data": json.dumps(data),
                },
                user_id=session.user_id,
            )
            logger.debug(f"[SessionManager] Saved session {session.session_id}")
        except Exception as e:
            logger.error(f"[SessionManager] Failed to save session {session.session_id}: {e}")

    def _load_session(self, session_id: UUID) -> Optional[Session]:
        """Load a session from the KnowledgeStore."""
        if not self._secure_memory:
            return None
        try:
            results = self._secure_memory.search_by_text(
                f"SESSION: {session_id}",
                limit=1,
                user_id="system"
            )
            if not results:
                return None
            metadata = results[0].get("metadata", {})
            data_str = metadata.get("data")
            if not data_str:
                return None
            data = json.loads(data_str)
            session = Session(**data)
            return session
        except Exception as e:
            logger.error(f"[SessionManager] Failed to load session {session_id}: {e}")
            return None

    def load_all_sessions(self) -> int:
        """Load all sessions from the KnowledgeStore."""
        if not self._secure_memory:
            logger.warning("[SessionManager] No secure memory; skipping load.")
            return 0
        try:
            results = self._secure_memory.search_by_text(
                "SESSION:",
                limit=1000,  # reasonable limit
                user_id="system"
            )
            count = 0
            for record in results:
                metadata = record.get("metadata", {})
                data_str = metadata.get("data")
                if not data_str:
                    continue
                try:
                    data = json.loads(data_str)
                    session = Session(**data)
                    self._sessions[session.session_id] = session
                    self._user_to_session[session.user_id] = session.session_id
                    count += 1
                except Exception as e:
                    logger.warning(f"[SessionManager] Failed to restore session: {e}")
            self._loaded = True
            logger.info(f"[SessionManager] Loaded {count} sessions from KnowledgeStore.")
            return count
        except Exception as e:
            logger.error(f"[SessionManager] Failed to load sessions: {e}")
            return 0

    # ---------- Core Methods ----------
    def get_session_for_user(self, user_id: str) -> UUID:
        """
        Retrieve the session UUID for a given user.
        If the user has no session, create one with a deterministic UUID.
        """
        if user_id in self._user_to_session:
            session_id = self._user_to_session[user_id]
            # Ensure the session still exists (it should)
            if session_id in self._sessions:
                return session_id
            # If the session was deleted, remove mapping and recreate
            del self._user_to_session[user_id]

        # Create a new session with a deterministic UUID based on user_id
        session_id = uuid5(self.NAMESPACE, user_id)
        session = Session(session_id=session_id, user_id=user_id)
        self._sessions[session_id] = session
        self._user_to_session[user_id] = session_id
        self._save_session(session)
        logger.info(f"[SessionManager] Created session {session_id} for user {user_id}")
        return session_id

    def get_or_create(self, session_id: UUID, user_id: str) -> Session:
        """
        Retrieve an existing session by UUID or create a new one.
        Used when we have a session UUID externally.
        """
        if session_id in self._sessions:
            session = self._sessions[session_id]
            # Update the user mapping
            self._user_to_session[user_id] = session_id
            session.updated_at = datetime.now()
            self._save_session(session)
            return session
        else:
            # Try to load from persistent storage
            session = self._load_session(session_id)
            if session:
                self._sessions[session_id] = session
                self._user_to_session[user_id] = session_id
                logger.info(f"[SessionManager] Restored session {session_id} for user {user_id}")
                return session

            # Create new session with the provided UUID (should be deterministic)
            session = Session(session_id=session_id, user_id=user_id)
            self._sessions[session_id] = session
            self._user_to_session[user_id] = session_id
            self._save_session(session)
            logger.info(f"[SessionManager] Created session {session_id} for user {user_id} (provided UUID)")
            return session

    def update_state(self, session_id: UUID, state: SessionState) -> bool:
        if session_id in self._sessions:
            self._sessions[session_id].state = state
            self._sessions[session_id].updated_at = datetime.now()
            self._save_session(self._sessions[session_id])
            return True
        return False

    def add_message(self, session_id: UUID, message: Message) -> bool:
        if session_id in self._sessions:
            self._sessions[session_id].conversation.append(message)
            self._sessions[session_id].updated_at = datetime.now()
            self._save_session(self._sessions[session_id])
            return True
        return False

    def get_conversation(self, session_id: UUID, limit: int = 20) -> List[Message]:
        if session_id in self._sessions:
            conv = self._sessions[session_id].conversation
            return conv[-limit:] if limit > 0 else conv
        return []

    def set_tone(self, session_id: UUID, tone: Tone) -> bool:
        if session_id in self._sessions:
            self._sessions[session_id].tone = tone
            self._sessions[session_id].updated_at = datetime.now()
            self._save_session(self._sessions[session_id])
            return True
        return False

    def delete_session(self, session_id: UUID) -> bool:
        if session_id in self._sessions:
            session = self._sessions[session_id]
            for user_id, sid in list(self._user_to_session.items()):
                if sid == session_id:
                    del self._user_to_session[user_id]
                    break
            del self._sessions[session_id]
            logger.info(f"[SessionManager] Deleted session {session_id}")
            # Optionally remove from persistent storage (not implemented)
            return True
        return False

    def get_all_sessions(self) -> List[Session]:
        return list(self._sessions.values())
