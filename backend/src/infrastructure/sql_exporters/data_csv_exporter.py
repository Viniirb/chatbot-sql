import pandas as pd
import io


class DataCsvExporter:
    @staticmethod
    def export(data: list, columns: list) -> bytes:
        df = pd.DataFrame(data, columns=columns)
        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue().encode("utf-8")

    @staticmethod
    def get_content_type() -> str:
        return "text/csv"

    @staticmethod
    def get_file_extension() -> str:
        return "csv"
