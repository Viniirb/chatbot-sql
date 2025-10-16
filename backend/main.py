import os
import sys
import warnings
import logging
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("llama_index").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.ERROR)

os.environ.setdefault(
    "PYTHONWARNINGS", "ignore::UserWarning,ignore::DeprecationWarning"
)
warnings.filterwarnings("ignore", category=Warning, module="pydantic")
warnings.filterwarnings("ignore", message=".*validate_default.*")
warnings.filterwarnings("ignore", message=".*UnsupportedFieldAttributeWarning.*")
warnings.filterwarnings(
    "ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited"
)

load_dotenv()

_app = None

def get_app():
    global _app
    if _app is None:
        from src.infrastructure.container import create_configured_app

        _app = create_configured_app()
    return _app

app = get_app()

downloads_path = os.path.join(os.getcwd(), "downloads")
if os.path.exists(downloads_path):
    app.mount("/downloads", StaticFiles(directory=downloads_path), name="downloads")
