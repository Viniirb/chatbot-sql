from functools import lru_cache
from typing import Dict, Any

from ..application.interfaces import IProcessQueryUseCase, ISessionManagementUseCase, ISessionService, IQueryProcessorService, IExportSessionUseCase
from ..application.use_cases import ProcessQueryUseCase, SessionManagementUseCase
from ..application.export_use_case import ExportSessionUseCase
from ..infrastructure.services import SessionService, InMemorySessionRepository
from ..infrastructure.adapters import QueryProcessorService, QueryContextEnhancer
from ..infrastructure.lazy_agent import LazyAgentFactory
from ..presentation.controllers import ChatController, SessionController, ExportController, create_app


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
    print("🟨 CONTAINER: Iniciando criação do container...")
    container = DIContainer()
    
    print("🟨 CONTAINER: Criando repositories e services...")
    session_repository = InMemorySessionRepository()
    session_service = SessionService(session_repository)
    
    print("🟨 CONTAINER: Criando chat_agent via LazyAgentFactory...")
    chat_agent = LazyAgentFactory.create_agent()
    print("🟨 CONTAINER: Chat agent criado!")
    
    context_enhancer = QueryContextEnhancer()
    query_processor = QueryProcessorService(chat_agent, context_enhancer)
    print("🟨 CONTAINER: Query processor criado!")
    
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
    print("🟨 CREATE_CONFIGURED_APP: Obtendo container...")
    container = get_container()
    
    print("🟨 CREATE_CONFIGURED_APP: Obtendo controllers...")
    chat_controller = container.get(ChatController)
    session_controller = container.get(SessionController)
    export_controller = container.get(ExportController)
    
    print("🟨 CREATE_CONFIGURED_APP: Criando FastAPI app...")
    app = create_app(chat_controller, session_controller, export_controller)
    
    print("🟨 CREATE_CONFIGURED_APP: App criado com sucesso!")
    return app