from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from typing import Optional
import os

from ..application.interfaces import (
    IProcessQueryUseCase, ISessionManagementUseCase, IExportSessionUseCase,
    UpdateSessionStatsRequest
)
from ..application.use_cases import ProcessQueryRequest
from ..domain.export_entities import ExportFormat


class QueryRequest(BaseModel):
    query: Optional[str] = None
    prompt: Optional[str] = None
    session_id: Optional[str] = None


class TitleRequest(BaseModel):
    prompt: Optional[str] = None
    query: Optional[str] = None


class SessionRequest(BaseModel):
    pass


class SessionStatsUpdateRequest(BaseModel):
    """Request para atualizar estatísticas da sessão"""
    messageCount: int = Field(..., alias="messageCount", ge=0)
    queryCount: int = Field(..., alias="queryCount", ge=0)
    timestamp: str
    
    class Config:
        populate_by_name = True


class ExportRequest(BaseModel):
    format: str


class ChatController:
    def __init__(self, process_query_use_case: IProcessQueryUseCase):
        self._process_query_use_case = process_query_use_case

    async def process_query(self, request: QueryRequest) -> JSONResponse:
        query_text = request.prompt or request.query
        
        if not query_text:
            raise HTTPException(status_code=400, detail="Campo 'query' ou 'prompt' é obrigatório")
        
        print(f"💬 {query_text[:80]}..." if len(query_text) > 80 else f"💬 {query_text}")
        
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
        
        agent_info = {
            "model": "gemini-2.5-flash-lite",
            "temperature": 0.2,
            "max_tokens": 2048,
            "provider": "Google Gemini API"
        }
        
        if not response:
            new_session = self._session_management_use_case.create_session()
            return JSONResponse({
                "session_id": new_session.session_id,
                "message_count": 0,
                "query_count": 0,
                "created_at": new_session.created_at,
                "session_exists": True,
                "agent": agent_info,
                "message": "Nova sessão criada automaticamente"
            }, status_code=200)
        
        return JSONResponse({**response.__dict__, "session_exists": True, "agent": agent_info})
    
    def update_session_stats(self, session_id: str, request: SessionStatsUpdateRequest) -> JSONResponse:
        """Atualiza as estatísticas de uma sessão"""
        try:
            # Converte o request do Pydantic para o formato do use case
            use_case_request = UpdateSessionStatsRequest(
                message_count=request.messageCount,
                query_count=request.queryCount,
                timestamp=request.timestamp
            )
            
            response = self._session_management_use_case.update_session_stats(session_id, use_case_request)
            
            return JSONResponse({
                "sessionId": response.session_id,
                "messageCount": response.message_count,
                "queryCount": response.query_count,
                "updatedAt": response.updated_at,
                "status": response.status
            })
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao atualizar estatísticas: {str(e)}")

    def cleanup_sessions(self) -> JSONResponse:
        self._session_management_use_case.cleanup_expired_sessions()
        return JSONResponse({"message": "Limpeza de sessões executada"})


class ExportController:
    def __init__(self, export_use_case: IExportSessionUseCase):
        self._export_use_case = export_use_case

    def export_session(self, session_id: str, request: ExportRequest) -> JSONResponse:
        try:
            export_format = ExportFormat(request.format.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Formato inválido. Formatos válidos: pdf, json, txt"
            )
        
        try:
            result = self._export_use_case.execute(session_id, export_format)
            
            response_data = {
                "success": True,
                "filename": result.filename,
                "filepath": result.filepath,
                "download_url": f"/downloads/exports/{result.filename}" if result.filepath else None,
                "message": "Exportação realizada com sucesso"
            }
            
            return JSONResponse(content=response_data)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao exportar sessão: {str(e)}")


def create_app(
    chat_controller: ChatController,
    session_controller: SessionController,
    export_controller: ExportController
) -> FastAPI:
    app = FastAPI(
        title="Chatbot SQL API",
        description="API para chatbot de consultas SQL com contexto conversacional"
    )

    @app.middleware("http")
    async def log_requests(request, call_next):
        from datetime import datetime
        
        response = await call_next(request)
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_emoji = "✅" if 200 <= response.status_code < 300 else "❌"
        print(f"{status_emoji} [{timestamp}] {request.method} {request.url.path} - {response.status_code}")
        
        return response

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
    
    if not os.path.exists("downloads/exports"):
        os.makedirs("downloads/exports")

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
        import sys
        print("\n" + "🟥"*35, flush=True)
        print("🔴🔴🔴 ROTA /ask CHAMADA! 🔴🔴🔴", flush=True)
        print(f"Request: {request}", flush=True)
        print("🟥"*35 + "\n", flush=True)
        sys.stdout.flush()
        
        result = await chat_controller.process_query(request)
        
        print("\n" + "🟩"*35, flush=True)
        print("🟢🟢🟢 ROTA /ask RETORNANDO! 🟢🟢🟢", flush=True)
        print(f"Result type: {type(result)}", flush=True)
        print("🟩"*35 + "\n", flush=True)
        sys.stdout.flush()
        
        return result

    @app.post("/sessions")
    def create_session():
        return session_controller.create_session()

    @app.get("/sessions/{session_id}/stats")
    def get_session_info(session_id: str):
        return session_controller.get_session_stats(session_id)
    
    @app.post("/sessions/{session_id}/stats")
    def update_session_stats(session_id: str, request: SessionStatsUpdateRequest):
        return session_controller.update_session_stats(session_id, request)

    @app.post("/sessions/cleanup")
    def cleanup_sessions():
        return session_controller.cleanup_sessions()

    @app.post("/sessions/{session_id}/export")
    def export_session(session_id: str, request: ExportRequest):
        return export_controller.export_session(session_id, request)

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