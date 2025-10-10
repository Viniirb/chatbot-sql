"""Run the application in development mode with compact, readable logs.

This script intentionally keeps terminal output concise: it configures a
compact logging formatter, mutes noisy libraries, and disables Uvicorn
access logs to avoid excessive lines while still showing warnings and
exceptions with stack traces.
"""
import os
import sys
import logging
from datetime import datetime

os.environ["PYTHONUNBUFFERED"] = "1"


def setup_logging() -> None:
    """Configure a compact logger for development."""
    root = logging.getLogger()

    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    fmt = "[%(asctime)s] %(levelname)s: %(message)s"
    datefmt = "%H:%M:%S"
    handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    root.setLevel(logging.DEBUG)
    root.addHandler(handler)

    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('google_genai').setLevel(logging.WARNING)
    logging.getLogger('llama_index').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.ERROR)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)
    def startup_print(msg: str) -> None:
        """Print a concise startup message (emoji + text) without logging metadata.

        For most startup traces we prefer a clean line like:
            ✅ Chatbot SQL — modo desenvolvimento

        The debug-level log (with timestamp/level) will be emitted only for the
        single-process server start message as requested.
        """
        print(f"✅ {msg}", flush=True)

    def warn(msg: str) -> None:
        logger.warning(f"⚠️  {msg}")

    def error(msg: str) -> None:
        logger.error(f"💥 {msg}")

    startup_print("Chatbot SQL — modo desenvolvimento")
    startup_print("Iniciando servidor em http://127.0.0.1:8000 (hot reload ativado)")
    startup_print("Logs compactos: apenas warnings e erros exibidos")

    try:
        import uvicorn

        dev_reload = os.getenv("DEV_RELOAD", "0") in ("1", "true", "True")

        if dev_reload:
            now = datetime.now().strftime("%H:%M:%S")
            print(f"✅ Modo DEV_RELOAD ativo: hot-reload habilitado — {now}", flush=True)
            uvicorn.run(
                "main:app",
                host="127.0.0.1",
                port=8000,
                reload=True,
                reload_dirs=["src"],
                workers=1,
                log_level="warning",
                access_log=False,
                use_colors=True,
                loop="asyncio",
            )
        else:
            now = datetime.now().strftime("%H:%M:%S")
            print(f"⏳ Iniciando servidor — {now}", flush=True)
            uvicorn.run(
                "main:app",
                host="127.0.0.1",
                port=8000,
                reload=False,
                log_level="warning",
                access_log=False,
                use_colors=True,
                loop="asyncio",
            )
    except KeyboardInterrupt:
        now = datetime.now().strftime("%H:%M:%S")
        print(f"⚠️ Encerrando servidor (KeyboardInterrupt) — {now} — INFO", flush=True)
    except Exception as e:
        now = datetime.now().strftime("%H:%M:%S")
        print(f"💥 Servidor caiu: {str(e)} — {now} — ERROR", flush=True)
        import traceback
        traceback.print_exc()
        raise
