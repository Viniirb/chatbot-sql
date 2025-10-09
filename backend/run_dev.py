"""
Script para rodar em modo desenvolvimento COM logs visíveis
Usa reload mas configura corretamente para ver os prints
"""
import os
import sys

os.environ["PYTHONUNBUFFERED"] = "1"

if __name__ == "__main__":
    import uvicorn
    
    print("="*70)
    print("🚀 MODO DESENVOLVIMENTO - Logs visíveis")
    print("="*70)
    
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["src"],
        workers=1,
        log_level="info",
        access_log=True,
        use_colors=True,
        loop="asyncio"
    )
