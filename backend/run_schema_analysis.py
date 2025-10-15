import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Ensure backend/src is on sys.path so imports work when running this script
ROOT = Path(__file__).resolve().parent
SRC_PATH = str(ROOT / "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from sqlalchemy import create_engine
from infrastructure.analyze.schema_analyzer import SchemaAnalyzer  # type: ignore
from infrastructure.cache import Cache  # type: ignore

# Carrega variáveis de ambiente do arquivo .env (se existir) na raiz de backend
load_dotenv(ROOT / ".env")
# Configuração do banco de dados (padrão pode ser sobrescrito por .env)
DATABASE_URL = os.getenv("DATABASE_URL_ALTERNATIVE") 
# Inicializa engine, cache e analyzer
engine = create_engine(DATABASE_URL)
cache = Cache()
analyzer = SchemaAnalyzer(engine, cache=cache)

if __name__ == "__main__":
    try:
        print(f"🔍 Iniciando análise do schema do banco...")
        from sqlalchemy.engine import make_url
        db_name = make_url(DATABASE_URL).database if DATABASE_URL else None
        print(f"🗄️ Banco de dados: {db_name or '(desconhecido)'}")
        print(f"⚠️ Observação: uso de cache ativo; reexecução atualizará o cache")
        analysis = analyzer.analyze_full_database(force_refresh=False)
        analyzer.export_analysis(analysis, output_path="schema_analysis.json")

        try:
            cache_path = getattr(cache, 'persist_path', None)
            cache_path_str = str(cache_path) if cache_path is not None else "(sem persistência configurada)"
        except Exception:
            cache_path_str = "(desconhecido)"

        print(f"✅ Análise concluída. Quality: {analysis.get('quality_score', 0)}/100 — cache atualizado: {cache_path_str}")
        print("📋 Recomendações:")
        for rec in analysis.get('recommendations', []):
            print(f" - {rec}")
    except Exception as e:
        # Seguir padrão de logs do projeto para erros
        print(f"❌ Erro durante a análise do schema: {e}")
        raise
