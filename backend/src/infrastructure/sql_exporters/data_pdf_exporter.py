from datetime import datetime
from fpdf import FPDF
from typing import List, Dict, Any
import os

class DataPdfExporter:
    """Gera PDFs com dados de consultas SQL (não relacionado a sessões de chat)"""
    @staticmethod
    def export(data: List[Dict[str, Any]], title: str = "Relatorio de Dados") -> bytes:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", "B", 16)
        sanitized_title = DataPdfExporter._sanitize_text(title)
        pdf.cell(0, 10, sanitized_title, ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "I", 10)
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        pdf.cell(0, 8, f"Gerado em: {timestamp}", ln=True)
        pdf.ln(5)
        if not data:
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, "Nenhum dado encontrado.", ln=True)
        else:
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, f"Total de registros: {len(data)}", ln=True)
            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "Dados:", ln=True)
            pdf.ln(2)
            for idx, record in enumerate(data, 1):
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 6, f"Registro #{idx}", ln=True)
                pdf.set_font("Arial", "", 9)
                for key, value in record.items():
                    sanitized_key = DataPdfExporter._sanitize_text(str(key))
                    sanitized_value = DataPdfExporter._sanitize_text(str(value))
                    pdf.cell(0, 5, f"  {sanitized_key}: {sanitized_value}", ln=True)
                pdf.ln(3)
        pdf.ln(10)
        pdf.set_font("Arial", "I", 8)
        pdf.cell(0, 6, "Documento gerado automaticamente pelo Chatbot SQL", ln=True, align="C")
        output = bytes(pdf.output(dest='S').encode('latin1'))
        return output
    @staticmethod
    def get_content_type() -> str:
        return "application/pdf"
    @staticmethod
    def get_file_extension() -> str:
        return "pdf"
    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Remove acentos e caracteres especiais para compatibilidade com fpdf"""
        replacements = {
            'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a',
            'é': 'e', 'ê': 'e',
            'í': 'i',
            'ó': 'o', 'õ': 'o', 'ô': 'o',
            'ú': 'u', 'ü': 'u',
            'ç': 'c',
            'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A',
            'É': 'E', 'Ê': 'E',
            'Í': 'I',
            'Ó': 'O', 'Õ': 'O', 'Ô': 'O',
            'Ú': 'U', 'Ü': 'U',
            'Ç': 'C'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
