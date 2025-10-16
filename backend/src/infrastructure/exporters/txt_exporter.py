from datetime import datetime

from ...domain.entities import Session
from ...domain.export_entities import IExporter


class TxtExporter(IExporter):
    def export(self, session: Session) -> bytes:
        lines = []

        lines.append("=" * 80)
        lines.append(f"SESSÃO DE CHAT: {session.session_id.value}")
        lines.append("=" * 80)
        lines.append(f"Criada em: {self._format_datetime(session.created_at)}")
        lines.append(
            f"Última atividade: {self._format_datetime(session.last_activity)}"
        )
        lines.append("")

        lines.append("=" * 80)
        lines.append("HISTÓRICO DE CONVERSAS")
        lines.append("=" * 80)
        lines.append("")

        for msg in session.message_history:
            role_label = "👤 USUÁRIO" if msg.role == "user" else "🤖 ASSISTENTE"
            timestamp = self._format_datetime(msg.timestamp)
            lines.append(f"[{timestamp}] {role_label}")
            lines.append(msg.content)
            lines.append("")

        if session.active_dataset:
            lines.append("=" * 80)
            lines.append("DATASET ATIVO")
            lines.append("=" * 80)
            lines.append(f"Consulta: {session.active_dataset.query}")
            lines.append(f"Registros: {session.active_dataset.row_count}")
            lines.append(f"Colunas: {', '.join(session.active_dataset.columns)}")
            lines.append("")

        lines.append("=" * 80)
        lines.append(f"Exportado em: {self._format_datetime(datetime.now())}")
        lines.append("=" * 80)

        content = "\n".join(lines)
        return content.encode("utf-8")

    def get_content_type(self) -> str:
        return "text/plain"

    def get_file_extension(self) -> str:
        return "txt"

    def _format_datetime(self, dt: datetime) -> str:
        return dt.strftime("%d/%m/%Y %H:%M:%S")
