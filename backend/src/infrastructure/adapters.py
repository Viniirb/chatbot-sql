import os
import asyncio
import concurrent.futures
from datetime import datetime
from typing import Optional

from llama_index.core import Settings, SQLDatabase
from llama_index.llms.google_genai import GoogleGenAI  
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.core.tools import QueryEngineTool, FunctionTool
from llama_index.core.agent import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer
from sqlalchemy import create_engine

from ..domain.entities import Session, QueryResult, QueryType, IChatAgent, IQueryContextEnhancer
from ..application.interfaces import IQueryProcessorService


class QueryContextEnhancer(IQueryContextEnhancer):
    CONTEXTUAL_KEYWORDS = [
        "dessas", "desses", "desta", "deste", "disso", "deles", "delas",
        "anterior", "últimos", "últimas", "mesmo", "mesma", "mesmos", "mesmas",
        "esses", "essas", "aqueles", "aquelas", "os dados", "as informações",
        "resultado", "resultados", "consulta anterior", "query anterior"
    ]

    def needs_context(self, query: str) -> bool:
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.CONTEXTUAL_KEYWORDS)

    def enhance_query(self, query: str, session: Session) -> str:
        if not self.needs_context(query) or not session.active_dataset:
            return query

        context_summary = session.get_context_summary()
        
        return f"""
CONTEXTO DA CONVERSA:
{context_summary}

ÚLTIMA CONSULTA EXECUTADA:
{session.active_dataset.query}

PERGUNTA ATUAL DO USUÁRIO:
{query}

INSTRUÇÕES ESPECIAIS:
- Use os dados da consulta anterior como base para responder a pergunta atual
- Se o usuário se refere a "dessas", "desses", etc., ele está falando dos dados da última consulta
- Considere o contexto completo da conversa ao formular a resposta SQL
- Se possível, reutilize ou adapte a consulta anterior em vez de criar uma nova do zero
"""


