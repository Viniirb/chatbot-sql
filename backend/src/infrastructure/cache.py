import os
import json
from typing import Any, Optional
from pathlib import Path


class Cache:
    """Cache simples com persistência em arquivo JSON.

    Uso:
        cache = Cache(persist_path='data/schema_cache.json')
        cache.set(key, value)
        data = cache.get(key)
    """

    def __init__(self, persist_path: Optional[str] = None, auto_save: bool = True):
        # Default: use existing backend/cache/ directory (project-level cache)
        root = Path(__file__).resolve().parent.parent.parent
        default_dir = root / "cache"
        default_dir.mkdir(parents=True, exist_ok=True)
        self.persist_path = Path(persist_path) if persist_path else default_dir / "schema_cache.json"
        self._store = {}
        self.auto_save = auto_save
        self._load_from_file()

    def _load_from_file(self):
        try:
            if self.persist_path.exists():
                with open(self.persist_path, 'r', encoding='utf-8') as f:
                    self._store = json.load(f)
        except Exception:
            # Se falhar no load, inicia com cache vazio e loga o erro
            print(f"❌ Falha ao carregar cache de {self.persist_path}, iniciando cache vazio")
            self._store = {}

    def _save_to_file(self):
        try:
            tmp_path = self.persist_path.with_suffix('.tmp')
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(self._store, f, indent=2, ensure_ascii=False)
            # Replace atomically
            os.replace(tmp_path, self.persist_path)
        except Exception:
            # Falha em salvar não deve quebrar a aplicação, mas logamos para debug
            print(f"⚠️ Falha ao salvar cache em {self.persist_path}")

    def get(self, key: str) -> Any:
        return self._store.get(key)

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value
        if self.auto_save:
            self._save_to_file()

    def clear(self) -> None:
        self._store.clear()
        try:
            if self.persist_path.exists():
                self.persist_path.unlink()
        except Exception:
            pass

    def dump(self) -> dict:
        """Retorna o conteúdo atual do cache (útil para debugging)."""
        return dict(self._store)
