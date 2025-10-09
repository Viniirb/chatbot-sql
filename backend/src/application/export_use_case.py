from ..domain.entities import SessionId
from ..domain.export_entities import ExportFormat
from ..infrastructure.exporters import ExporterFactory
from .interfaces import IExportSessionUseCase, ExportSessionResponse, ISessionService


class ExportSessionUseCase(IExportSessionUseCase):
    def __init__(self, session_service: ISessionService, save_to_disk: bool = True):
        self._session_service = session_service
        self._save_to_disk = save_to_disk

    def execute(self, session_id: str, format: ExportFormat) -> ExportSessionResponse:
        session = self._session_service.get_session(session_id)
        # Se não existe, cria e persiste uma nova sessão com o ID fornecido
        if not session:
            from ..domain.entities import Session, SessionId
            session = Session(SessionId(session_id))
            self._session_service.save_session(session)
        exporter = ExporterFactory.get_exporter(format)
        content = exporter.export(session)
        content_type = exporter.get_content_type()
        file_extension = exporter.get_file_extension()
        filename = f"chat-{session_id}.{file_extension}"
        filepath = None
        if self._save_to_disk:
            try:
                filepath = ExporterFactory.save_export_to_disk(content, filename)
            except Exception:
                pass
        return ExportSessionResponse(
            content=content,
            content_type=content_type,
            filename=filename,
            filepath=filepath
        )
