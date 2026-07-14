"""
Session Manager – In-memory session storage with user mapping.
Governed by INTERACTION_MODEL.md
"""

import logging
from typing import Dict, Optional, List
from uuid import UUID, uuid4, uuid5, NAMESPACE_DNS
from datetime import datetime

from src.interaction.models import Session, SessionState, Message, Tone

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages user sessions.
    In-memory for now; will later persist to KnowledgeStore.
    """

    # Use a constant namespace for deterministic UUID generation per user
    NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

    def __init__(self):
        self._sessions: Dict[UUID, Session] = {}
        self._user_to_session: Dict[str, UUID] = {}
        logger.info("[SessionManager] Initialized (in-memory).")

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
            return session
        else:
            # Create new session with the provided UUID (should be deterministic)
            session = Session(session_id=session_id, user_id=user_id)
            self._sessions[session_id] = session
            self._user_to_session[user_id] = session_id
            logger.info(f"[SessionManager] Created session {session_id} for user {user_id} (provided UUID)")
            return session

    def update_state(self, session_id: UUID, state: SessionState) -> bool:
        if session_id in self._sessions:
            self._sessions[session_id].state = state
            self._sessions[session_id].updated_at = datetime.now()
            return True
        return False

    def add_message(self, session_id: UUID, message: Message) -> bool:
        if session_id in self._sessions:
            self._sessions[session_id].conversation.append(message)
            self._sessions[session_id].updated_at = datetime.now()
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
            return True
        return False

    def delete_session(self, session_id: UUID) -> bool:
        if session_id in self._sessions:
            # Remove from user mapping
            session = self._sessions[session_id]
            for user_id, sid in list(self._user_to_session.items()):
                if sid == session_id:
                    del self._user_to_session[user_id]
                    break
            del self._sessions[session_id]
            logger.info(f"[SessionManager] Deleted session {session_id}")
            return True
        return False

    def get_all_sessions(self) -> List[Session]:
        return list(self._sessions.values())

    # ---- Persistence (stub) ----
    def save_to_knowledge_store(self):
        """Will be implemented later to persist sessions."""
        pass

    def load_from_knowledge_store(self):
        """Will be implemented later to restore sessions."""
        pass
