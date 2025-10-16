from ..domain.entities import SessionId, Session, Message
from ..domain.export_entities import ExportFormat
from ..infrastructure.exporters import ExporterFactory
from .interfaces import IExportSessionUseCase, ExportSessionResponse, ISessionService
from typing import Optional, Dict, Any


class ExportSessionUseCase(IExportSessionUseCase):
    def __init__(self, session_service: ISessionService, save_to_disk: bool = True):
        self._session_service = session_service
        self._save_to_disk = save_to_disk

    def execute(
        self,
        session_id: str,
        format: ExportFormat,
        session_payload: Optional[Dict[str, Any]] = None,
    ) -> ExportSessionResponse:
        session: Optional[Session] = None

        if session_payload:
            sid_val = session_payload.get("id") or session_id
            sid = SessionId(sid_val)
            session = Session(sid)
            try:
                from datetime import datetime

                created = session_payload.get("createdAt")
                updated = session_payload.get("updatedAt")
                if created:
                    session._created_at = datetime.fromisoformat(created)
                if updated:
                    session._last_activity = datetime.fromisoformat(updated)
            except Exception:
                pass

            for m in session_payload.get("messages", []):
                try:
                    ts = m.get("timestamp")
                    from datetime import datetime

                    timestamp = datetime.fromisoformat(ts) if ts else None
                    msg = Message(
                        role=m.get("role", "user"),
                        content=m.get("content", ""),
                        timestamp=timestamp or session._last_activity,
                        metadata={},
                    )
                    session.add_message(msg)
                except Exception:
                    continue

            existing = self._session_service.get_session(sid.value)
            if not existing:
                try:
                    self._session_service.save_session(session)
                except Exception:
                    pass
        else:
            session = self._session_service.get_session(session_id)
            if not session:
                sid = SessionId(session_id)
                session = Session(sid)
                try:
                    self._session_service.save_session(session)
                except Exception:
                    pass

        exporter = ExporterFactory.get_exporter(format)
        content = exporter.export(session)
        content_type = exporter.get_content_type()
        file_extension = exporter.get_file_extension()
        if file_extension == "pdf":
            kind = "documentoPDF"
        elif file_extension in ("xls", "xlsx"):
            kind = "documentoExcel"
        elif file_extension == "csv":
            kind = "documentoCSV"
        else:
            kind = "documento"

        if session:
            session.stats.query_count += 1
            session.stats.updated_at = (
                session.stats.updated_at or session._last_activity
            )
            try:
                self._session_service.save_session(session)
            except Exception:
                pass
        try:
            from ..infrastructure.exporters.exporter_factory import (
                ExporterFactory as EF,
            )

            filename = EF.build_filename(kind, file_extension)
        except Exception:
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
            filepath=filepath,
        )
