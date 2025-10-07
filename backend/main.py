import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

app = FastAPI()

if not os.path.exists("downloads"):
    os.makedirs("downloads")

app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")

# Configuração de CORS (importante para o frontend)
origins = [
    "http://localhost:5173", # Adicione aqui a URL do seu frontend React/Vue
]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

class TitleRequest(BaseModel):
    prompt: str

# ROTA DE HEALTH CHECK (NOVA ROTA)
@app.get("/status")
def get_server_status():
    """Retorna o status do servidor e do serviço."""
    # Neste ponto, o simples fato de o FastAPI responder
    # já indica que o servidor Python está 'OK'.
    
    # Podemos adicionar uma verificação de dependências aqui,
    # como se o motor do DB foi inicializado, se quisermos ser mais robustos.
    try:
        from agent import engine
        db_status = "ok" if engine is not None else "erro_db"
    except Exception:
        # Se nem o 'agent' puder ser importado, o servidor está em modo de falha.
        db_status = "falha_import"
        
    return JSONResponse(content={
        "status": "ok",
        "service": "Chatbot SQL Agent",
        "db_status": db_status
    })

@app.post("/ask")
async def ask_agent(request: QueryRequest):
    # Importa o agente apenas quando necessário (evita custo/erros no startup)
    from agent import get_response  # lazy import
    response = await get_response(request.query)
    if not response["success"]:
        # Se o agente retornar 'success: False', levanta um erro 500
        raise HTTPException(status_code=500, detail=response["error"])
    return {"answer": response["data"]}

@app.post("/generate-title")
async def get_title(request: TitleRequest):
    # Importa o agente apenas quando necessário (evita custo/erros no startup)
    from agent import generate_chat_title  # lazy import
    title = await generate_chat_title(request.prompt)
    return {"title": title}

@app.get("/")
def root():
    return {"message": "API do Chatbot SQL está no ar!"}
