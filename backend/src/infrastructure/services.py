import uuid
from typing import Dict, Optional, List
from threading import Lock

from ..domain.entities import Session, SessionId, ISessionRepository
from ..application.interfaces import ISessionService


class InMemorySessionRepository(ISessionRepository):
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._lock = Lock()

    def save(self, session: Session) -> None:
        with self._lock:
            self._sessions[session.session_id.value] = session

    def find_by_id(self, session_id: SessionId) -> Optional[Session]:
        with self._lock:
            return self._sessions.get(session_id.value)

    def delete(self, session_id: SessionId) -> None:
        with self._lock:
            self._sessions.pop(session_id.value, None)

    def find_expired_sessions(self, timeout_seconds: int) -> List[SessionId]:
        with self._lock:
            expired = []
            for session_id, session in self._sessions.items():
                if session.is_expired(timeout_seconds):
                    expired.append(SessionId(session_id))
            return expired


class SessionService(ISessionService):
    def __init__(self, repository: ISessionRepository, session_timeout: int = 3600):
        self._repository = repository
        self._session_timeout = session_timeout

    def create_session(self) -> Session:
        session_id = SessionId(str(uuid.uuid4()))
        session = Session(session_id)
        self._repository.save(session)
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        try:
            sid = SessionId(session_id)
            session = self._repository.find_by_id(sid)
            
            if session and session.is_expired(self._session_timeout):
                self._repository.delete(sid)
                return None
                
            return session
        except ValueError:
            return None

    def save_session(self, session: Session) -> None:
        self._repository.save(session)

    def cleanup_expired_sessions(self, timeout_seconds: int = 3600) -> None:
        expired_sessions = self._repository.find_expired_sessions(timeout_seconds)
        for session_id in expired_sessions:
            self._repository.delete(session_id)