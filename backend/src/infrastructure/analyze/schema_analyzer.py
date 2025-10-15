from sqlalchemy import inspect, text, MetaData, Table, select, func
from typing import Dict, List, Any
import pandas as pd
from datetime import datetime
import json
from ..cache import Cache

class SchemaAnalyzer:
    """Analisa e documenta schemas de bancos de dados"""
    def __init__(self, engine, llm_client=None, cache: Cache = None):
        self.engine = engine
        self.inspector = inspect(engine)
        self.llm_client = llm_client
        self.metadata = MetaData()
        self.cache = cache or Cache()

    def analyze_full_database(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Análise completa do banco de dados com cache persistente.

        O resultado da análise é sempre persistido em cache (arquivo JSON).
        Por padrão a análise usa o cache salvo; para forçar uma nova execução
        passar force_refresh=True.
        """
        cache_key = f"schema_analysis_{self.engine.url.database}"
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                print("♻️ Retornando análise a partir do cache")
                return cached
        dialect = getattr(self.engine.dialect, 'name', 'unknown')
        print(f"🔍 Iniciando análise completa do banco de dados...")
        print(f"🔤 Dialeto detectado: {dialect}")

        analysis = {
            'database_info': self._get_database_info(),
            'tables': {},
            'relationships': self._analyze_relationships(),
            'quality_score': 0,
            'recommendations': [],
            'timestamp': datetime.now().isoformat()
        }

        tables = self.inspector.get_table_names()
        print(f"📚 Total de tabelas encontradas: {len(tables)}")
        for i, table_name in enumerate(tables, start=1):
            print(f"  → [{i}/{len(tables)}] Lendo tabela: {table_name}")
            analysis['tables'][table_name] = self._analyze_table(table_name)

        analysis['quality_score'] = self._calculate_overall_quality(analysis['tables'])
        analysis['recommendations'] = self._generate_recommendations(analysis)

        self.cache.set(cache_key, analysis)
        return analysis

    def _get_database_info(self) -> Dict[str, Any]:
        return {
            'dialect': self.engine.dialect.name,
            'driver': self.engine.driver,
            'database_name': self.engine.url.database,
            'table_count': len(self.inspector.get_table_names())
        }

    def _analyze_table(self, table_name: str) -> Dict[str, Any]:
        print(f"    ↳ Iniciando análise da tabela '{table_name}'")
        columns = self.inspector.get_columns(table_name)
        pk = self.inspector.get_pk_constraint(table_name)
        fks = self.inspector.get_foreign_keys(table_name)
        indexes = self.inspector.get_indexes(table_name)
        sample_data = self._get_sample_data(table_name, limit=100)
        table_analysis = {
            'columns': self._analyze_columns(columns, sample_data),
            'primary_key': pk.get('constrained_columns', []),
            'foreign_keys': fks,
            'indexes': [idx['name'] for idx in indexes],
            # 'row_count': self._get_row_count(table_name),
            'data_quality': self._assess_data_quality(sample_data),
            'naming_quality': self._assess_naming_quality(table_name, columns),
            'llm_documentation': None
        }
        print(f"      → colunas: {len(columns)}, registros amostrados: {len(sample_data)}; pk: {table_analysis['primary_key']}")
        if self.llm_client:
            table_analysis['llm_documentation'] = self._generate_llm_documentation(table_name, table_analysis)
        return table_analysis

    def _analyze_columns(self, columns: List[Dict], sample_data: pd.DataFrame) -> List[Dict]:
        analyzed_columns = []
        for col in columns:
            col_name = col['name']
            col_analysis = {
                'name': col_name,
                'type': str(col['type']),
                'nullable': col['nullable'],
                'default': col.get('default'),
                'statistics': {}
            }
            if col_name in sample_data.columns:
                series = sample_data[col_name]
                col_analysis['statistics'] = {
                    'null_count': int(series.isna().sum()),
                    'null_percentage': float(series.isna().mean() * 100),
                    'unique_count': int(series.nunique()),
                    'most_common': self._get_most_common_values(series),
                }
                if pd.api.types.is_numeric_dtype(series):
                    col_analysis['statistics'].update({
                        'min': float(series.min()) if not series.isna().all() else None,
                        'max': float(series.max()) if not series.isna().all() else None,
                        'mean': float(series.mean()) if not series.isna().all() else None,
                    })
                elif pd.api.types.is_string_dtype(series):
                    col_analysis['statistics'].update({
                        'min_length': int(series.str.len().min()) if not series.isna().all() else None,
                        'max_length': int(series.str.len().max()) if not series.isna().all() else None,
                        'avg_length': float(series.str.len().mean()) if not series.isna().all() else None,
                    })
            analyzed_columns.append(col_analysis)
        return analyzed_columns

    def _get_sample_data(self, table_name: str, limit: int = 100) -> pd.DataFrame:
        """Busca amostra de dados usando SQLAlchemy Core para ser dialect-aware."""
        try:
            metadata = MetaData()
            metadata.reflect(bind=self.engine, only=[table_name])
            if table_name in metadata.tables:
                table = metadata.tables[table_name]
                stmt = select(table).limit(limit)
                with self.engine.connect() as conn:
                    result = conn.execute(stmt)
                    df = pd.DataFrame(result.fetchall(), columns=result.keys())
                    return df
            else:
                dialect = self.engine.dialect.name.lower()
                if dialect in ("mssql", "microsoft sql server"):
                    query = text(f"SELECT TOP {limit} * FROM {table_name}")
                else:
                    query = text(f"SELECT * FROM {table_name} LIMIT {limit}")
                return pd.read_sql(query, self.engine)
        except Exception:
            return pd.DataFrame()

    def _get_row_count(self, table_name: str) -> int:
        try:
            metadata = MetaData()
            metadata.reflect(bind=self.engine, only=[table_name])
            if table_name in metadata.tables:
                table = metadata.tables[table_name]
                stmt = select(func.count()).select_from(table)
                with self.engine.connect() as conn:
                    result = conn.execute(stmt).scalar()
                    return int(result or 0)
            else:
                # Fallback
                query = text(f"SELECT COUNT(*) as count FROM {table_name}")
                with self.engine.connect() as conn:
                    result = conn.execute(query)
                    row = result.fetchone()
                    return int(row[0]) if row else 0
        except Exception:
            return 0

    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty:
            return {'score': 0, 'issues': ['Sem dados para análise']}
        total_cells = df.size
        null_cells = df.isna().sum().sum()
        quality_score = max(0, 100 - (null_cells / total_cells * 100))
        issues = []
        for col in df.columns:
            null_pct = df[col].isna().mean() * 100
            if null_pct > 50:
                issues.append(f"Coluna '{col}' tem {null_pct:.1f}% de valores nulos")
            if pd.api.types.is_string_dtype(df[col]):
                if df[col].str.strip().eq('').sum() > 0:
                    issues.append(f"Coluna '{col}' contém strings vazias")
        return {
            'score': round(quality_score, 2),
            'total_cells': total_cells,
            'null_cells': int(null_cells),
            'null_percentage': round(null_cells / total_cells * 100, 2),
            'issues': issues
        }

    def _assess_naming_quality(self, table_name: str, columns: List[Dict]) -> Dict[str, Any]:
        issues = []
        score = 100
        if not table_name.replace('_', '').isalnum():
            issues.append(f"Tabela contém caracteres especiais: {table_name}")
            score -= 10
        if len(table_name) < 3:
            issues.append(f"Nome da tabela muito curto: {table_name}")
            score -= 10
        if table_name.upper() == table_name or table_name.lower() == table_name:
            issues.append(f"Nome sem convenção CamelCase/snake_case: {table_name}")
            score -= 5
        for col in columns:
            col_name = col['name']
            if len(col_name) < 2:
                issues.append(f"Coluna com nome muito curto: {col_name}")
                score -= 5
            if len(col_name) > 64:
                issues.append(f"Coluna com nome muito longo: {col_name}")
                score -= 5
            if len(col_name) <= 5 and col_name.isupper():
                issues.append(f"Possível abreviação confusa: {col_name}")
                score -= 3
        return {
            'score': max(0, score),
            'issues': issues
        }

    def _analyze_relationships(self) -> List[Dict]:
        relationships = []
        for table in self.inspector.get_table_names():
            fks = self.inspector.get_foreign_keys(table)
            for fk in fks:
                relationships.append({
                    'from_table': table,
                    'from_columns': fk['constrained_columns'],
                    'to_table': fk['referred_table'],
                    'to_columns': fk['referred_columns']
                })
        return relationships

    def _calculate_overall_quality(self, tables: Dict) -> float:
        if not tables:
            return 0
        scores = []
        for table_data in tables.values():
            data_quality = table_data['data_quality']['score']
            naming_quality = table_data['naming_quality']['score']
            table_score = (data_quality * 0.6) + (naming_quality * 0.4)
            scores.append(table_score)
        return round(sum(scores) / len(scores), 2)

    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        recommendations = []
        quality_score = analysis['quality_score']
        if quality_score < 50:
            recommendations.append("⚠️ CRÍTICO: Qualidade geral do banco está abaixo de 50%")
        for table_name, table_data in analysis['tables'].items():
            if not table_data['primary_key']:
                recommendations.append(f"Tabela '{table_name}' não tem chave primária definida")
            data_quality = table_data['data_quality']
            if data_quality['null_percentage'] > 30:
                recommendations.append(f"Tabela '{table_name}' tem {data_quality['null_percentage']:.1f}% de valores nulos")
            naming_quality = table_data['naming_quality']
            if naming_quality['score'] < 70:
                recommendations.append(f"Melhorar nomenclatura da tabela '{table_name}'")
        return recommendations

    def _generate_llm_documentation(self, table_name: str, table_analysis: Dict) -> str:
        columns_info = "\n".join([
            f"- {col['name']} ({col['type']}): "
            f"{col['statistics'].get('null_percentage', 0):.1f}% nulos, "
            f"{col['statistics'].get('unique_count', 0)} valores únicos"
            for col in table_analysis['columns']
        ])
        prompt = f"""
Analise esta tabela de banco de dados e gere uma documentação clara:

TABELA: {table_name}
COLUNAS:
{columns_info}

CHAVE PRIMÁRIA: {', '.join(table_analysis['primary_key']) if table_analysis['primary_key'] else 'Não definida'}
TOTAL DE REGISTROS: {table_analysis['row_count']}

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
            return f"Erro ao gerar documentação: {e}"

    def _get_most_common_values(self, series: pd.Series, top_n: int = 5):
        value_counts = series.value_counts().head(top_n)
        return [
            {'value': str(val), 'count': int(count)}
            for val, count in value_counts.items()
        ]

    def export_analysis(self, analysis: Dict, output_path: str = "schema_analysis.json"):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