class LlamaIndexChatAgent(IChatAgent):
    def __init__(self, agent_factory_config: dict):
        self._config = agent_factory_config

    def process_query(self, query: str) -> str:
        import warnings
        warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited")
        warnings.filterwarnings("ignore", message=".*Task.*was destroyed but it is pending")
        
        def run_sync():
            print(f"[DEBUG] Executando query: {query[:100]}...")
            
            import asyncio
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def execute():
                agent = self._create_agent_in_loop()
                handler = agent.run(query)
                result = await handler
                return result
            
            try:
                result = loop.run_until_complete(execute())
                print(f"[DEBUG] Resultado tipo: {type(result)}")
                return result
            except Exception as e:
                print(f"[DEBUG] Erro durante execução: {e}")
                raise
            finally:
                try:
                    pending = asyncio.all_tasks(loop)
                    if pending:
                        for task in pending:
                            task.cancel()
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_sync)
            response = future.result(timeout=120)
        
        text = self._extract_response_text(response)
        return self._clean_response(text)
    
    def _create_agent_in_loop(self) -> ReActAgent:
        from llama_index.core import Settings, SQLDatabase
        from llama_index.llms.google_genai import GoogleGenAI
        from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
        from llama_index.core.query_engine import NLSQLTableQueryEngine
        from llama_index.core.tools import QueryEngineTool
        from llama_index.core.agent import ReActAgent
        from llama_index.core.memory import ChatMemoryBuffer
        from sqlalchemy import create_engine
        
        engine = create_engine(
            self._config['db_uri'],
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
        db = SQLDatabase(engine, include_tables=None, sample_rows_in_table_info=3)
        
        llm = GoogleGenAI(
            model_name="models/gemini-2.5-flash",
            api_key=self._config['google_api_key'],
            temperature=0.1,
            max_tokens=4096,
            top_p=0.95
        )
        
        embed_model = GoogleGenAIEmbedding(
            model_name="models/embedding-001",
            api_key=self._config['google_api_key'],
            embed_batch_size=10
        )
        
        Settings.llm = llm
        Settings.embed_model = embed_model
        Settings.chunk_size = 1024
        Settings.chunk_overlap = 200

        sql_query_engine = NLSQLTableQueryEngine(
            sql_database=db,
            llm=llm,
            embed_model=embed_model,
            synthesize_response=True,
            streaming=False,
            return_raw=False
        )
        
        tools = [
            QueryEngineTool.from_defaults(
                query_engine=sql_query_engine,
                name="sql_query_tool",
                description=(
                    "Converte uma pergunta em linguagem natural para uma consulta SQL T-SQL "
                    "e a executa no banco de dados SQL Server. Retorna o resultado da consulta formatado."
                )
            )
        ]

        memory = ChatMemoryBuffer.from_defaults(token_limit=4000, tokenizer_fn=Settings.tokenizer)
        
        system_prompt = """
Você é um assistente especialista em análise de dados e SQL Server (T-SQL) com MEMÓRIA CONVERSACIONAL.

Responsabilidades:
1. Use sempre a ferramenta `sql_query_tool` para responder perguntas sobre dados
2. Responda sempre em português brasileiro
3. Use sintaxe T-SQL (TOP N, não LIMIT; GETDATE(), não NOW())
4. Considere o contexto de conversas anteriores fornecido no prompt
5. Se o usuário se refere a "dessas", "desses", ele está falando de dados mencionados anteriormente

Seja preciso, contextual e útil!
"""
        
        return ReActAgent(
            tools=tools,
            llm=llm,
            memory=memory,
            verbose=False,
            system_prompt=system_prompt,
            max_iterations=10
        )
    
    def _clean_response(self, text: str) -> str:
        text = text.strip()
        prefixes = ["assistant:", "Assistant:", "assistant :", "Assistant :", "Assistente:", "assistente:"]
        for prefix in prefixes:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()
                break
        return text

    def _extract_response_text(self, response) -> str:
        try:
            print(f"[DEBUG] Tipo de resposta: {type(response)}")
            
            if hasattr(response, 'response') and response.response:
                return str(response.response)
            elif hasattr(response, 'result') and callable(response.result):
                return str(response.result())
            elif hasattr(response, 'result'):
                return str(response.result)
            else:
                return str(response)
        except Exception as e:
            print(f"[DEBUG] Erro ao extrair: {e}")
            return f"Erro ao extrair resposta: {str(e)}"


class QueryProcessorService(IQueryProcessorService):
    def __init__(self, chat_agent: IChatAgent, context_enhancer: IQueryContextEnhancer):
        self._chat_agent = chat_agent
        self._context_enhancer = context_enhancer

    async def process_query(self, query: str, session: Session) -> str:
        enhanced_query = self._context_enhancer.enhance_query(query, session)
        
        response = self._chat_agent.process_query(enhanced_query)
        
        if "SELECT" in query.upper():
            await self._try_capture_query_result(query, session)
        
        return response

    async def _try_capture_query_result(self, user_query: str, session: Session) -> None:
        try:
            import re
            from sqlalchemy import text
            
            sql_pattern = r'SELECT\s+.*?(?=\s*$|\s*;|\s*\)|\s+UNION|\s+ORDER\s+BY|\s+GROUP\s+BY|\s+HAVING|\s+LIMIT|\s+OFFSET)'
            sql_match = re.search(sql_pattern, user_query, re.IGNORECASE | re.DOTALL)
            
            if sql_match:
                sql_query = sql_match.group(0).strip()
                
                query_result = QueryResult(
                    query=sql_query,
                    result_data=f"Query executada com sucesso",
                    timestamp=datetime.now(),
                    row_count=0,
                    columns=[],
                    query_type=QueryType.SELECT
                )
                
                session.add_query_result(query_result)
        except Exception:
            pass


class LlamaIndexAgentFactory:
    @staticmethod
    def create_agent() -> IChatAgent:
        db_uri = os.getenv("DATABASE_URL")
        google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        if not db_uri or not google_api_key:
            raise ValueError("Missing required environment variables")

        engine = create_engine(db_uri, pool_pre_ping=True, pool_recycle=3600, echo=False)
        db = SQLDatabase(engine, include_tables=None, sample_rows_in_table_info=3)
        
        llm = GoogleGenAI(
            model_name="models/gemini-2.5-flash",
            api_key=google_api_key,
            temperature=0.1,
            max_tokens=4096,
            top_p=0.95
        )
        
        embed_model = GoogleGenAIEmbedding(
            model_name="models/embedding-001",
            api_key=google_api_key,
            embed_batch_size=10
        )
        
        Settings.llm = llm
        Settings.embed_model = embed_model
        Settings.chunk_size = 1024
        Settings.chunk_overlap = 200

        sql_query_engine = NLSQLTableQueryEngine(
            sql_database=db,
            llm=llm,
            embed_model=embed_model,
            synthesize_response=True,
            streaming=False,
            return_raw=False
        )
        
        tools = [
            QueryEngineTool.from_defaults(
                query_engine=sql_query_engine,
                name="sql_query_tool",
                description=(
                    "Converte uma pergunta em linguagem natural para uma consulta SQL T-SQL "
                    "e a executa no banco de dados SQL Server. Retorna o resultado da consulta formatado."
                )
            )
        ]

        memory = ChatMemoryBuffer.from_defaults(token_limit=4000, tokenizer_fn=Settings.tokenizer)
        
        system_prompt = """
Você é um assistente especialista em análise de dados e SQL Server (T-SQL) com MEMÓRIA CONVERSACIONAL.

Responsabilidades:
1. Use sempre a ferramenta `sql_query_tool` para responder perguntas sobre dados
2. Responda sempre em português brasileiro
3. Use sintaxe T-SQL (TOP N, não LIMIT; GETDATE(), não NOW())
4. Considere o contexto de conversas anteriores fornecido no prompt
5. Se o usuário se refere a "dessas", "desses", ele está falando de dados mencionados anteriormente

Seja preciso, contextual e útil!
"""
        
        react_agent = ReActAgent(
            tools=tools,
            llm=llm,
            memory=memory,
            verbose=False,
            system_prompt=system_prompt,
            max_iterations=10
        )
        
        return LlamaIndexChatAgent(react_agent)