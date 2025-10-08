import os
import asyncio
import concurrent.futures
from typing import Dict

from llama_index.core import Settings, SQLDatabase
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.core.tools import QueryEngineTool
from llama_index.core.agent import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer
from sqlalchemy import create_engine

from ..domain.entities import IChatAgent


class LazyLlamaIndexChatAgent(IChatAgent):
    def __init__(self, config: Dict[str, str]):
        self._config = config

    def process_query(self, query: str) -> str:
        import warnings
        warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited")
        warnings.filterwarnings("ignore", message=".*Task.*was destroyed but it is pending")
        
        def run_sync():
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
Você é um assistente especialista em análise de dados e SQL Server (T-SQL).

INSTRUÇÕES IMPORTANTES:
- Você TEM acesso total ao banco de dados via ferramenta sql_query_tool
- SEMPRE use a ferramenta sql_query_tool para responder perguntas sobre dados
- NUNCA diga que não tem acesso ou permissão - você tem acesso completo
- Responda em português brasileiro
- Use sintaxe T-SQL (TOP N ao invés de LIMIT; GETDATE() ao invés de NOW())

EXEMPLOS:
Pergunta: "Quais pessoas existem?"
Ação: Use sql_query_tool com "SELECT * FROM pessoas"

Pergunta: "Quantas pessoas temos?"
Ação: Use sql_query_tool com "SELECT COUNT(*) as total FROM pessoas"
"""
        
        return ReActAgent(
            tools=tools,
            llm=llm,
            memory=memory,
            verbose=True,
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
            if hasattr(response, 'response') and response.response:
                return str(response.response)
            elif hasattr(response, 'result') and callable(response.result):
                return str(response.result())
            elif hasattr(response, 'result'):
                return str(response.result)
            else:
                return str(response)
        except Exception:
            return "Erro ao processar resposta"


class LazyAgentFactory:
    @staticmethod
    def create_agent() -> IChatAgent:
        db_uri = os.getenv("DATABASE_URL")
        google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        if not db_uri or not google_api_key:
            raise ValueError("Missing required environment variables")
        
        config = {
            'db_uri': db_uri,
            'google_api_key': google_api_key
        }
        
        return LazyLlamaIndexChatAgent(config)
