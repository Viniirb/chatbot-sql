from sqlalchemy import inspect, MetaData, Table, select
from typing import Dict, List, Any
import pandas as pd
from datetime import datetime
from pathlib import Path
import json
import yaml
import os
from ..cache import Cache
from concurrent.futures import ThreadPoolExecutor, as_completed

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class SchemaAnalyzer:
    """Analisa e documenta schemas de bancos de dados"""

    def __init__(self, engine, llm_client=None, cache: Cache = None):
        self.engine = engine
        self.inspector = inspect(engine)
        self.llm_client = llm_client
        self.metadata = MetaData()
        self.cache = cache or Cache()
        self.conventions = self._load_conventions()

    def analyze_full_database(
        self, force_refresh: bool = False, max_workers: int = 8
    ) -> Dict[str, Any]:
        """Análise completa do banco de dados com cache e processamento paralelo."""
        cache_key = f"schema_analysis_{self.engine.url.database}"
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                print(f"♻️ Retornando análise a partir do cache - {timestamp}")
                return cached

        dialect = getattr(self.engine.dialect, "name", "unknown")
        print(f"🔍 Iniciando análise completa do banco de dados - {timestamp}")
        print(f"🗄️ Dialeto do banco: {dialect} - {timestamp}")

        tables = self.inspector.get_table_names()
        print(f"📚 Total de tabelas encontradas: {len(tables)} - {timestamp}")

        analysis = {
            "database_info": self._get_database_info(tables),
            "tables": {},
            "relationships": self._analyze_relationships(tables),
            "quality_score": 0,
            "recommendations": [],
            "timestamp": datetime.now().isoformat(),
        }

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_table = {
                executor.submit(self._analyze_table, table_name): table_name
                for table_name in tables
            }

            for i, future in enumerate(as_completed(future_to_table), start=1):
                table_name = future_to_table[future]
                try:
                    table_analysis = future.result()
                    analysis["tables"][table_name] = table_analysis
                    print(
                        f"  → [{i}/{len(tables)}] Análise da tabela '{table_name}' concluída. - {timestamp}"
                    )
                except Exception as exc:
                    print(
                        f"  → [{i}/{len(tables)}] ERRO ao analisar a tabela '{table_name}': {exc} - {timestamp}"
                    )
                    analysis["tables"][table_name] = {"error": str(exc)}

        analysis["quality_score"] = self._calculate_overall_quality(analysis["tables"])
        analysis["recommendations"] = self._generate_recommendations(analysis)

        self.cache.set(cache_key, analysis)
        return analysis

    def _get_database_info(self, tables: List[str]) -> Dict[str, Any]:
        return {
            "dialect": self.engine.dialect.name,
            "driver": self.engine.driver,
            "database_name": self.engine.url.database,
            "table_count": len(tables),
        }

    def _load_conventions(self, path: str = None) -> Dict[str, Any]:
        """Carrega arquivo YAML com convenções de prefixos para tabelas/colunas.

        Procura por `backend/src/infrastructure/yaml/database_conventions.yaml` por padrão.
        Retorna estrutura {'tables': [...], 'columns': [...]} ou {} se não encontrado/erro.
        """
        try:
            if not path:
                base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                # base -> backend/src/infrastructure
                path = os.path.join(base, "yaml", "database_conventions.yaml")
            if not os.path.exists(path):
                return {}
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            # Normaliza para facilitar busca
            conv = {"tables": [], "columns": []}
            root = data.get("database_conventions") or {}
            for k in ("tables", "columns"):
                items = root.get(k, [])
                # Ensure prefix is uppercase for matching
                for it in items:
                    it = dict(it)
                    it["prefix"] = it.get("prefix", "").upper()
                    conv[k].append(it)
            return conv
        except Exception:
            return {}

    def _suggest_from_prefix(self, name: str, kind: str) -> Dict[str, Any]:
        """Tenta casar o nome (table/column) com um prefixo conhecido e retorna a convenção encontrada.

        kind: 'tables' ou 'columns'
        Retorna dict com keys prefix, layer, description/suggested_meaning ou None.
        """
        if not self.conventions:
            return {}
        name_up = (name or "").upper()
        candidates = self.conventions.get(kind, [])
        # Ordena por comprimento do prefixo para encontrar match mais específico primeiro
        candidates = sorted(candidates, key=lambda x: len(x.get("prefix", "")), reverse=True)
        for c in candidates:
            p = c.get("prefix", "")
            if not p:
                continue
            if name_up.startswith(p):
                return c
        return {}

    def _analyze_table(self, table_name: str) -> Dict[str, Any]:
        print(f"    ↳ Analisando '{table_name}'...")
        columns = self.inspector.get_columns(table_name)
        pk = self.inspector.get_pk_constraint(table_name)
        fks = self.inspector.get_foreign_keys(table_name)
        indexes = self.inspector.get_indexes(table_name)
        sample_data = self._get_sample_data(table_name, limit=100)

        # Analisa colunas primeiro para anexar convenções por coluna
        analyzed_columns = self._analyze_columns(columns, sample_data)

        # Detecta convenção por prefixo para a tabela
        table_conv = self._suggest_from_prefix(table_name, "tables")

        table_analysis = {
            "columns": analyzed_columns,
            "primary_key": pk.get("constrained_columns", []),
            "foreign_keys": fks,
            "indexes": [idx["name"] for idx in indexes],
            "data_quality": self._assess_data_quality(sample_data),
            # Passa as colunas já analisadas para avaliação de nomenclatura
            "naming_quality": self._assess_naming_quality(table_name, analyzed_columns),
            "convention": table_conv,
            "llm_documentation": None,
        }

        if self.llm_client:
            table_analysis["llm_documentation"] = self._generate_llm_documentation(
                table_name, table_analysis
            )

        return table_analysis

    def _analyze_relationships(self, tables: List[str]) -> List[Dict]:
        relationships = []
        for table_name in tables:
            try:
                fks = self.inspector.get_foreign_keys(table_name)
                for fk in fks:
                    relationships.append(
                        {
                            "from_table": table_name,
                            "from_columns": fk["constrained_columns"],
                            "to_table": fk["referred_table"],
                            "to_columns": fk["referred_columns"],
                        }
                    )
            except Exception as e:
                print(
                    f"Aviso: Não foi possível obter FKs para a tabela {table_name}. Erro: {e} - {timestamp}"
                )
        return relationships

    def _get_sample_data(self, table_name: str, limit: int = 100) -> pd.DataFrame:
        try:
            table = Table(table_name, self.metadata, autoload_with=self.engine)
            stmt = select(table).limit(limit)
            with self.engine.connect() as conn:
                result = conn.execute(stmt)
                return pd.DataFrame(result.fetchall(), columns=result.keys())
        except Exception:
            try:
                return pd.read_sql(
                    f"SELECT * FROM {table_name} LIMIT {limit}", self.engine
                )
            except Exception:
                return pd.DataFrame()

    def _analyze_columns(
        self, columns: List[Dict], sample_data: pd.DataFrame
    ) -> List[Dict]:
        analyzed_columns = []
        for col in columns:
            col_name = col["name"]
            col_analysis = {
                "name": col_name,
                "type": str(col["type"]),
                "nullable": col["nullable"],
                "default": col.get("default"),
                "statistics": {},
            }
            # Sugestões a partir de prefixos de colunas
            col_conv = self._suggest_from_prefix(col_name, "columns")
            col_analysis["convention"] = col_conv or {}
            if col_name in sample_data.columns:
                series = sample_data[col_name]
                col_analysis["statistics"] = {
                    "null_count": int(series.isna().sum()),
                    "null_percentage": float(series.isna().mean() * 100),
                    "unique_count": int(series.nunique()),
                    "most_common": self._get_most_common_values(series),
                }
                if pd.api.types.is_numeric_dtype(series):
                    col_analysis["statistics"].update(
                        {
                            "min": float(series.min())
                            if not series.isna().all()
                            else None,
                            "max": float(series.max())
                            if not series.isna().all()
                            else None,
                            "mean": float(series.mean())
                            if not series.isna().all()
                            else None,
                        }
                    )
                elif pd.api.types.is_string_dtype(series):
                    col_analysis["statistics"].update(
                        {
                            "min_length": int(series.str.len().min())
                            if not series.isna().all()
                            else None,
                            "max_length": int(series.str.len().max())
                            if not series.isna().all()
                            else None,
                            "avg_length": float(series.str.len().mean())
                            if not series.isna().all()
                            else None,
                        }
                    )
            analyzed_columns.append(col_analysis)
        return analyzed_columns

    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty:
            return {"score": 0, "issues": ["Sem dados para análise"]}
        total_cells = df.size
        null_cells = df.isna().sum().sum()
        quality_score = max(0, 100 - (null_cells / total_cells * 100))
        issues = []
        for col in df.columns:
            null_pct = df[col].isna().mean() * 100
            if null_pct > 50:
                issues.append(f"Coluna '{col}' tem {null_pct:.1f}% de valores nulos")
            if pd.api.types.is_string_dtype(df[col]):
                if df[col].str.strip().eq("").sum() > 0:
                    issues.append(f"Coluna '{col}' contém strings vazias")
        return {
            "score": round(quality_score, 2),
            "total_cells": total_cells,
            "null_cells": int(null_cells),
            "null_percentage": round(null_cells / total_cells * 100, 2)
            if total_cells > 0
            else 0,
            "issues": issues,
        }

    def _assess_naming_quality(
        self, table_name: str, columns: List[Dict]
    ) -> Dict[str, Any]:
        issues = []
        score = 100
        if not table_name.replace("_", "").isalnum():
            issues.append(
                f"Tabela contém caracteres especiais: {table_name} - {timestamp}"
            )
            score -= 10
        if len(table_name) < 3:
            issues.append(f"Nome da tabela muito curto: {table_name} - {timestamp}")
            score -= 10
        if table_name.upper() == table_name or table_name.lower() == table_name:
            issues.append(
                f"Nome sem convenção CamelCase/snake_case: {table_name} - {timestamp}"
            )
            score -= 5
        for col in columns:
            col_name = col["name"]
            if len(col_name) < 2:
                issues.append(f"Coluna com nome muito curto: {col_name} - {timestamp}")
                score -= 5
            if len(col_name) > 64:
                issues.append(f"Coluna com nome muito longo: {col_name} - {timestamp}")
                score -= 5
            if len(col_name) <= 5 and col_name.isupper():
                issues.append(f"Possível abreviação confusa: {col_name} - {timestamp}")
                score -= 3
            # Se o analisador de colunas já anexou convenção, inclua na análise
            conv = col.get("convention") if isinstance(col, dict) else None
            if conv:
                # conv pode ser {} se não houver match
                if conv.get("prefix"):
                    layer = conv.get("layer", "")
                    meaning = conv.get("suggested_meaning") or conv.get("description")
                    issues.append(
                        f"Coluna '{col_name}' coincide com prefixo '{conv.get('prefix')}' (camada: {layer}). {meaning or ''} - {timestamp}"
                    )
                    # não penaliza fortemente; apenas adiciona informação
                    score = max(0, score - 0)
        return {"score": max(0, score), "issues": issues}

    def _calculate_overall_quality(self, tables: Dict) -> float:
        if not tables:
            return 0
        scores = []
        for table_data in tables.values():
            if "error" in table_data:
                continue
            data_quality = table_data["data_quality"]["score"]
            naming_quality = table_data["naming_quality"]["score"]
            table_score = (data_quality * 0.6) + (naming_quality * 0.4)
            scores.append(table_score)
        return round(sum(scores) / len(scores), 2) if scores else 0

    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        recommendations = []
        quality_score = analysis["quality_score"]
        if quality_score < 50:
            recommendations.append(
                f"⚠️ CRÍTICO: Qualidade geral do banco está abaixo de 50% - ação imediata recomendada - {timestamp}"
            )
        for table_name, table_data in analysis["tables"].items():
            if "error" in table_data:
                continue
            if not table_data["primary_key"]:
                recommendations.append(
                    f"Tabela '{table_name}' não tem chave primária definida - {timestamp}"
                )
            data_quality = table_data["data_quality"]
            if data_quality.get("null_percentage", 0) > 30:
                recommendations.append(
                    f"Tabela '{table_name}' tem {data_quality['null_percentage']:.1f}% de valores nulos - {timestamp}"
                )
            naming_quality = table_data["naming_quality"]
            if naming_quality["score"] < 70:
                recommendations.append(
                    f"Melhorar nomenclatura da tabela '{table_name}' - {timestamp}"
                )
            # Recomendações baseadas em convenções carregadas via YAML
            conv = table_data.get("convention") or {}
            if conv and conv.get("prefix"):
                layer = conv.get("layer", "")
                # Se for prefixo de sistema, sugerir documentar/evitar alterações
                if layer == "system":
                    recommendations.append(
                        f"Tabela '{table_name}' usa prefixo de sistema '{conv.get('prefix')}'. Considere documentar sua finalidade e evite alterações em produção - {timestamp}"
                    )
                # Se for prefixo de cliente, sugerir revisão antes de alterar
                if layer == "client":
                    recommendations.append(
                        f"Tabela '{table_name}' usa prefixo de cliente '{conv.get('prefix')}'. Verifique impactos em customizações antes de alterações - {timestamp}"
                    )
            # Colunas com convenções detectadas
            for col in table_data.get("columns", []):
                col_conv = (col or {}).get("convention") or {}
                if col_conv and col_conv.get("prefix"):
                    layer = col_conv.get("layer", "")
                    if layer == "system":
                        recommendations.append(
                            f"Coluna '{col.get('name')}' em '{table_name}' parece ser de sistema (prefixo '{col_conv.get('prefix')}'). Evite alterações diretas - {timestamp}"
                        )
                    if layer == "client":
                        recommendations.append(
                            f"Coluna '{col.get('name')}' em '{table_name}' parece ser customização de cliente (prefixo '{col_conv.get('prefix')}'). Revise antes de alterar - {timestamp}"
                        )
        return recommendations

    def _generate_llm_documentation(self, table_name: str, table_analysis: Dict) -> str:
        columns_info = "\n".join(
            [
                f"- {col['name']} ({col['type']}): "
                f"{col.get('statistics', {}).get('null_percentage', 0):.1f}% nulos, "
                f"{col.get('statistics', {}).get('unique_count', 0)} valores únicos"
                for col in table_analysis["columns"]
            ]
        )
        prompt = f"""
Analise esta tabela de banco de dados e gere uma documentação clara:

TABELA: {table_name}
COLUNAS:
{columns_info}

CHAVE PRIMÁRIA: {", ".join(table_analysis["primary_key"]) if table_analysis["primary_key"] else "Não definida"}

Gere:
1. Descrição do propósito da tabela
2. Explicação das colunas principais
3. Possíveis problemas identificados
4. Sugestões de aliases para nomes confusos
"""
        try:
            response = self.llm_client.process_query(prompt)
            return response
        except Exception as e:
            return f"Erro ao gerar documentação: {e} - {timestamp}"

    def _get_most_common_values(self, series: pd.Series, top_n: int = 5):
        try:
            value_counts = series.value_counts().head(top_n)
            return [
                {"value": str(val), "count": int(count)}
                for val, count in value_counts.items()
            ]
        except TypeError:
            return []

    def export_analysis(self, analysis: Dict, output_path: str = None):
        if output_path is None:
            script_file_path = Path(__file__).resolve()
            
            project_root = script_file_path.parent.parent.parent 
            
            default_output = project_root / "scripts" / "schema" / "schema_analysis.json"
            output_path = default_output
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
