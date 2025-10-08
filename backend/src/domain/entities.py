from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class QueryType(Enum):
    SELECT = "select"
    EXPORT_EXCEL = "export_excel"
    EXPORT_CSV = "export_csv"
    EXPORT_PDF = "export_pdf"


@dataclass(frozen=True)
class SessionId:
    value: str

    def __post_init__(self):
        if not self.value or len(self.value.strip()) == 0:
            raise ValueError("SessionId cannot be empty")


@dataclass(frozen=True)
class QueryResult:
    query: str
    result_data: str
    timestamp: datetime
    row_count: int
    columns: List[str]
    query_type: QueryType


@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]


class Session:
    def __init__(self, session_id: SessionId):
        self._session_id = session_id
        self._created_at = datetime.now()
        self._last_activity = datetime.now()
        self._message_history: List[Message] = []
        self._query_results: List[QueryResult] = []
        self._active_dataset: Optional[QueryResult] = None

    @property
    def session_id(self) -> SessionId:
        return self._session_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def last_activity(self) -> datetime:
        return self._last_activity

    @property
    def message_history(self) -> List[Message]:
        return self._message_history.copy()

    @property
    def active_dataset(self) -> Optional[QueryResult]:
        return self._active_dataset

    def add_message(self, message: Message) -> None:
        self._message_history.append(message)
        self._last_activity = datetime.now()

    def add_query_result(self, query_result: QueryResult) -> None:
        self._query_results.append(query_result)
        if len(self._query_results) > 5:
            self._query_results.pop(0)
        
        if query_result.row_count > 0:
            self._active_dataset = query_result
        
        self._last_activity = datetime.now()

    def is_expired(self, timeout_seconds: int) -> bool:
        time_diff = datetime.now() - self._last_activity
        return time_diff.total_seconds() > timeout_seconds

    def get_context_summary(self) -> str:
        if not self._message_history:
            return ""
        
        context_parts = []
        recent_messages = self._message_history[-6:]
        
        for msg in recent_messages:
            role_emoji = "🙋‍♂️" if msg.role == "user" else "🤖"
            content_preview = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            context_parts.append(f"{role_emoji} {content_preview}")
        
        if self._active_dataset:
            columns_preview = ', '.join(self._active_dataset.columns[:5])
            if len(self._active_dataset.columns) > 5:
                columns_preview += "..."
            
            context_parts.append(
                f"\n📊 DATASET ATIVO: {self._active_dataset.row_count} registros, "
                f"colunas: {columns_preview}"
            )
        
        return "\n".join(context_parts)


class IChatAgent(ABC):
    @abstractmethod
    def process_query(self, query: str) -> str:
        pass


class ISessionRepository(ABC):
    @abstractmethod
    def save(self, session: Session) -> None:
        pass

    @abstractmethod
    def find_by_id(self, session_id: SessionId) -> Optional[Session]:
        pass

    @abstractmethod
    def delete(self, session_id: SessionId) -> None:
        pass

    @abstractmethod
    def find_expired_sessions(self, timeout_seconds: int) -> List[SessionId]:
        pass


class IQueryContextEnhancer(ABC):
    @abstractmethod
    def enhance_query(self, query: str, session: Session) -> str:
        pass

    @abstractmethod
    def needs_context(self, query: str) -> bool:
        pass