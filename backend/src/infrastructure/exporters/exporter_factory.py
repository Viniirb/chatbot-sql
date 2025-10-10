import os
from typing import Dict

from ...domain.export_entities import IExporter, ExportFormat
from .json_exporter import JsonExporter
from .txt_exporter import TxtExporter
from .pdf_exporter import PdfExporter
import uuid
from datetime import datetime


class ExporterFactory:
    _exporters: Dict[ExportFormat, IExporter] = {
        ExportFormat.JSON: JsonExporter(),
        ExportFormat.TXT: TxtExporter(),
        ExportFormat.PDF: PdfExporter()
    }

    @classmethod
    def get_exporter(cls, format: ExportFormat) -> IExporter:
        exporter = cls._exporters.get(format)
        if not exporter:
            raise ValueError(f"Formato de exportação não suportado: {format}")
        return exporter
    
    @staticmethod
    def save_export_to_disk(content: bytes, filename: str, export_dir: str = "downloads/exports") -> str:
        os.makedirs(export_dir, exist_ok=True)
        filepath = os.path.join(export_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(content)
        
        return filepath

    @staticmethod
    def build_filename(kind: str, extension: str) -> str:
        """Build a deterministic but unique filename.

        Example: documentoPDF_20251010_160255_a1b2c3.pdf
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        short = uuid.uuid4().hex[:6]
        kind_sanitized = ''.join(c for c in kind if c.isalnum() or c in ('_', '-'))
        return f"{kind_sanitized}_{ts}_{short}.{extension}"
