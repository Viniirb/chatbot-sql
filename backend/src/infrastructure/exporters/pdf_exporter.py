from datetime import datetime
from fpdf import FPDF

from ...domain.entities import Session
from ...domain.export_entities import IExporter


class PdfExporter(IExporter):
    def export(self, session: Session) -> bytes:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, f"Sessao de Chat: {session.session_id.value}", ln=True, align="C")
        
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 8, f"Criada em: {self._format_datetime(session.created_at)}", ln=True)
        pdf.cell(0, 8, f"Ultima atividade: {self._format_datetime(session.last_activity)}", ln=True)
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Historico de Conversas", ln=True)
        pdf.ln(3)
        
        for msg in session.message_history:
            role_label = "USUARIO" if msg.role == "user" else "ASSISTENTE"
            timestamp = self._format_datetime(msg.timestamp)
            
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, f"[{timestamp}] {role_label}", ln=True)
            
            pdf.set_font("Arial", "", 9)
            content = self._sanitize_text(msg.content)
            pdf.multi_cell(0, 5, content)
            pdf.ln(3)
        
        if session.active_dataset:
            pdf.ln(5)
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Dataset Ativo", ln=True)
            pdf.ln(3)
            
            pdf.set_font("Arial", "", 9)
            pdf.multi_cell(0, 5, f"Consulta: {self._sanitize_text(session.active_dataset.query)}")
            pdf.cell(0, 6, f"Registros: {session.active_dataset.row_count}", ln=True)
            pdf.multi_cell(0, 5, f"Colunas: {', '.join(session.active_dataset.columns)}")
        
        pdf.ln(10)
        pdf.set_font("Arial", "I", 8)
        pdf.cell(0, 6, f"Exportado em: {self._format_datetime(datetime.now())}", ln=True, align="C")
        
        return pdf.output(dest='S').encode('latin-1')

    def get_content_type(self) -> str:
        return "application/pdf"

    def get_file_extension(self) -> str:
        return "pdf"

    def _format_datetime(self, dt: datetime) -> str:
        return dt.strftime("%d/%m/%Y %H:%M:%S")

    def _sanitize_text(self, text: str) -> str:
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
