import uuid
from typing import Optional
from datetime import datetime

from .interfaces import (
    IProcessQueryUseCase, ISessionManagementUseCase, IQueryProcessorService, ISessionService,
    ProcessQueryRequest, ProcessQueryResponse, CreateSessionResponse, SessionStatsResponse
)
from ..domain.entities import Session, SessionId, Message


class ProcessQueryUseCase(IProcessQueryUseCase):
    def __init__(self, session_service: ISessionService, query_processor: IQueryProcessorService):
        self._session_service = session_service
        self._query_processor = query_processor

    async def execute(self, request: ProcessQueryRequest) -> ProcessQueryResponse:
        try:
            if not request.query.strip():
                return ProcessQueryResponse(
                    success=False,
                    error="Query vazia fornecida."
                )

            session_id = request.session_id or str(uuid.uuid4())
            session = self._session_service.get_session(session_id)
            
            if not session:
                print(f"[SESSION] Sessão {session_id} não encontrada. Criando nova sessão...")
                session = self._session_service.create_session()
                session_id = session.session_id.value
                print(f"[SESSION] Nova sessão criada: {session_id}")
            else:
                print(f"[SESSION] Usando sessão existente: {session_id}")

            user_message = Message(
                role="user",
                content=request.query,
                timestamp=datetime.now(),
                metadata={}
            )
            session.add_message(user_message)

            response_text = await self._query_processor.process_query(request.query, session)

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

        except Exception as e:
            return ProcessQueryResponse(
                success=False,
                error=f"Erro ao processar consulta: {str(e)}",
                error_code="PROCESSING_ERROR"
            )


class SessionManagementUseCase(ISessionManagementUseCase):
    def __init__(self, session_service: ISessionService):
        self._session_service = session_service

    def create_session(self) -> CreateSessionResponse:
        session = self._session_service.create_session()
        return CreateSessionResponse(session_id=session.session_id.value)

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
            created_at=session.created_at.timestamp(),
            last_activity=session.last_activity.timestamp(),
            message_count=len(session.message_history),
            has_active_dataset=session.active_dataset is not None,
            active_dataset_info=active_dataset_info
        )

    def cleanup_expired_sessions(self) -> None:
        self._session_service.cleanup_expired_sessions()