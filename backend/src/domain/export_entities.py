from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass

from .entities import Session


class ExportFormat(Enum):
    PDF = "pdf"
    JSON = "json"
    TXT = "txt"


@dataclass
class ExportRequest:
    session_id: str
    format: ExportFormat


class IExporter(ABC):
    @abstractmethod
    def export(self, session: Session) -> bytes:
        pass

    @abstractmethod
    def get_content_type(self) -> str:
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        pass
