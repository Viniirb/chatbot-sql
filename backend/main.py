import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()

if not os.path.exists("downloads"):
    os.makedirs("downloads")

app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")

origins = [
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

class TitleRequest(BaseModel):
    prompt: str

@app.post("/ask")
async def ask_agent(request: QueryRequest):
    # Importa o agente apenas quando necessário (evita custo/erros no startup)
    from agent import get_response  # lazy import
    response = await get_response(request.query)
    if not response["success"]:
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