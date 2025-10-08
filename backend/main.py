import os
import warnings

warnings.filterwarnings("ignore", category=Warning, module="pydantic._internal._generate_schema")
warnings.filterwarnings("ignore", message=".*validate_default.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited")

from dotenv import load_dotenv

load_dotenv()

_app = None

def get_app():
    global _app
    if _app is None:
        from src.infrastructure.container import create_configured_app
        _app = create_configured_app()
    return _app

app = get_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
