from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import os

from ..application.interfaces import IProcessQueryUseCase, ISessionManagementUseCase
from ..application.use_cases import ProcessQueryRequest


class QueryRequest(BaseModel):
    query: Optional[str] = None
    prompt: Optional[str] = None
    session_id: Optional[str] = None


class TitleRequest(BaseModel):
    prompt: Optional[str] = None
    query: Optional[str] = None


class SessionRequest(BaseModel):
    pass


class ChatController:
    def __init__(self, process_query_use_case: IProcessQueryUseCase):
        self._process_query_use_case = process_query_use_case

    async def process_query(self, request: QueryRequest) -> JSONResponse:
        query_text = request.prompt or request.query
        
        if not query_text:
            raise HTTPException(status_code=400, detail="Campo 'query' ou 'prompt' é obrigatório")
        
        if query_text.strip().startswith(("Assistente:", "Assistant:")):
            raise HTTPException(status_code=400, detail="Mensagem inválida: não envie mensagens do assistente")
        
        use_case_request = ProcessQueryRequest(
            query=query_text.strip(),
            session_id=request.session_id or ""
        )
        
        response = await self._process_query_use_case.execute(use_case_request)
        
        if not response.success:
            error_code = response.error_code or "GENERIC_ERROR"
            
            if error_code in ["QUOTA_EXCEEDED", "RATE_LIMIT", "RESOURCE_EXHAUSTED"]:
                status_code = 429
            elif error_code in ["API_KEY_INVALID", "BILLING_NOT_ENABLED"]:
                status_code = 401
            elif error_code == "TIMEOUT":
                status_code = 504
            else:
                status_code = 500
            
            raise HTTPException(status_code=status_code, detail=response.__dict__)
        
        return JSONResponse({
            "answer": response.data,
            "session_id": response.session_id,
            "context_used": response.context_used
        })


class SessionController:
    def __init__(self, session_management_use_case: ISessionManagementUseCase):
        self._session_management_use_case = session_management_use_case

    def create_session(self) -> JSONResponse:
        response = self._session_management_use_case.create_session()
        return JSONResponse({
            "session_id": response.session_id,
            "message": "Sessão criada com sucesso"
        })

    def get_session_stats(self, session_id: str) -> JSONResponse:
        response = self._session_management_use_case.get_session_stats(session_id)
        
        if not response:
            return JSONResponse({
                "message": "Sessão não encontrada. Uma nova sessão será criada automaticamente na próxima mensagem.",
                "session_exists": False
            }, status_code=200)
        
        return JSONResponse({**response.__dict__, "session_exists": True})

    def cleanup_sessions(self) -> JSONResponse:
        self._session_management_use_case.cleanup_expired_sessions()
        return JSONResponse({"message": "Limpeza de sessões executada"})


def create_app(
    chat_controller: ChatController,
    session_controller: SessionController
) -> FastAPI:
    app = FastAPI(
        title="Chatbot SQL API",
        description="API para chatbot de consultas SQL com contexto conversacional"
    )

    origins = ["http://localhost:5173"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")

    @app.get("/status")
    def get_server_status():
        return JSONResponse({
            "status": "ok",
            "service": "Chatbot SQL Agent",
            "dbStatus": "connected"
        })

    @app.post("/ask")
    async def ask_agent(request: QueryRequest):
        return await chat_controller.process_query(request)

    @app.post("/sessions")
    def create_session():
        return session_controller.create_session()

    @app.get("/sessions/{session_id}/stats")
    def get_session_info(session_id: str):
        return session_controller.get_session_stats(session_id)

    @app.post("/sessions/cleanup")
    def cleanup_sessions():
        return session_controller.cleanup_sessions()

    @app.post("/generate-title")
    async def generate_title(request: TitleRequest):
        try:
            text = request.prompt or request.query or "Nova conversa"
            text = text.strip()
            title = text[:50] + "..." if len(text) > 50 else text
            return JSONResponse({"title": title})
        except Exception:
            return JSONResponse({"title": "Nova conversa"}, status_code=200)

    @app.get("/")
    def root():
        return {"message": "API do Chatbot SQL está no ar!"}

    return app