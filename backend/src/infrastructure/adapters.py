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

def _create_pdf_generation_tool(engine):
    def generate_data_pdf(sql_query: str, title: str = "Relatorio de Dados") -> str:
        try:
            print(f"📄 Gerando PDF com query: {sql_query[:100]}...")
            from sqlalchemy import text
            
            with engine.connect() as conn:
                result = conn.execute(text(sql_query))
                rows = result.fetchall()
                columns = result.keys()
                data = [dict(zip(columns, row)) for row in rows]
            
            print(f"📊 Dados obtidos: {len(data)} registros")
            
            from .exporters.data_pdf_exporter import DataPdfExporter
            filepath = DataPdfExporter.export_query_data(data, title)
            print(f"✅ PDF criado: {filepath}")
            
            download_url = f"http://127.0.0.1:8000/{filepath.replace(chr(92), '/')}"
            filename = filepath.split('\\')[-1].split('/')[-1]
            
            return f"✅ PDF gerado com sucesso! {len(data)} registros processados.\n\n📥 [Clique aqui para baixar o arquivo]({download_url})"
        except Exception as e:
            error_msg = f"Erro ao gerar PDF: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg
    
    return FunctionTool.from_defaults(
        fn=generate_data_pdf,
        name="generate_pdf_tool",
        description=(
            "Gera um arquivo PDF com dados de uma consulta SQL. "
            "Use quando o usuário pedir para gerar/criar um PDF, Excel ou CSV com dados. "
            "Primeiro use sql_query_tool para ver os dados, depois use esta ferramenta para gerar o arquivo."
        )
    )


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
                return result
            except Exception as e:
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
        db = SQLDatabase(engine, include_tables=None, sample_rows_in_table_info=2)
        
        model_name = "gemini-2.5-flash-lite"
        
        llm = GoogleGenAI(
            model=model_name,
            api_key=self._config['google_api_key'],
            temperature=0.2,
            max_tokens=2048,
            top_p=0.95
        )
        
        embed_model = GoogleGenAIEmbedding(
            model_name="models/embedding-001",
            api_key=self._config['google_api_key'],
            embed_batch_size=10
        )
        
        Settings.llm = llm
        Settings.embed_model = embed_model
        Settings.chunk_size = 512
        Settings.chunk_overlap = 100

        sql_query_engine = NLSQLTableQueryEngine(
            sql_database=db,
            llm=llm,
            embed_model=embed_model,
            synthesize_response=True,
            streaming=False,
            return_raw=False
        )
        
        sql_query_tool = QueryEngineTool.from_defaults(
            query_engine=sql_query_engine,
            name="sql_query_tool",
            description=(
                "FERRAMENTA OBRIGATÓRIA para QUALQUER pergunta sobre dados de pessoas. "
                "Executa consultas SQL T-SQL no banco de dados SQL Server. "
                "USE SEMPRE que o usuário perguntar sobre pessoas, dados, informações do banco. "
                "Retorna o resultado da consulta formatado."
            )
        )
        
        pdf_tool = _create_pdf_generation_tool(engine)
        
        tools = [sql_query_tool, pdf_tool]

        memory = ChatMemoryBuffer.from_defaults(token_limit=1500, tokenizer_fn=Settings.tokenizer)
        
        system_prompt = """Assistente SQL Server. Use sql_query_tool para consultar. Sintaxe T-SQL: TOP N.
Contexto: "dessas/desses" = dados anteriores.

Para gerar PDF com dados:
1. Use sql_query_tool para buscar
2. Use generate_pdf_tool com a query SQL
3. Retorne o link de download"""
        
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
            if hasattr(response, 'response'):
                chat_message = response.response
                
                if hasattr(chat_message, 'blocks'):
                    blocks = chat_message.blocks
                    if blocks:
                        text_parts = []
                        for block in blocks:
                            try:
                                block_type = type(block).__name__
                                if block_type == 'ThinkingBlock':
                                    continue
                                if hasattr(block, 'text'):
                                    text_parts.append(str(block.text))
                                elif hasattr(block, 'content'):
                                    text_parts.append(str(block.content))
                            except Exception:
                                continue
                        
                        if text_parts:
                            return ' '.join(text_parts)
                
                if hasattr(chat_message, 'content'):
                    try:
                        content = chat_message.content
                        if content:
                            return str(content)
                    except Exception:
                        pass
            
            elif hasattr(response, 'result') and callable(response.result):
                return str(response.result())
            elif hasattr(response, 'result'):
                return str(response.result)
            
            return str(response)
            
        except Exception as e:
            print(f"⚠️ Erro ao extrair texto: {e}")
            return "Desculpe, houve um erro ao processar a resposta."


class QueryProcessorService(IQueryProcessorService):
    def __init__(self, chat_agent: IChatAgent, context_enhancer: IQueryContextEnhancer):
        self._chat_agent = chat_agent
        self._context_enhancer = context_enhancer

    async def process_query(self, query: str, session: Session) -> str:
        print(f"\n🟢 QUERY PROCESSOR: Iniciando processamento...")
        
        enhanced_query = self._context_enhancer.enhance_query(query, session)
        
        print(f"🟢 QUERY PROCESSOR: Chamando chat_agent.process_query...")
        
        try:
            response = self._chat_agent.process_query(enhanced_query)
            
            print(f"🟢 QUERY PROCESSOR: Resposta recebida do agent")
            print(f"   Resposta: {response[:100]}...")
            
        except Exception as e:
            print(f"\n❌ QUERY PROCESSOR: Erro ao chamar agent")
            print(f"   Erro: {str(e)}")
            raise
        
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
        db = SQLDatabase(engine, include_tables=None, sample_rows_in_table_info=2)
        
        model_name = "gemini-2.5-flash-lite"
        
        llm = GoogleGenAI(
            model=model_name,
            api_key=google_api_key,
            temperature=0.2,
            max_tokens=2048,
            top_p=0.95
        )
        
        embed_model = GoogleGenAIEmbedding(
            model_name="models/embedding-001",
            api_key=google_api_key,
            embed_batch_size=10
        )
        
        Settings.llm = llm
        Settings.embed_model = embed_model
        Settings.chunk_size = 512
        Settings.chunk_overlap = 100

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
                    "FERRAMENTA OBRIGATÓRIA para QUALQUER pergunta sobre dados de pessoas. "
                    "Executa consultas SQL T-SQL no banco de dados SQL Server. "
                    "USE SEMPRE que o usuário perguntar sobre pessoas, dados, informações do banco. "
                    "Retorna o resultado da consulta formatado."
                )
            ),
            _create_pdf_generation_tool(engine)
        ]

        memory = ChatMemoryBuffer.from_defaults(token_limit=1500, tokenizer_fn=Settings.tokenizer)
        
        system_prompt = """Assistente SQL Server. Use sql_query_tool para consultar. Sintaxe T-SQL: TOP N.
Contexto: "dessas/desses" = dados anteriores.

Para gerar PDF com dados:
1. Use sql_query_tool para buscar
2. Use generate_pdf_tool com a query SQL
3. Retorne o link de download"""
        
        react_agent = ReActAgent(
            tools=tools,
            llm=llm,
            memory=memory,
            verbose=False,
            system_prompt=system_prompt,
            max_iterations=10
        )
        
        return LlamaIndexChatAgent(react_agent)