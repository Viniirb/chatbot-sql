# 🔄 Guia de Adaptabilidade para Bases de Dados Desorganizadas

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Análise da Arquitetura Atual](#análise-da-arquitetura-atual)
3. [Recomendações de Melhorias](#recomendações-de-melhorias)
4. [Ferramentas e Tecnologias](#ferramentas-e-tecnologias)
5. [Implementação por Fases](#implementação-por-fases)
6. [Recursos de Estudo](#recursos-de-estudo)

---

## 🎯 Visão Geral

Este documento detalha como adaptar o backend atual para trabalhar com bases de dados mal organizadas, sem padronização de nomenclatura, esquemas inconsistentes e estruturas problemáticas.

### Pontos Fortes da Arquitetura Atual

✅ **Arquitetura em Camadas** (Domain, Application, Infrastructure)
- Facilita mudanças isoladas sem afetar todo o sistema
- Separação clara de responsabilidades

✅ **Uso de LLM para Geração de SQL** (LlamaIndex + Gemini)
- Adapta-se dinamicamente a schemas diferentes
- Entende nomes de colunas mal escritos
- Não precisa de mapeamentos hardcoded

✅ **SQLAlchemy como Abstração**
- Suporta múltiplos bancos de dados
- Auto-discovery de tabelas e schemas

### Limitações Atuais

⚠️ **Hardcoded para SQL Server (T-SQL)**
⚠️ **Sem mecanismo de documentação de schema**
⚠️ **Memory buffer limitado (1500 tokens)**
⚠️ **Falta de retry logic inteligente**
⚠️ **Sem sistema de aprendizado de queries**

---

## 🔧 Recomendações de Melhorias

### 1. Prompt do Sistema Configurável

#### 📖 O Que É
Sistema que adapta automaticamente as instruções do LLM baseado no tipo de banco de dados detectado.

#### 🎯 Problema que Resolve
Cada banco tem sintaxes diferentes (TOP vs LIMIT, aspas vs backticks, etc.). Um prompt genérico pode gerar SQL incorreto.

#### 🛠️ Como Implementar

**Tecnologias:**
- YAML/JSON para configuração
- Pydantic para validação
- Jinja2 para templates (opcional)

**Estrutura de Arquivos:**
```
config/
├── prompts/
│   ├── sql_server.yaml
│   ├── mysql.yaml
│   ├── postgresql.yaml
│   └── oracle.yaml
```

**Exemplo de Configuração (sql_server.yaml):**
```yaml
database_type: "SQL Server"
dialect: "T-SQL"

syntax_rules:
  limit: "TOP N (antes das colunas)"
  string_quotes: "aspas simples"
  identifier_quotes: "colchetes [table]"
  date_format: "YYYY-MM-DD"
  
system_prompt_template: |
  Você é um assistente especializado em {database_type}.
  
  REGRAS DE SINTAXE:
  - Use {syntax_rules.limit} para limitar resultados
  - Datas no formato {syntax_rules.date_format}
  - Identificadores com {syntax_rules.identifier_quotes}
  
  QUIRKS ESPECÍFICOS:
  {quirks}

quirks:
  - "GETDATE() para data atual, não NOW()"
  - "LEN() para tamanho de string, não LENGTH()"
  - "Concatenação com + não ||"

common_functions:
  current_date: "GETDATE()"
  string_length: "LEN(column)"
  substring: "SUBSTRING(column, start, length)"
  concat: "column1 + column2"
```

**Implementação Python:**
```python
# src/infrastructure/config_loader.py
from pathlib import Path
import yaml
from pydantic import BaseModel
from typing import Dict, List

class DatabaseSyntaxRules(BaseModel):
    limit: str
    string_quotes: str
    identifier_quotes: str
    date_format: str

class DatabasePromptConfig(BaseModel):
    database_type: str
    dialect: str
    syntax_rules: DatabaseSyntaxRules
    system_prompt_template: str
    quirks: List[str]
    common_functions: Dict[str, str]

class PromptConfigLoader:
    def __init__(self, config_dir: str = "config/prompts"):
        self.config_dir = Path(config_dir)
    
    def load_config(self, database_type: str) -> DatabasePromptConfig:
        """Carrega configuração para o tipo de banco especificado"""
        config_file = self.config_dir / f"{database_type.lower()}.yaml"
        
        if not config_file.exists():
            raise ValueError(f"Configuração não encontrada para {database_type}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        return DatabasePromptConfig(**config_data)
    
    def generate_system_prompt(self, database_type: str) -> str:
        """Gera o prompt do sistema baseado no tipo de banco"""
        config = self.load_config(database_type)
        
        quirks_formatted = "\n".join([f"- {q}" for q in config.quirks])
        
        prompt = config.system_prompt_template.format(
            database_type=config.database_type,
            syntax_rules=config.syntax_rules,
            quirks=quirks_formatted
        )
        
        return prompt
```

**Recursos de Estudo:**
- 📚 [YAML Tutorial](https://yaml.org/spec/1.2.2/)
- 📚 [Pydantic Documentation](https://docs.pydantic.dev/)
- 📚 [Jinja2 Templating](https://jinja.palletsprojects.com/)

---

### 2. Schema Analyzer (Analisador de Esquema)

#### 📖 O Que É
Ferramenta que inspeciona automaticamente o banco de dados, documenta tabelas/colunas e identifica problemas de qualidade.

#### 🎯 Problema que Resolve
Bases mal organizadas têm nomes confusos, falta de documentação e dados inconsistentes. O analyzer cria um "mapa" do banco.

#### 🛠️ Como Implementar

**Tecnologias:**
- **SQLAlchemy Inspector** - Introspeção de schema
- **Pandas** - Análise de dados
- **Great Expectations** - Validação de qualidade
- **LLM (Gemini/GPT)** - Documentação automática

**Implementação:**

```python
# src/infrastructure/schema_analyzer.py
from sqlalchemy import inspect, text, MetaData, Table
from typing import Dict, List, Any
import pandas as pd
from datetime import datetime

class SchemaAnalyzer:
    """Analisa e documenta schemas de bancos de dados"""
    
    def __init__(self, engine, llm_client=None):
        self.engine = engine
        self.inspector = inspect(engine)
        self.llm_client = llm_client
        self.metadata = MetaData()
    
    def analyze_full_database(self) -> Dict[str, Any]:
        """Análise completa do banco de dados"""
        print("🔍 Iniciando análise do banco de dados...")
        
        analysis = {
            'database_info': self._get_database_info(),
            'tables': {},
            'relationships': self._analyze_relationships(),
            'quality_score': 0,
            'recommendations': [],
            'timestamp': datetime.now().isoformat()
        }
        
        tables = self.inspector.get_table_names()
        
        for table_name in tables:
            print(f"  📊 Analisando tabela: {table_name}")
            analysis['tables'][table_name] = self._analyze_table(table_name)
        
        analysis['quality_score'] = self._calculate_overall_quality(analysis['tables'])
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _get_database_info(self) -> Dict[str, Any]:
        """Informações gerais do banco"""
        return {
            'dialect': self.engine.dialect.name,
            'driver': self.engine.driver,
            'database_name': self.engine.url.database,
            'table_count': len(self.inspector.get_table_names())
        }
    
    def _analyze_table(self, table_name: str) -> Dict[str, Any]:
        """Análise detalhada de uma tabela"""
        columns = self.inspector.get_columns(table_name)
        pk = self.inspector.get_pk_constraint(table_name)
        fks = self.inspector.get_foreign_keys(table_name)
        indexes = self.inspector.get_indexes(table_name)
        
        # Pega amostra de dados
        sample_data = self._get_sample_data(table_name, limit=100)
        
        table_analysis = {
            'columns': self._analyze_columns(columns, sample_data),
            'primary_key': pk.get('constrained_columns', []),
            'foreign_keys': fks,
            'indexes': [idx['name'] for idx in indexes],
            'row_count': self._get_row_count(table_name),
            'data_quality': self._assess_data_quality(sample_data),
            'naming_quality': self._assess_naming_quality(table_name, columns),
            'llm_documentation': None
        }
        
        # Usa LLM para gerar documentação (se disponível)
        if self.llm_client:
            table_analysis['llm_documentation'] = self._generate_llm_documentation(
                table_name, table_analysis
            )
        
        return table_analysis
    
    def _analyze_columns(self, columns: List[Dict], sample_data: pd.DataFrame) -> List[Dict]:
        """Analisa cada coluna da tabela"""
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
            
            # Estatísticas baseadas em dados reais
            if col_name in sample_data.columns:
                series = sample_data[col_name]
                col_analysis['statistics'] = {
                    'null_count': int(series.isna().sum()),
                    'null_percentage': float(series.isna().mean() * 100),
                    'unique_count': int(series.nunique()),
                    'most_common': self._get_most_common_values(series),
                }
                
                # Estatísticas específicas por tipo
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
        """Busca amostra de dados da tabela"""
        try:
            query = text(f"SELECT * FROM {table_name} LIMIT {limit}")
            return pd.read_sql(query, self.engine)
        except Exception as e:
            print(f"⚠️ Erro ao buscar dados de {table_name}: {e}")
            return pd.DataFrame()
    
    def _get_row_count(self, table_name: str) -> int:
        """Conta registros na tabela"""
        try:
            query = text(f"SELECT COUNT(*) as count FROM {table_name}")
            result = self.engine.execute(query)
            return result.fetchone()[0]
        except:
            return 0
    
    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Avalia qualidade dos dados"""
        if df.empty:
            return {'score': 0, 'issues': ['Sem dados para análise']}
        
        total_cells = df.size
        null_cells = df.isna().sum().sum()
        
        quality_score = max(0, 100 - (null_cells / total_cells * 100))
        
        issues = []
        
        # Detecta problemas comuns
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
        """Avalia qualidade dos nomes de tabelas e colunas"""
        issues = []
        score = 100
        
        # Verifica nome da tabela
        if not table_name.replace('_', '').isalnum():
            issues.append(f"Tabela contém caracteres especiais: {table_name}")
            score -= 10
        
        if len(table_name) < 3:
            issues.append(f"Nome da tabela muito curto: {table_name}")
            score -= 10
        
        if table_name.upper() == table_name or table_name.lower() == table_name:
            # Tudo maiúsculo ou minúsculo pode ser ok, mas vamos registrar
            issues.append(f"Nome sem convenção CamelCase/snake_case: {table_name}")
            score -= 5
        
        # Verifica colunas
        for col in columns:
            col_name = col['name']
            
            if len(col_name) < 2:
                issues.append(f"Coluna com nome muito curto: {col_name}")
                score -= 5
            
            if len(col_name) > 64:
                issues.append(f"Coluna com nome muito longo: {col_name}")
                score -= 5
            
            # Detecta abreviações confusas
            if len(col_name) <= 5 and col_name.isupper():
                issues.append(f"Possível abreviação confusa: {col_name}")
                score -= 3
        
        return {
            'score': max(0, score),
            'issues': issues
        }
    
    def _analyze_relationships(self) -> List[Dict]:
        """Analisa relacionamentos entre tabelas"""
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
        """Calcula score geral de qualidade"""
        if not tables:
            return 0
        
        scores = []
        for table_data in tables.values():
            data_quality = table_data['data_quality']['score']
            naming_quality = table_data['naming_quality']['score']
            
            # Peso: 60% qualidade dos dados, 40% nomenclatura
            table_score = (data_quality * 0.6) + (naming_quality * 0.4)
            scores.append(table_score)
        
        return round(sum(scores) / len(scores), 2)
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """Gera recomendações de melhorias"""
        recommendations = []
        
        quality_score = analysis['quality_score']
        
        if quality_score < 50:
            recommendations.append("⚠️ CRÍTICO: Qualidade geral do banco está abaixo de 50%")
        
        # Analisa cada tabela
        for table_name, table_data in analysis['tables'].items():
            if not table_data['primary_key']:
                recommendations.append(f"Tabela '{table_name}' não tem chave primária definida")
            
            data_quality = table_data['data_quality']
            if data_quality['null_percentage'] > 30:
                recommendations.append(
                    f"Tabela '{table_name}' tem {data_quality['null_percentage']:.1f}% de valores nulos"
                )
            
            naming_quality = table_data['naming_quality']
            if naming_quality['score'] < 70:
                recommendations.append(f"Melhorar nomenclatura da tabela '{table_name}'")
        
        return recommendations
    
    def _generate_llm_documentation(self, table_name: str, table_analysis: Dict) -> str:
        """Usa LLM para gerar documentação da tabela"""
        # Prepara contexto para o LLM
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
        """Retorna os valores mais comuns"""
        value_counts = series.value_counts().head(top_n)
        return [
            {'value': str(val), 'count': int(count)}
            for val, count in value_counts.items()
        ]
    
    def export_analysis(self, analysis: Dict, output_path: str = "schema_analysis.json"):
        """Exporta análise para arquivo JSON"""
        import json
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Análise exportada para: {output_path}")
```

**Uso:**
```python
from sqlalchemy import create_engine
from src.infrastructure.schema_analyzer import SchemaAnalyzer

engine = create_engine('your_database_url')
analyzer = SchemaAnalyzer(engine)

analysis = analyzer.analyze_full_database()
analyzer.export_analysis(analysis, 'database_report.json')

print(f"Qualidade geral: {analysis['quality_score']}/100")
print(f"\nRecomendações:")
for rec in analysis['recommendations']:
    print(f"  - {rec}")
```

**Recursos de Estudo:**
- 📚 [SQLAlchemy Inspector](https://docs.sqlalchemy.org/en/20/core/reflection.html)
- 📚 [Pandas Profiling](https://github.com/ydataai/ydata-profiling)
- 📚 [Great Expectations](https://greatexpectations.io/)
- 🎥 [YouTube: Database Schema Design](https://www.youtube.com/results?search_query=database+schema+design)

---

### 3. Sistema de Retry Logic Inteligente

#### 📖 O Que É
Mecanismo que tenta novamente quando uma query falha, aprendendo com os erros e usando o LLM para corrigir.

#### 🎯 Problema que Resolve
Schemas mal organizados podem causar erros frequentes. Em vez de falhar imediatamente, o sistema tenta corrigir automaticamente.

#### 🛠️ Como Implementar

**Tecnologias:**
- **Tenacity** - Biblioteca de retry
- **LLM** - Para corrigir queries
- **Logging** - Para rastrear tentativas

**Implementação:**

```python
# src/infrastructure/intelligent_query_executor.py
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from sqlalchemy.exc import SQLAlchemyError
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)

class IntelligentQueryExecutor:
    """Executor de queries com retry inteligente e aprendizado"""
    
    def __init__(self, engine, llm_client):
        self.engine = engine
        self.llm_client = llm_client
        self.successful_patterns = []  # Cache de padrões bem-sucedidos
        self.error_patterns = {}  # Cache de erros conhecidos
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(SQLAlchemyError),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def execute_with_retry(self, query: str, user_question: str = "") -> Any:
        """
        Executa query com retry automático
        
        Args:
            query: SQL query para executar
            user_question: Pergunta original do usuário (para contexto)
        
        Returns:
            Resultado da query
        """
        try:
            logger.info(f"Tentando executar query: {query[:100]}...")
            
            with self.engine.connect() as conn:
                result = conn.execute(query)
                rows = result.fetchall()
            
            # Se deu certo, salva o padrão
            self._save_successful_pattern(user_question, query, len(rows))
            
            logger.info(f"✅ Query executada com sucesso: {len(rows)} registros")
            return rows
            
        except SQLAlchemyError as e:
            logger.warning(f"⚠️ Erro na query: {str(e)}")
            
            # Tenta corrigir usando LLM
            corrected_query = self._attempt_correction(query, str(e), user_question)
            
            if corrected_query and corrected_query != query:
                logger.info(f"🔄 Tentando query corrigida...")
                with self.engine.connect() as conn:
                    result = conn.execute(corrected_query)
                    rows = result.fetchall()
                
                self._save_successful_pattern(user_question, corrected_query, len(rows))
                return rows
            else:
                # Se não conseguiu corrigir, re-raise
                raise
    
    def _attempt_correction(self, query: str, error: str, user_question: str) -> str:
        """Tenta corrigir query usando LLM"""
        
        # Verifica se já vimos este tipo de erro antes
        if error in self.error_patterns:
            logger.info("📚 Usando correção conhecida do cache")
            return self.error_patterns[error].get('corrected_query', query)
        
        correction_prompt = f"""
A seguinte query SQL falhou. Corrija o erro:

PERGUNTA DO USUÁRIO:
{user_question}

QUERY ORIGINAL:
{query}

ERRO:
{error}

INSTRUÇÕES:
1. Analise o erro e identifique o problema
2. Corrija a sintaxe SQL mantendo a intenção original
3. Retorne APENAS a query corrigida, sem explicações

QUERY CORRIGIDA:
"""
        
        try:
            corrected_query = self.llm_client.process_query(correction_prompt)
            
            # Limpa a resposta (remove markdown, etc)
            corrected_query = self._clean_sql(corrected_query)
            
            # Salva no cache de erros
            self.error_patterns[error] = {
                'original_query': query,
                'corrected_query': corrected_query,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"🔧 Query corrigida pelo LLM")
            return corrected_query
            
        except Exception as llm_error:
            logger.error(f"❌ Erro ao tentar corrigir com LLM: {llm_error}")
            return query
    
    def _clean_sql(self, sql: str) -> str:
        """Remove formatação extra do SQL"""
        import re
        
        # Remove markdown code blocks
        sql = re.sub(r'```sql\n?', '', sql)
        sql = re.sub(r'```\n?', '', sql)
        
        # Remove comentários desnecessários
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        
        return sql.strip()
    
    def _save_successful_pattern(self, question: str, query: str, result_count: int):
        """Salva padrão bem-sucedido para aprendizado futuro"""
        pattern = {
            'question': question,
            'query': query,
            'result_count': result_count,
            'timestamp': datetime.now().isoformat()
        }
        
        self.successful_patterns.append(pattern)
        
        # Mantém apenas os últimos 100 padrões
        if len(self.successful_patterns) > 100:
            self.successful_patterns.pop(0)
        
        logger.debug(f"💾 Padrão salvo: {len(self.successful_patterns)} no cache")
    
    def get_similar_successful_queries(self, user_question: str, top_k: int = 3) -> List[Dict]:
        """
        Busca queries similares que foram bem-sucedidas
        (Implementação básica - pode ser melhorada com embeddings)
        """
        from difflib import SequenceMatcher
        
        similarities = []
        
        for pattern in self.successful_patterns:
            similarity = SequenceMatcher(
                None,
                user_question.lower(),
                pattern['question'].lower()
            ).ratio()
            
            similarities.append({
                'pattern': pattern,
                'similarity': similarity
            })
        
        # Ordena por similaridade e retorna top_k
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        return [s['pattern'] for s in similarities[:top_k]]
```

**Recursos de Estudo:**
- 📚 [Tenacity Documentation](https://tenacity.readthedocs.io/)
- 📚 [Error Handling Best Practices](https://realpython.com/python-exceptions/)
- 🎥 [YouTube: Retry Patterns](https://www.youtube.com/results?search_query=retry+pattern+python)

---

### 4. Sistema de Aprendizado com Vector Database

#### 📖 O Que É
Sistema que armazena queries bem-sucedidas em um banco vetorial e busca exemplos similares antes de gerar novas queries.

#### 🎯 Problema que Resolve
Em vez de começar do zero toda vez, o sistema aprende com queries anteriores e usa exemplos similares como referência (RAG - Retrieval Augmented Generation).

#### 🛠️ Como Implementar

**Tecnologias:**
- **ChromaDB** - Vector database leve e local
- **Alternativas**: Pinecone (cloud), Qdrant, pgvector
- **Embeddings** - Google Gemini Embeddings (já usa no projeto)

**Instalação:**
```bash
pip install chromadb
```

**Implementação:**

```python
# src/infrastructure/query_learning_system.py
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from datetime import datetime
import hashlib

class QueryLearningSystem:
    """Sistema de aprendizado de queries usando vector database"""
    
    def __init__(self, persist_directory: str = "./chroma_db", embedding_function=None):
        """
        Args:
            persist_directory: Diretório para persistir o banco
            embedding_function: Função de embedding (usa Gemini por padrão)
        """
        # Inicializa ChromaDB com persistência
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        # Cria ou pega coleção existente
        self.collection = self.client.get_or_create_collection(
            name="successful_queries",
            metadata={"description": "Queries SQL bem-sucedidas para aprendizado"}
        )
        
        self.embedding_function = embedding_function
    
    def save_successful_query(
        self,
        user_question: str,
        sql_query: str,
        result_count: int,
        execution_time: float = 0.0,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Salva uma query bem-sucedida no banco vetorial
        
        Args:
            user_question: Pergunta original do usuário
            sql_query: Query SQL que funcionou
            result_count: Número de resultados retornados
            execution_time: Tempo de execução em segundos
            metadata: Metadados adicionais
        
        Returns:
            ID do registro salvo
        """
        # Gera ID único baseado na pergunta
        query_id = self._generate_id(user_question, sql_query)
        
        # Prepara metadados
        query_metadata = {
            "sql_query": sql_query,
            "result_count": result_count,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
        
        if metadata:
            query_metadata.update(metadata)
        
        try:
            # Adiciona ao ChromaDB
            self.collection.add(
                documents=[user_question],  # O texto que será embedado
                metadatas=[query_metadata],
                ids=[query_id]
            )
            
            print(f"💾 Query salva no banco de aprendizado: {query_id}")
            return query_id
            
        except Exception as e:
            print(f"⚠️ Erro ao salvar query: {e}")
            return ""
    
    def find_similar_queries(
        self,
        user_question: str,
        top_k: int = 5,
        min_similarity: float = 0.7
    ) -> List[Dict]:
        """
        Busca queries similares bem-sucedidas
        
        Args:
            user_question: Pergunta do usuário
            top_k: Quantos exemplos retornar
            min_similarity: Similaridade mínima (0-1)
        
        Returns:
            Lista de queries similares com metadados
        """
        try:
            results = self.collection.query(
                query_texts=[user_question],
                n_results=top_k
            )
            
            if not results['documents'][0]:
                return []
            
            similar_queries = []
            
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                # Converte distância em similaridade (0-1)
                # ChromaDB usa distância euclidiana, então menor é melhor
                similarity = 1 / (1 + distance)
                
                if similarity >= min_similarity:
                    similar_queries.append({
                        'question': doc,
                        'sql_query': metadata['sql_query'],
                        'result_count': metadata['result_count'],
                        'similarity': round(similarity, 3),
                        'timestamp': metadata.get('timestamp', 'unknown')
                    })
            
            print(f"🔍 Encontradas {len(similar_queries)} queries similares")
            return similar_queries
            
        except Exception as e:
            print(f"⚠️ Erro ao buscar queries similares: {e}")
            return []
    
    def get_best_examples_for_context(
        self,
        user_question: str,
        max_examples: int = 3
    ) -> str:
        """
        Retorna exemplos formatados para incluir no contexto do LLM
        
        Args:
            user_question: Pergunta do usuário
            max_examples: Máximo de exemplos a incluir
        
        Returns:
            String formatada com exemplos
        """
        similar = self.find_similar_queries(user_question, top_k=max_examples)
        
        if not similar:
            return ""
        
        examples_text = "📚 EXEMPLOS DE QUERIES SIMILARES ANTERIORES:\n\n"
        
        for i, example in enumerate(similar, 1):
            examples_text += f"EXEMPLO {i} (similaridade: {example['similarity']}):\n"
            examples_text += f"Pergunta: {example['question']}\n"
            examples_text += f"SQL: {example['sql_query']}\n"
            examples_text += f"Resultados: {example['result_count']} registros\n"
            examples_text += "-" * 50 + "\n\n"
        
        return examples_text
    
    def get_statistics(self) -> Dict:
        """Retorna estatísticas do sistema de aprendizado"""
        count = self.collection.count()
        
        return {
            'total_queries': count,
            'collection_name': self.collection.name,
            'last_updated': datetime.now().isoformat()
        }
    
    def clear_old_queries(self, days_old: int = 30):
        """Remove queries antigas do banco"""
        # Implementação simplificada - ChromaDB não tem query por data nativamente
        # Em produção, usar um banco com suporte a TTL ou implementar limpeza manual
        print(f"🧹 Limpeza de queries com mais de {days_old} dias")
        # TODO: Implementar lógica de limpeza
    
    def _generate_id(self, question: str, sql: str) -> str:
        """Gera ID único para a query"""
        combined = f"{question}_{sql}_{datetime.now().date()}"
        return hashlib.md5(combined.encode()).hexdigest()


class EnhancedQueryProcessor:
    """Query Processor melhorado com aprendizado"""
    
    def __init__(self, base_processor, learning_system: QueryLearningSystem):
        self.base_processor = base_processor
        self.learning_system = learning_system
    
    async def process_with_learning(
        self,
        user_question: str,
        session
    ) -> str:
        """
        Processa query com aprendizado de exemplos similares
        
        Args:
            user_question: Pergunta do usuário
            session: Sessão atual
        
        Returns:
            Resposta processada
        """
        # Busca exemplos similares
        examples_context = self.learning_system.get_best_examples_for_context(
            user_question,
            max_examples=2
        )
        
        # Adiciona exemplos ao contexto se encontrou algum
        if examples_context:
            enhanced_question = f"""
{examples_context}

USE OS EXEMPLOS ACIMA COMO REFERÊNCIA quando apropriado.

PERGUNTA ATUAL DO USUÁRIO:
{user_question}
"""
        else:
            enhanced_question = user_question
        
        # Processa normalmente
        import time
        start_time = time.time()
        
        response = await self.base_processor.process_query(enhanced_question, session)
        
        execution_time = time.time() - start_time
        
        # Se a query foi bem-sucedida e contém SELECT, salva para aprendizado
        if "SELECT" in response.upper() and "erro" not in response.lower():
            # Extrai a query SQL da resposta (implementação simplificada)
            sql_query = self._extract_sql_from_response(response)
            
            if sql_query:
                self.learning_system.save_successful_query(
                    user_question=user_question,
                    sql_query=sql_query,
                    result_count=0,  # TODO: Extrair do resultado
                    execution_time=execution_time
                )
        
        return response
    
    def _extract_sql_from_response(self, response: str) -> Optional[str]:
        """Extrai SQL da resposta do LLM"""
        import re
        
        # Procura por SELECT statements
        sql_pattern = r'SELECT\s+.+?(?=;|\n\n|$)'
        match = re.search(sql_pattern, response, re.IGNORECASE | re.DOTALL)
        
        if match:
            return match.group(0).strip()
        
        return None
```

**Integração no Projeto:**

```python
# src/infrastructure/container.py (adicionar)
from .query_learning_system import QueryLearningSystem, EnhancedQueryProcessor

def setup_learning_system(query_processor):
    """Configura sistema de aprendizado"""
    learning_system = QueryLearningSystem(
        persist_directory="./data/query_learning",
        embedding_function=None  # Usa o padrão do ChromaDB
    )
    
    enhanced_processor = EnhancedQueryProcessor(
        base_processor=query_processor,
        learning_system=learning_system
    )
    
    return enhanced_processor
```

**Recursos de Estudo:**
- 📚 [ChromaDB Documentation](https://docs.trychroma.com/)
- 📚 [Vector Databases Explained](https://www.pinecone.io/learn/vector-database/)
- 📚 [RAG (Retrieval Augmented Generation)](https://python.langchain.com/docs/use_cases/question_answering/)
- 🎥 [YouTube: Vector Databases](https://www.youtube.com/results?search_query=vector+database+tutorial)
- 🎥 [YouTube: RAG Explained](https://www.youtube.com/results?search_query=retrieval+augmented+generation)

---

### 5. Detecção Automática de Tipo de Banco

#### 📖 O Que É
Sistema que detecta automaticamente o tipo de banco de dados (SQL Server, MySQL, PostgreSQL, etc.) e ajusta configurações.

#### 🎯 Problema que Resolve
Cada banco tem peculiaridades. Detecção automática permite usar o mesmo código com diferentes bancos.

#### 🛠️ Como Implementar

```python
# src/infrastructure/database_detector.py
from sqlalchemy import create_engine, inspect
from typing import Dict, Any
from enum import Enum

class DatabaseType(Enum):
    SQL_SERVER = "mssql"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    ORACLE = "oracle"
    SQLITE = "sqlite"
    UNKNOWN = "unknown"

class DatabaseConfig:
    """Configuração específica por tipo de banco"""
    
    CONFIGS = {
        DatabaseType.SQL_SERVER: {
            'name': 'SQL Server',
            'dialect': 'T-SQL',
            'limit_syntax': 'TOP N',
            'limit_example': 'SELECT TOP 10 * FROM table',
            'string_concat': '+',
            'current_date': 'GETDATE()',
            'string_length': 'LEN(column)',
            'identifier_quote': '[]',
            'features': ['windows_authentication', 'schemas'],
            'quirks': [
                "Use SELECT TOP N antes das colunas",
                "Concatenação com +, não ||",
                "GETDATE() para data atual, não NOW()",
                "LEN() para tamanho, não LENGTH()"
            ]
        },
        DatabaseType.MYSQL: {
            'name': 'MySQL',
            'dialect': 'MySQL',
            'limit_syntax': 'LIMIT N',
            'limit_example': 'SELECT * FROM table LIMIT 10',
            'string_concat': 'CONCAT()',
            'current_date': 'NOW()',
            'string_length': 'LENGTH(column)',
            'identifier_quote': '``',
            'features': ['auto_increment', 'storage_engines'],
            'quirks': [
                "Use LIMIT N no final da query",
                "Backticks para nomes de tabelas/colunas",
                "NOW() para data atual",
                "LENGTH() para tamanho de string"
            ]
        },
        DatabaseType.POSTGRESQL: {
            'name': 'PostgreSQL',
            'dialect': 'PostgreSQL',
            'limit_syntax': 'LIMIT N',
            'limit_example': 'SELECT * FROM table LIMIT 10',
            'string_concat': '||',
            'current_date': 'NOW()',
            'string_length': 'LENGTH(column)',
            'identifier_quote': '""',
            'features': ['schemas', 'advanced_types', 'jsonb'],
            'quirks': [
                "Use LIMIT N no final da query",
                "Concatenação com ||",
                "Case-sensitive para nomes entre aspas",
                "Schemas públicos e privados"
            ]
        },
        DatabaseType.ORACLE: {
            'name': 'Oracle',
            'dialect': 'PL/SQL',
            'limit_syntax': 'ROWNUM',
            'limit_example': 'SELECT * FROM table WHERE ROWNUM <= 10',
            'string_concat': '||',
            'current_date': 'SYSDATE',
            'string_length': 'LENGTH(column)',
            'identifier_quote': '""',
            'features': ['packages', 'advanced_analytics'],
            'quirks': [
                "Use WHERE ROWNUM <= N ou FETCH FIRST N ROWS",
                "SYSDATE para data atual",
                "Schemas são usuários",
                "DUAL table para selects sem FROM"
            ]
        },
        DatabaseType.SQLITE: {
            'name': 'SQLite',
            'dialect': 'SQLite',
            'limit_syntax': 'LIMIT N',
            'limit_example': 'SELECT * FROM table LIMIT 10',
            'string_concat': '||',
            'current_date': "datetime('now')",
            'string_length': 'LENGTH(column)',
            'identifier_quote': '""',
            'features': ['file_based', 'lightweight'],
            'quirks': [
                "Tipos de dados dinâmicos",
                "Sem RIGHT JOIN",
                "datetime('now') para data atual",
                "Limitações em ALTER TABLE"
            ]
        }
    }
    
    @classmethod
    def get_config(cls, db_type: DatabaseType) -> Dict[str, Any]:
        """Retorna configuração para o tipo de banco"""
        return cls.CONFIGS.get(db_type, cls.CONFIGS[DatabaseType.SQL_SERVER])

class DatabaseDetector:
    """Detecta tipo de banco e retorna configurações apropriadas"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.engine = None
        self.db_type = DatabaseType.UNKNOWN
        self.config = None
    
    def detect(self) -> Dict[str, Any]:
        """
        Detecta o tipo de banco e retorna configurações
        
        Returns:
            Dicionário com tipo, configurações e metadados
        """
        try:
            self.engine = create_engine(self.connection_string)
            dialect_name = self.engine.dialect.name.lower()
            
            # Mapeia dialect para DatabaseType
            dialect_mapping = {
                'mssql': DatabaseType.SQL_SERVER,
                'mysql': DatabaseType.MYSQL,
                'postgresql': DatabaseType.POSTGRESQL,
                'oracle': DatabaseType.ORACLE,
                'sqlite': DatabaseType.SQLITE
            }
            
            self.db_type = dialect_mapping.get(dialect_name, DatabaseType.UNKNOWN)
            self.config = DatabaseConfig.get_config(self.db_type)
            
            # Coleta informações adicionais
            metadata = self._collect_metadata()
            
            return {
                'type': self.db_type.value,
                'name': self.config['name'],
                'dialect': self.config['dialect'],
                'config': self.config,
                'metadata': metadata,
                'connection_info': {
                    'driver': self.engine.driver,
                    'database': self.engine.url.database,
                    'host': self.engine.url.host
                }
            }
            
        except Exception as e:
            return {
                'type': 'unknown',
                'error': str(e),
                'config': DatabaseConfig.get_config(DatabaseType.UNKNOWN)
            }
    
    def _collect_metadata(self) -> Dict[str, Any]:
        """Coleta metadados do banco"""
        try:
            inspector = inspect(self.engine)
            
            return {
                'tables_count': len(inspector.get_table_names()),
                'schemas': inspector.get_schema_names() if hasattr(inspector, 'get_schema_names') else [],
                'version': self._get_version()
            }
        except:
            return {}
    
    def _get_version(self) -> str:
        """Tenta obter versão do banco"""
        version_queries = {
            DatabaseType.SQL_SERVER: "SELECT @@VERSION",
            DatabaseType.MYSQL: "SELECT VERSION()",
            DatabaseType.POSTGRESQL: "SELECT version()",
            DatabaseType.ORACLE: "SELECT * FROM V$VERSION WHERE ROWNUM = 1",
            DatabaseType.SQLITE: "SELECT sqlite_version()"
        }
        
        query = version_queries.get(self.db_type)
        if not query:
            return "unknown"
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query).fetchone()
                return str(result[0]) if result else "unknown"
        except:
            return "unknown"
    
    def generate_system_prompt(self) -> str:
        """Gera prompt do sistema adaptado ao tipo de banco"""
        if not self.config:
            self.detect()
        
        quirks_text = "\n".join([f"- {q}" for q in self.config['quirks']])
        
        prompt = f"""Você é um assistente SQL especializado em {self.config['name']}.

INFORMAÇÕES DO BANCO:
- Dialeto: {self.config['dialect']}
- Sintaxe de Limit: {self.config['limit_syntax']}
- Exemplo: {self.config['limit_example']}

FUNÇÕES ESPECÍFICAS:
- Data atual: {self.config['current_date']}
- Tamanho de string: {self.config['string_length']}
- Concatenação: {self.config['string_concat']}

PECULIARIDADES IMPORTANTES:
{quirks_text}

INSTRUÇÕES:
1. SEMPRE use a sintaxe específica deste banco
2. Considere as peculiaridades listadas acima
3. Se não tiver certeza, prefira sintaxe padrão SQL
4. Retorne apenas SQL válido para {self.config['name']}
"""
        
        return prompt
```

**Uso:**

```python
from src.infrastructure.database_detector import DatabaseDetector

# Detecta automaticamente
detector = DatabaseDetector(database_url)
db_info = detector.detect()

print(f"Banco detectado: {db_info['name']}")
print(f"Dialeto: {db_info['dialect']}")

# Gera prompt adaptado
system_prompt = detector.generate_system_prompt()

# Usa no agent
agent = ReActAgent(
    tools=tools,
    llm=llm,
    system_prompt=system_prompt,
    ...
)
```

**Recursos de Estudo:**
- 📚 [SQL Dialects Comparison](https://www.jooq.org/translate/)
- 📚 [SQLAlchemy Dialects](https://docs.sqlalchemy.org/en/20/dialects/)
- 🎥 [YouTube: SQL Dialects Differences](https://www.youtube.com/results?search_query=sql+dialects+differences)

---

## 📊 Implementação por Fases

### **Fase 1: Fundação (1-2 dias)**

**Objetivo:** Preparar infraestrutura básica

**Tarefas:**
- [ ] Instalar dependências necessárias
- [ ] Implementar DatabaseDetector
- [ ] Criar estrutura de configs (YAML)
- [ ] Adicionar logging estruturado
- [ ] Testes básicos de detecção

**Comandos:**
```bash
pip install pyyaml pydantic tenacity chromadb
```

---

### **Fase 2: Schema Analysis (3-5 dias)**

**Objetivo:** Entender e documentar o banco

**Tarefas:**
- [ ] Implementar SchemaAnalyzer completo
- [ ] Integrar com LLM para documentação
- [ ] Criar relatórios de qualidade
- [ ] Exportar análises em JSON/HTML
- [ ] Testes com bancos reais

**Entregáveis:**
- Script de análise standalone
- Relatório de qualidade do banco
- Documentação automática de tabelas

---

### **Fase 3: Query Intelligence (3-5 dias)**

**Objetivo:** Adicionar retry e aprendizado

**Tarefas:**
- [ ] Implementar IntelligentQueryExecutor
- [ ] Configurar retry com Tenacity
- [ ] Integrar correção via LLM
- [ ] Adicionar logging de erros
- [ ] Testes de falha e recuperação

---

### **Fase 4: Learning System (1 semana)**

**Objetivo:** Sistema de aprendizado com RAG

**Tarefas:**
- [ ] Configurar ChromaDB
- [ ] Implementar QueryLearningSystem
- [ ] Integrar com QueryProcessor
- [ ] Criar dashboard de estatísticas
- [ ] Testes de similaridade

---

### **Fase 5: Integration & Polish (3-5 dias)**

**Objetivo:** Integrar tudo e refinar

**Tarefas:**
- [ ] Integrar todos os componentes
- [ ] Ajustar prompts do sistema
- [ ] Documentação completa
- [ ] Testes end-to-end
- [ ] Otimizações de performance

---

## 🛠️ Ferramentas e Tecnologias

### **Análise de Schema**

| Ferramenta | Uso | Complexidade | Licença |
|------------|-----|--------------|---------|
| **SQLAlchemy Inspector** | Introspeção de tabelas/colunas | ⭐⭐ | MIT |
| **Pandas** | Análise estatística de dados | ⭐⭐ | BSD |
| **Great Expectations** | Validação de qualidade | ⭐⭐⭐ | Apache 2.0 |
| **SQLFluff** | Linter SQL | ⭐⭐ | MIT |

### **Vector Databases**

| Ferramenta | Uso | Quando Usar | Custo |
|------------|-----|-------------|-------|
| **ChromaDB** | Local, leve, fácil | Projetos pequenos/médios | Grátis |
| **Pinecone** | Cloud, gerenciado | Produção, escala | Pago |
| **Qdrant** | Open-source, performático | Alta performance | Grátis |
| **pgvector** | Extensão PostgreSQL | Já usa PostgreSQL | Grátis |

### **LLMs e Embeddings**

| Modelo | Uso | Context Window | Custo |
|--------|-----|----------------|-------|
| **Gemini 1.5 Flash** | Rápido, atual no projeto | 1M tokens | Baixo |
| **Gemini 1.5 Pro** | Schemas complexos | 2M tokens | Médio |
| **GPT-4** | Melhor raciocínio | 128K tokens | Alto |
| **Claude 3.5** | Alternativa forte | 200K tokens | Alto |

### **Retry e Resilience**

| Ferramenta | Uso | Complexidade |
|------------|-----|--------------|
| **Tenacity** | Retry decorators | ⭐ |
| **Backoff** | Retry com backoff | ⭐ |
| **Celery** | Tasks assíncronas | ⭐⭐⭐ |

---

## 📚 Recursos de Estudo

### **Livros**

- 📖 "Designing Data-Intensive Applications" - Martin Kleppmann
- 📖 "Database Reliability Engineering" - Laine Campbell
- 📖 "SQL Performance Explained" - Markus Winand

### **Cursos Online**

- 🎓 [SQLAlchemy Complete Course](https://www.udemy.com/topic/sqlalchemy/)
- 🎓 [Vector Databases Crash Course](https://www.deeplearning.ai/short-courses/vector-databases-embeddings-applications/)
- 🎓 [LangChain & RAG](https://www.deeplearning.ai/short-courses/langchain-chat-with-your-data/)

### **Documentações Oficiais**

- 📚 [SQLAlchemy](https://docs.sqlalchemy.org/)
- 📚 [ChromaDB](https://docs.trychroma.com/)
- 📚 [LlamaIndex](https://docs.llamaindex.ai/)
- 📚 [Tenacity](https://tenacity.readthedocs.io/)
- 📚 [Great Expectations](https://docs.greatexpectations.io/)

### **Artigos e Papers**

- 📄 [RAG Explained](https://arxiv.org/abs/2005.11401)
- 📄 [Vector Similarity Search](https://www.pinecone.io/learn/vector-similarity/)
- 📄 [Database Schema Design Best Practices](https://www.sqlshack.com/database-schema-design-best-practices/)

### **Vídeos YouTube**

- 🎥 [Vector Databases Explained](https://www.youtube.com/watch?v=klTvEwg3oJ4)
- 🎥 [RAG Tutorial](https://www.youtube.com/results?search_query=retrieval+augmented+generation+tutorial)
- 🎥 [SQLAlchemy Advanced](https://www.youtube.com/results?search_query=sqlalchemy+advanced+tutorial)
- 🎥 [Database Design Patterns](https://www.youtube.com/results?search_query=database+design+patterns)

### **Comunidades**

- 💬 [SQLAlchemy Discord](https://discord.gg/sqlalchemy)
- 💬 [LlamaIndex Discord](https://discord.gg/llamaindex)
- 💬 [Stack Overflow - sql tag](https://stackoverflow.com/questions/tagged/sql)

---

## 🎯 Checklist de Estudos

### **Nível Iniciante**

- [ ] Entender conceitos de embeddings
- [ ] Praticar SQLAlchemy Inspector
- [ ] Estudar YAML/JSON para configs
- [ ] Aprender retry patterns básicos
- [ ] Configurar ChromaDB local

### **Nível Intermediário**

- [ ] Implementar schema analyzer básico
- [ ] Criar sistema de retry com LLM
- [ ] Entender RAG (Retrieval Augmented Generation)
- [ ] Trabalhar com múltiplos dialetos SQL
- [ ] Configurar logging estruturado

### **Nível Avançado**

- [ ] Otimizar performance de embeddings
- [ ] Implementar sistema de cache distribuído
- [ ] Criar métricas de qualidade customizadas
- [ ] Integrar múltiplos LLMs
- [ ] Deploy em produção com monitoramento

---

## 🚀 Próximos Passos

1. **Escolha uma fase** para começar
2. **Estude as ferramentas** necessárias para essa fase
3. **Implemente incrementalmente** - não tente fazer tudo de uma vez
4. **Teste com dados reais** - use bases problemáticas para validar
5. **Documente aprendizados** - mantenha um diário de desenvolvimento

---

## 📝 Notas Finais

Este guia foi criado para ser um **roteiro de estudos e implementação**. Cada seção pode ser expandida em projetos individuais.

**Recomendação:** Comece pela **Fase 1** e avance gradualmente. Não pule etapas!

**Lembre-se:** A melhor maneira de aprender é **fazendo**. Escolha um componente, estude e implemente.

---

**Versão:** 1.0  
**Data:** Outubro 2025  
**Autor:** Análise da Arquitetura do Chatbot SQL  
**Licença:** MIT
