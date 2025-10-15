from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
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
from ..infrastructure.service.schema_service import SchemaService
from ..application.use_cases import ProcessQueryRequest
from ..domain.export_entities import ExportFormat
from datetime import datetime


class QueryRequest(BaseModel):
    query: Optional[str] = None
    prompt: Optional[str] = None
    session_id: Optional[str] = None
    client_message_id: Optional[str] = None


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
    session: Optional[dict] = None


class ChatController:
    def __init__(self, process_query_use_case: IProcessQueryUseCase, schema_service: SchemaService = None):
        self._process_query_use_case = process_query_use_case
        self._schema_service = schema_service or SchemaService()

    async def process_query(self, request: QueryRequest, request_id: Optional[str] = None) -> JSONResponse:
        query_text = request.prompt or request.query
        if not query_text:
            raise HTTPException(status_code=400, detail="Campo 'query' ou 'prompt' é obrigatório")
        print(f"💬 {query_text[:80]}..." if len(query_text) > 80 else f"💬 {query_text}")
        if query_text.strip().startswith(("Assistente:", "Assistant:")):
            raise HTTPException(status_code=400, detail="Mensagem inválida: não envie mensagens do assistente")
        use_case_request = ProcessQueryRequest(
            query=query_text.strip(),
            session_id=request.session_id or "",
            request_id=request_id,
            client_message_id=request.client_message_id
        )
        schema_analysis = self._schema_service.get_schema_analysis(force_refresh=False)
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
            "context_used": response.context_used,
            "schema_analysis": schema_analysis
        })


class SessionController:
    def __init__(self, session_management_use_case: ISessionManagementUseCase, schema_service: SchemaService = None):
        self._session_management_use_case = session_management_use_case
        self._schema_service = schema_service or SchemaService()

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
        schema_analysis = self._schema_service.get_schema_analysis(force_refresh=False)
        if not response:
            new_session = self._session_management_use_case.create_session()
            return JSONResponse({
                "session_id": new_session.session_id,
                "message_count": 0,
                "query_count": 0,
                "created_at": new_session.created_at,
                "session_exists": True,
                "agent": agent_info,
                "message": "Nova sessão criada automaticamente",
                "schema_analysis": schema_analysis
            }, status_code=200)
        return JSONResponse({**response.__dict__, "session_exists": True, "agent": agent_info, "schema_analysis": schema_analysis})
    
    def update_session_stats(self, session_id: str, request: SessionStatsUpdateRequest) -> JSONResponse:
        """Atualiza as estatísticas de uma sessão"""
        try:
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
    def __init__(self, export_use_case: IExportSessionUseCase, schema_service: SchemaService = None):
        self._export_use_case = export_use_case
        self._schema_service = schema_service or SchemaService()

    def export_session(self, session_id: str, request: ExportRequest):
        now = datetime.now().strftime("%H:%M:%S")
        has_payload = bool(request.session)
        payload_id = request.session.get('id') if has_payload and isinstance(request.session, dict) else None
        print(f"📤 EXPORT_REQUEST session_id={session_id} format={request.format} payload_present={has_payload} payload_id={payload_id} — {now} — DEBUG", flush=True)
        schema_analysis = self._schema_service.get_schema_analysis(force_refresh=False)
        try:
            export_format = ExportFormat(request.format.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Formato inválido. Formatos válidos: pdf, json, txt"
            )
        try:
            result = self._export_use_case.execute(session_id, export_format, session_payload=request.session)
            headers = {"Content-Disposition": f'attachment; filename="{result.filename}"'}
            return Response(content=result.content, media_type=result.content_type, headers=headers)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao exportar sessão: {str(e)}")



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
        print(f"{status_emoji} {request.method} {request.url.path} - {response.status_code} - {timestamp}")
        
        return response

    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    @app.post("/sessions/{session_id}/sync")
    def sync_session(session_id: str, request: dict):
        print(f"SYNC PAYLOAD: {request}", flush=True)
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

    from fastapi import Request

    @app.post("/ask")
    async def ask_agent(body: QueryRequest, fastapi_request: Request):
        import sys
        print("🔴🔴🔴 ROTA /ask CHAMADA! 🔴🔴🔴", flush=True)
        print(f"Request: {body}", flush=True)
        
        client_req_id = None
        try:
            client_req_id = fastapi_request.headers.get('x-request-id') or fastapi_request.headers.get('X-Request-ID')
        except Exception:
            client_req_id = None
        sys.stdout.flush()
        
        result = await chat_controller.process_query(body, client_req_id)
        
        print("🟢🟢🟢 ROTA /ask RETORNANDO! 🟢🟢🟢", flush=True)
        print(f"Result type: {type(result)}", flush=True)
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

    @app.post("/sessions/{session_id}/sync")
    def sync_session(session_id: str, request: dict):
        """
        Recebe payload completo da sessão do frontend e atualiza/cria sessão interna.
        Espera um dict com pelo menos: id, messages, createdAt, updatedAt, title, etc.
        """
        from ..domain.entities import Session, SessionId, Message
        from datetime import datetime
        session_service = session_controller._session_management_use_case._session_service
        session = session_service.get_session(session_id)
        if not session:
            session = Session(SessionId(session_id), title=request.get('title'))
        else:
            session.title = request.get('title', session.title)
        session.created_at = datetime.fromisoformat(request.get('createdAt')) if request.get('createdAt') else session.created_at
        session.updated_at = datetime.fromisoformat(request.get('updatedAt')) if request.get('updatedAt') else session.updated_at
        
        messages = request.get('messages', [])
        session._message_history = []
        for msg in messages:
            m = Message(
                role=msg.get('role'),
                content=msg.get('content'),
                timestamp=datetime.fromisoformat(msg.get('timestamp')) if msg.get('timestamp') else datetime.now(),
                metadata=msg.get('metadata', {})
            )
            session._message_history.append(m)
        session.stats.message_count = len(session._message_history)
        client_query_count = request.get('queryCount', None)
        if client_query_count is not None:
            try:
                client_q = int(client_query_count)
                session.stats.query_count = max(session.stats.query_count, client_q)
            except Exception:
                pass
        
        if not session_service.get_session(session_id) and client_query_count is not None:
            try:
                session.stats.query_count = int(client_query_count)
            except Exception:
                pass
        session.stats.updated_at = datetime.now()
        session_service.save_session(session)
        return JSONResponse({
                    "session_id": session.session_id.value,
                    "message_count": session.stats.message_count,
                    "query_count": session.stats.query_count,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "status": "synced"
                })

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

    @app.post('/requests/{request_id}/cancel')
    async def cancel_request(request_id: str):
        from ..infrastructure.execution_context import set_cancel
        try:
            set_cancel(request_id)
            return JSONResponse({"status": "cancellation_requested", "request_id": request_id})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to cancel request: {e}")

    return app
    return app