from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    url: str


@dataclass 
class GoogleAIConfig:
    api_key: str
    model_name: str = "gemini-2.5-flash-lite"
    temperature: float = 0.2
    max_tokens: int = 2048
    top_p: float = 0.95


@dataclass
class EmbeddingConfig:
    model_name: str = "models/embedding-001"
    embed_batch_size: int = 10


@dataclass
class LlamaIndexConfig:
    chunk_size: int = 1024
    chunk_overlap: int = 200


@dataclass
class SessionConfig:
    timeout_seconds: int = 3600


@dataclass
class AppConfig:
    database: DatabaseConfig
    google_ai: GoogleAIConfig
    embedding: EmbeddingConfig
    llama_index: LlamaIndexConfig
    session: SessionConfig