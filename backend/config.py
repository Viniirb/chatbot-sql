"""
Configurações do Chatbot SQL com LlamaIndex e Gemini
"""
import os
from typing import Dict, Any

# Configurações do Gemini LLM
GEMINI_CONFIG = {
    "model_name": "models/gemini-2.5-flash",
    "temperature": 0.1,  # Baixa para maior precisão em SQL
    "max_tokens": 4096,
    "top_p": 0.95
}

# Configurações do Embedding
EMBEDDING_CONFIG = {
    "model_name": "models/embedding-001",
    "embed_batch_size": 10
}

# Configurações do LlamaIndex
LLAMA_INDEX_CONFIG = {
    "chunk_size": 1024,
    "chunk_overlap": 200
}

# Configurações do SQLDatabase
SQL_CONFIG = {
    "include_tables": None,  # None = todas as tabelas
    "sample_rows_in_table_info": 3
}

# Configurações do Query Engine
QUERY_ENGINE_CONFIG = {
    "synthesize_response": True,
    "streaming": False,
    "return_raw": False
}

# Configurações do ReAct Agent
AGENT_CONFIG = {
    "verbose": True,
    "max_iterations": 10
}

# Configurações da memória
MEMORY_CONFIG = {
    "token_limit": 4000
}

# Configurações de exportação
EXPORT_CONFIG = {
    "max_excel_rows": 100000,
    "max_csv_rows": 500000,
    "max_pdf_rows": 1000,
    "max_pdf_columns": 8,
    "csv_chunk_size": 50000
}

# Configurações do banco de dados
DB_CONFIG = {
    "pool_pre_ping": True,
    "pool_recycle": 3600,
    "echo": False,
    "fast_executemany": True  # Para SQL Server
}

def get_config() -> Dict[str, Any]:
    """Retorna todas as configurações consolidadas."""
    return {
        "gemini": GEMINI_CONFIG,
        "embedding": EMBEDDING_CONFIG,
        "llama_index": LLAMA_INDEX_CONFIG,
        "sql": SQL_CONFIG,
        "query_engine": QUERY_ENGINE_CONFIG,
        "agent": AGENT_CONFIG,
        "memory": MEMORY_CONFIG,
        "export": EXPORT_CONFIG,
        "database": DB_CONFIG
    }