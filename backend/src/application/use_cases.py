import uuid
import asyncio
from typing import Optional
from datetime import datetime

from .interfaces import (
    IProcessQueryUseCase, ISessionManagementUseCase, IQueryProcessorService, ISessionService,
    ProcessQueryRequest, ProcessQueryResponse, CreateSessionResponse, SessionStatsResponse,
    UpdateSessionStatsRequest, UpdateSessionStatsResponse
)
from ..domain.entities import Session, SessionId, Message


class ProcessQueryUseCase(IProcessQueryUseCase):
    def __init__(self, session_service: ISessionService, query_processor: IQueryProcessorService):
        self._session_service = session_service
        self._query_processor = query_processor

    async def execute(self, request: ProcessQueryRequest) -> ProcessQueryResponse:
        import sys
        print(f"\n🔵 USE CASE: Iniciando execução...", flush=True)
        print(f"   Query: {request.query[:100]}", flush=True)
        print(f"   Session: {request.session_id or 'nova'}", flush=True)
        sys.stdout.flush()
        
        try:
            if not request.query.strip():
                return ProcessQueryResponse(
                    success=False,
                    error="Query vazia fornecida."
                )

            session_id = request.session_id or str(uuid.uuid4())
            session = self._session_service.get_session(session_id)
            
            if not session:
                session = self._session_service.create_session()
                session_id = session.session_id.value

            user_message = Message(
                role="user",
                content=request.query,
                timestamp=datetime.now(),
                metadata={}
            )
            session.add_message(user_message)

            print(f"\n🔵 USE CASE: Chamando query_processor...")
            
            response_text = await self._query_processor.process_query(request.query, session, request.request_id)
            
            print(f"\n🔵 USE CASE: Resposta recebida do processor")
            print(f"   Resposta: {response_text[:100]}...")

            assistant_message = Message(
                role="assistant", 
                content=response_text,
                timestamp=datetime.now(),
                metadata={}
            )
            session.add_message(assistant_message)
            
            self._session_service.save_session(session)

            return ProcessQueryResponse(
                success=True,
                data=response_text,
                session_id=session_id,
                context_used=True
            )

        except asyncio.CancelledError:
            # Request was cancelled (client disconnected or cancel endpoint used).
            print("⚪️ USE CASE: execução cancelada pelo cliente", flush=True)
            return ProcessQueryResponse(
                success=False,
                error="Operação cancelada pelo cliente",
                error_code="CANCELLED",
                error_type="CANCELLED"
            )
        except Exception as e:
            import traceback, re
            error_msg = str(e)
            print(f"\n{'='*70}")
            print(f"❌ ERRO CAPTURADO NO USE CASE")
            print(f"Erro: {error_msg}")
            print(f"\nTraceback completo:")
            print(traceback.format_exc())
            print(f"{'='*70}\n")

            # Detecta erro de quota/rate limit do Gemini
            if "429" in error_msg and ("quota" in error_msg.lower() or "RESOURCE_EXHAUSTED" in error_msg or "Too Many Requests" in error_msg):
                retry_match = re.search(r'retry in ([0-9]+)', error_msg)
                retry_seconds = int(retry_match.group(1)) if retry_match else 30
                return ProcessQueryResponse(
                    success=False,
                    error="Limite de requisições atingido. Tente novamente em alguns segundos.",
                    error_code="QUOTA_EXCEEDED",
                    error_type="QUOTA_ERROR",
                    retry_after=retry_seconds
                )
            # Erro de limite de tokens do modelo (caso comum)
            if 'MAX_TOKENS' in error_msg or 'Response was terminated early' in error_msg:
                return ProcessQueryResponse(
                    success=False,
                    error=("A resposta do modelo foi interrompida por limite de tokens. "
                           "Tente uma pergunta mais curta, divida a consulta em partes, "
                           "ou reduza o contexto enviado."),
                    error_code="MAX_TOKENS",
                    error_type="MODEL_ERROR"
                )

            # Erro genérico
            return ProcessQueryResponse(
                success=False,
                error=f"Erro ao processar consulta: {error_msg}",
                error_code="PROCESSING_ERROR",
                error_type="SERVER_ERROR"
            )


class SessionManagementUseCase(ISessionManagementUseCase):
    def __init__(self, session_service: ISessionService):
        self._session_service = session_service

    def create_session(self) -> CreateSessionResponse:
        session = self._session_service.create_session()
        return CreateSessionResponse(
            session_id=session.session_id.value,
            created_at=session.created_at.isoformat()
        )

    def get_session_stats(self, session_id: str) -> Optional[SessionStatsResponse]:
        session = self._session_service.get_session(session_id)
        if not session:
            return None

        active_dataset_info = None
        if session.active_dataset:
            active_dataset_info = {
                "row_count": session.active_dataset.row_count,
                "columns": session.active_dataset.columns
            }

        return SessionStatsResponse(
            session_id=session_id,
            created_at=session.created_at.isoformat(),
            last_activity=session.last_activity.isoformat(),
            message_count=len(session.message_history),
            has_active_dataset=session.active_dataset is not None,
            active_dataset_info=active_dataset_info,
            query_count=session.stats.query_count,
            updated_at=session.stats.updated_at.isoformat()
        )
    
    def update_session_stats(self, session_id: str, request: UpdateSessionStatsRequest) -> UpdateSessionStatsResponse:
        """Atualiza as estatísticas de uma sessão"""
        session = self._session_service.get_session(session_id)
        
        if not session:
            # Se a sessão não existe, cria uma nova
            session = self._session_service.create_session()
            session_id = session.session_id.value
        
        # Atualiza as estatísticas
        session.update_stats(request.message_count, request.query_count)
        self._session_service.save_session(session)
        
        return UpdateSessionStatsResponse(
            session_id=session_id,
            message_count=session.stats.message_count,
            query_count=session.stats.query_count,
            updated_at=session.stats.updated_at.isoformat(),
            status="synced"
        )

    def cleanup_expired_sessions(self) -> None:
        self._session_service.cleanup_expired_sessions()