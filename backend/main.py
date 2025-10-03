from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from agent import get_response

app = FastAPI()

origins = ["http://localhost:5173", "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

@app.post("/ask")
async def ask_agent(request: QueryRequest):
    response = get_response(request.query)
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["error"])
    return {"answer": response["data"]}

@app.get("/")
def root():
    return {"message": "API do Chatbot SQL está no ar!"}


# Adicione esta linha no final do arquivo:
print(">>> Arquivo agent.py foi executado até o fim sem erros.")