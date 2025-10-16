import pandas as pd
import io


class DataExcelExporter:
    @staticmethod
    def export(data: list, columns: list) -> bytes:
        df = pd.DataFrame(data, columns=columns)
        output = io.BytesIO()
        df.to_excel(output, index=False)
        return output.getvalue()

    @staticmethod
    def get_content_type() -> str:
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    @staticmethod
    def get_file_extension() -> str:
        return "xlsx"
