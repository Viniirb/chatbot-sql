from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ..domain.entities import Session
from ..domain.export_entities import ExportFormat


@dataclass
class ProcessQueryRequest:
    query: str
    session_id: str
    request_id: Optional[str] = None
    client_message_id: Optional[str] = None


@dataclass
class ProcessQueryResponse:
    success: bool
    data: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    # Tipo categórico do erro (ex: QUOTA_ERROR, SERVER_ERROR, MODEL_ERROR)
    error_type: Optional[str] = None
    # Quando aplicável, número de segundos sugeridos para retry
    retry_after: Optional[int] = None
    session_id: Optional[str] = None
    context_used: bool = False


@dataclass
class CreateSessionResponse:
    session_id: str
    created_at: str


@dataclass
class SessionStatsResponse:
    session_id: str
    created_at: str
    last_activity: str
    message_count: int
    has_active_dataset: bool
    active_dataset_info: Optional[Dict[str, Any]] = None
    query_count: int = 0
    updated_at: Optional[str] = None


@dataclass
class UpdateSessionStatsRequest:
    """Request para atualizar estatísticas da sessão"""

    message_count: int
    query_count: int
    timestamp: str


@dataclass
class UpdateSessionStatsResponse:
    """Response da atualização de estatísticas"""

    session_id: str
    message_count: int
    query_count: int
    updated_at: str
    status: str = "synced"


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
    def update_session_stats(
        self, session_id: str, request: UpdateSessionStatsRequest
    ) -> UpdateSessionStatsResponse:
        pass

    @abstractmethod
    def cleanup_expired_sessions(self) -> None:
        pass


class IQueryProcessorService(ABC):
    @abstractmethod
    async def process_query(
        self, query: str, session: Session, request_id: Optional[str] = None
    ) -> str:
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


@dataclass
class ExportSessionResponse:
    content: bytes
    content_type: str
    filename: str
    filepath: Optional[str] = None


class IExportSessionUseCase(ABC):
    @abstractmethod
    def execute(
        self,
        session_id: str,
        format: ExportFormat,
        session_payload: Optional[dict] = None,
    ) -> ExportSessionResponse:
        pass
