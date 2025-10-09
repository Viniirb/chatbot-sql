import os
import sys
import warnings
import logging

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('google_genai').setLevel(logging.WARNING)
logging.getLogger('llama_index').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.ERROR)

print("🚀 Chatbot SQL - Inicializando...")

os.environ.setdefault('PYTHONWARNINGS', 'ignore::UserWarning,ignore::DeprecationWarning')
warnings.filterwarnings("ignore", category=Warning, module="pydantic")
warnings.filterwarnings("ignore", message=".*validate_default.*")
warnings.filterwarnings("ignore", message=".*UnsupportedFieldAttributeWarning.*")
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

from fastapi.staticfiles import StaticFiles
downloads_path = os.path.join(os.getcwd(), "downloads")
if os.path.exists(downloads_path):
    app.mount("/downloads", StaticFiles(directory=downloads_path), name="downloads")

print("✅ Aplicação pronta!")

if __name__ == "__main__":
    import subprocess
    os.environ["PYTHONUNBUFFERED"] = "1"
    print("🌐 Servidor iniciado em http://127.0.0.1:8000 com múltiplos workers\n")
    # Executa uvicorn com múltiplos workers via subprocess
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--workers", "1",
        "--log-level", "warning",
        "--no-access-log"
    ])
