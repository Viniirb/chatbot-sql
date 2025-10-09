import os
from typing import Dict

from ...domain.export_entities import IExporter, ExportFormat
from .json_exporter import JsonExporter
from .txt_exporter import TxtExporter
from .pdf_exporter import PdfExporter


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
