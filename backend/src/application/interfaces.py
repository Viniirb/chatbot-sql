from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from ..domain.entities import Session, SessionId, QueryResult, Message


@dataclass
class ProcessQueryRequest:
    query: str
    session_id: str


@dataclass
class ProcessQueryResponse:
    success: bool
    data: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    session_id: Optional[str] = None
    context_used: bool = False


@dataclass
class CreateSessionResponse:
    session_id: str


@dataclass
class SessionStatsResponse:
    session_id: str
    created_at: float
    last_activity: float
    message_count: int
    has_active_dataset: bool
    active_dataset_info: Optional[Dict[str, Any]] = None


class IProcessQueryUseCase(ABC):
    @abstractmethod
    async def execute(self, request: ProcessQueryRequest) -> ProcessQueryResponse:
        pass


class ISessionManagementUseCase(ABC):
    @abstractmethod
    def create_session(self) -> CreateSessionResponse:
        pass

    @abstractmethod
    def get_session_stats(self, session_id: str) -> Optional[SessionStatsResponse]:
        pass

    @abstractmethod
    def cleanup_expired_sessions(self) -> None:
        pass


class IQueryProcessorService(ABC):
    @abstractmethod
    async def process_query(self, query: str, session: Session) -> str:
        pass


class ISessionService(ABC):
    @abstractmethod
    def create_session(self) -> Session:
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Session]:
        pass

    @abstractmethod
    def save_session(self, session: Session) -> None:
        pass

    @abstractmethod
    def cleanup_expired_sessions(self, timeout_seconds: int = 3600) -> None:
        pass