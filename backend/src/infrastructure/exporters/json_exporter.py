import json
from datetime import datetime
from typing import Dict, Any

from ...domain.entities import Session
from ...domain.export_entities import IExporter


class JsonExporter(IExporter):
    def export(self, session: Session) -> bytes:
        data = self._build_export_data(session)
        json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        return json_str.encode("utf-8")

    def get_content_type(self) -> str:
        return "application/json"

    def get_file_extension(self) -> str:
        return "json"

    def _build_export_data(self, session: Session) -> Dict[str, Any]:
        return {
            "session_id": session.session_id.value,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata,
                }
                for msg in session.message_history
            ],
            "active_dataset": {
                "columns": session.active_dataset.columns,
                "row_count": session.active_dataset.row_count,
                "query": session.active_dataset.query,
            }
            if session.active_dataset
            else None,
            "export_info": {
                "format": "json",
                "exported_at": datetime.now().isoformat(),
                "version": "1.0",
            },
        }
