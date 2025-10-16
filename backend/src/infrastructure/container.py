from functools import lru_cache
from typing import Dict, Any
import os
import logging
from datetime import datetime

from ..application.interfaces import (
    IProcessQueryUseCase,
    ISessionManagementUseCase,
    ISessionService,
    IQueryProcessorService,
    IExportSessionUseCase,
)
from ..application.use_cases import ProcessQueryUseCase, SessionManagementUseCase
from ..application.export_use_case import ExportSessionUseCase
from .service.services import SessionService, InMemorySessionRepository
from ..infrastructure.adapters import QueryProcessorService, QueryContextEnhancer
from ..infrastructure.lazy_agent import LazyAgentFactory
from ..presentation.controllers import (
    ChatController,
    SessionController,
    ExportController,
    create_app,
)

logger = logging.getLogger(__name__)

CONTAINER_VERBOSE = os.getenv("CONTAINER_VERBOSE", "0") in ("1", "true", "True")
CONTAINER_EMOJI = os.getenv("CONTAINER_EMOJI", "0") in ("1", "true", "True")


class DIContainer:
    def __init__(self):
        self._services: Dict[type, Any] = {}
        self._singletons: Dict[type, Any] = {}

    def register_singleton(self, interface: type, implementation: Any):
        self._singletons[interface] = implementation

    def register_transient(self, interface: type, implementation_factory):
        self._services[interface] = implementation_factory

    def get(self, interface: type):
        if interface in self._singletons:
            return self._singletons[interface]

        if interface in self._services:
            return self._services[interface]()

        raise ValueError(f"Service {interface} not registered")


@lru_cache()
def get_container() -> DIContainer:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"📦 Iniciando criação do container... — {now}", flush=True)
    container = DIContainer()
    now = datetime.now().strftime("%H:%M:%S")
    print(f"📦 Criando repositories e services... — {now}", flush=True)
    session_repository = InMemorySessionRepository()
    session_service = SessionService(session_repository)
    now = datetime.now().strftime("%H:%M:%S")
    print(f"🤖 Criando chat_agent via LazyAgentFactory... — {now} ", flush=True)
    chat_agent = LazyAgentFactory.create_agent()
    now = datetime.now().strftime("%H:%M:%S")
    print(f"✅ Agente criado com sucesso — {now}", flush=True)

    context_enhancer = QueryContextEnhancer()
    query_processor = QueryProcessorService(chat_agent, context_enhancer)
    now = datetime.now().strftime("%H:%M:%S")
    print(f"⚙️ Query processor criado — {now}", flush=True)

    process_query_use_case = ProcessQueryUseCase(session_service, query_processor)
    session_management_use_case = SessionManagementUseCase(session_service)
    export_session_use_case = ExportSessionUseCase(session_service)

    chat_controller = ChatController(process_query_use_case)
    session_controller = SessionController(session_management_use_case)
    export_controller = ExportController(export_session_use_case)

    container.register_singleton(ISessionService, session_service)
    container.register_singleton(IQueryProcessorService, query_processor)
    container.register_singleton(IProcessQueryUseCase, process_query_use_case)
    container.register_singleton(ISessionManagementUseCase, session_management_use_case)
    container.register_singleton(IExportSessionUseCase, export_session_use_case)
    container.register_singleton(ChatController, chat_controller)
    container.register_singleton(SessionController, session_controller)
    container.register_singleton(ExportController, export_controller)

    return container


def create_configured_app():
    now = datetime.now().strftime("%H:%M:%S")
    print(f"📦 Obtendo container...' — {now}", flush=True)
    container = get_container()

    now = datetime.now().strftime("%H:%M:%S")
    print(f"📦 Obtendo controllers... — {now}", flush=True)
    chat_controller = container.get(ChatController)
    session_controller = container.get(SessionController)
    export_controller = container.get(ExportController)

    now = datetime.now().strftime("%H:%M:%S")
    print(f"🗃️ Criando FastAPI app... — {now}", flush=True)
    app = create_app(chat_controller, session_controller, export_controller)

    print(f"✅ Aplicação criada com sucesso — {now}", flush=True)
    if CONTAINER_VERBOSE:
        now = datetime.now().strftime("%H:%M:%S")
        print(f"ℹ️ Controllers e serviços registrados no container — {now}", flush=True)

    return app
