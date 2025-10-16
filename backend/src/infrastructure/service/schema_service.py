from sqlalchemy import create_engine
from ..analyze.schema_analyzer import SchemaAnalyzer
from ..cache import Cache
import os


class SchemaService:
    """
    Serviço para acessar análise de schema e cache em todo o backend.
    """

    def __init__(self, database_url=None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "mssql+pyodbc://sa:your_password_here@localhost:1433/chatbot_db?driver=ODBC+Driver+17+for+SQL+Server",
        )
        self.engine = create_engine(self.database_url)
        self.cache = Cache()
        self.analyzer = SchemaAnalyzer(self.engine, cache=self.cache)

    def get_schema_analysis(self, force_refresh: bool = False):
        """
        Retorna a análise do schema do banco. Por padrão usa o cache salvo.
        Para forçar reexecução setar force_refresh=True.
        """
        return self.analyzer.analyze_full_database(force_refresh=force_refresh)

    def get_table_info(self, table_name, force_refresh: bool = False):
        """
        Retorna informações detalhadas de uma tabela específica.
        """
        analysis = self.get_schema_analysis(force_refresh=force_refresh)
        return analysis["tables"].get(table_name)

    def get_quality_score(self, force_refresh: bool = False):
        """
        Retorna o score de qualidade geral do banco.
        """
        analysis = self.get_schema_analysis(force_refresh=force_refresh)
        return analysis.get("quality_score", 0)

    def get_recommendations(self, force_refresh: bool = False):
        """
        Retorna recomendações de melhorias do schema.
        """
        analysis = self.get_schema_analysis(force_refresh=force_refresh)
        return analysis.get("recommendations", [])
