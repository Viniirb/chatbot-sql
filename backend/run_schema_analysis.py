import sys
from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy import create_engine
from src.infrastructure.analyze.schema_analyzer import SchemaAnalyzer  # type: ignore
from src.infrastructure.cache import Cache  # type: ignore

ROOT = Path(__file__).resolve().parent
SRC_PATH = str(ROOT / "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

load_dotenv(ROOT / ".env")
DATABASE_URL = os.getenv("DATABASE_URL_ALTERNATIVE")
engine = create_engine(DATABASE_URL)
cache = Cache()
analyzer = SchemaAnalyzer(engine, cache=cache)

if __name__ == "__main__":
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"🔍 Iniciando análise do schema do banco... - {timestamp}")
        from sqlalchemy.engine import make_url

        db_name = make_url(DATABASE_URL).database if DATABASE_URL else None
        print(f"🗄️ Banco de dados: {db_name or '(desconhecido)'} - {timestamp}")
        print(
            f"⚠️ Observação: uso de cache ativo; reexecução atualizará o cache - {timestamp}"
        )
        analysis = analyzer.analyze_full_database(force_refresh=False)
        analyzer.export_analysis(analysis, output_path="schema_analysis.json")

        try:
            cache_path = getattr(cache, "persist_path", None)
            cache_path_str = (
                str(cache_path)
                if cache_path is not None
                else "(sem persistência configurada)"
            )
        except Exception:
            cache_path_str = "(desconhecido)"

        print(f"✅ Análise concluída. - {timestamp}")
        print(f"💾 Cache salvo em: {cache_path_str} - {timestamp}")
        print(f"📄 Análise exportada para: schema_analysis.json - {timestamp}")
        print(f"📄 Quality: {analysis.get('quality_score', 0)}/100 - {timestamp}")
        print(f"📊 Tabelas analisadas: {len(analysis.get('tables', {}))} - {timestamp}")
        print(
            f"🔍 Colunas analisadas: {sum(len(t.get('columns', [])) for t in analysis.get('tables', {}).values())} - {timestamp}"
        )
        print(f"⚠️ Issues encontradas: {len(analysis.get('issues', []))} - {timestamp}")
        print("📋 Recomendações:")
        for rec in analysis.get("recommendations", []):
            print(f" - {rec}")
    except Exception as e:
        print(f"❌ Erro durante a análise do schema: {e}")
        raise
