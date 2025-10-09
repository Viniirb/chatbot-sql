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
                result = await agent.run(query)
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
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_sync)
                response = future.result(timeout=120)
            
            if response is None:
                return "Desculpe, não consegui processar a resposta adequadamente. Por favor, tente reformular sua pergunta."
            
            text = self._extract_response_text(response)
            return self._clean_response(text)
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            raise
    
    def _create_agent_in_loop(self) -> ReActAgent:
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
            max_tokens=65536,  # Limite máximo do Gemini 2.5 Flash-Lite
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
        
        from llama_index.core.tools import FunctionTool

        sql_query_tool = QueryEngineTool.from_defaults(
            query_engine=sql_query_engine,
            name="sql_query_tool",
            description=(
                "Ferramenta para mostrar dados do banco em texto/tabela. "
                "Use para responder perguntas sobre pessoas, dados, informações do banco. "
                "Só gere documentos (PDF, Excel, CSV) se o usuário pedir explicitamente. "
                "Priorize mostrar os dados diretamente quando o pedido for genérico."
            )
        )


        def generate_data_pdf(sql_query: str, title: str = "Relatorio de Dados") -> str:
            """
            Gera um PDF com dados de uma consulta SQL.
            Args:
                sql_query: Query SQL T-SQL para buscar dados (ex: "SELECT TOP 2 * FROM DIM_PESSOAS")
                title: Título do relatório PDF
            Returns:
                Link para download do PDF gerado
            """
            try:
                print(f"📄 Gerando PDF com query: {sql_query[:100]}...")
                from sqlalchemy import text
                from datetime import datetime
                with engine.connect() as conn:
                    result = conn.execute(text(sql_query))
                    rows = result.fetchall()
                    columns = result.keys()
                    data = [dict(zip(columns, row)) for row in rows]
                print(f"📊 Dados obtidos: {len(data)} registros")
                from src.infrastructure.sql_exporters.data_pdf_exporter import DataPdfExporter
                file_bytes = DataPdfExporter.export(data, title)
                filename = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                export_dir = "downloads/exports"
                os.makedirs(export_dir, exist_ok=True)
                filepath = os.path.join(export_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(file_bytes)
                filepath_normalized = filepath.replace("\\", "/")
                download_url = f"http://127.0.0.1:8000/{filepath_normalized}"
                return f"✅ PDF gerado com sucesso! {len(data)} registros processados.\n\n📥 <a href='{download_url}' download>Clique aqui para baixar o arquivo</a>"
            except Exception as e:
                error_msg = f"Erro ao gerar PDF: {str(e)}"
                print(f"❌ {error_msg}")
                import traceback
                traceback.print_exc()
                return error_msg

        def generate_data_excel(sql_query: str, title: str = "Relatorio de Dados") -> str:
            """
            Gera um Excel com dados de uma consulta SQL.
            Args:
                sql_query: Query SQL T-SQL para buscar dados
                title: Título do relatório Excel
            Returns:
                Link para download do Excel gerado
            """
            try:
                print(f"📄 Gerando Excel com query: {sql_query[:100]}...")
                from sqlalchemy import text
                from datetime import datetime
                with engine.connect() as conn:
                    result = conn.execute(text(sql_query))
                    rows = result.fetchall()
                    columns = result.keys()
                    data = [list(row) for row in rows]
                print(f"📊 Dados obtidos: {len(data)} registros")
                from src.infrastructure.sql_exporters.data_excel_exporter import DataExcelExporter
                file_bytes = DataExcelExporter.export(data, list(columns))
                filename = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                export_dir = "downloads/exports"
                os.makedirs(export_dir, exist_ok=True)
                filepath = os.path.join(export_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(file_bytes)
                filepath_normalized = filepath.replace("\\", "/")
                download_url = f"http://127.0.0.1:8000/{filepath_normalized}"
                return f"✅ Excel gerado com sucesso! {len(data)} registros processados.\n\n📥 <a href='{download_url}' download>Clique aqui para baixar o arquivo</a>"
            except Exception as e:
                error_msg = f"Erro ao gerar Excel: {str(e)}"
                print(f"❌ {error_msg}")
                import traceback
                traceback.print_exc()
                return error_msg

        def generate_data_csv(sql_query: str, title: str = "Relatorio de Dados") -> str:
            """
            Gera um CSV com dados de uma consulta SQL.
            Args:
                sql_query: Query SQL T-SQL para buscar dados
                title: Título do relatório CSV
            Returns:
                Link para download do CSV gerado
            """
            try:
                print(f"📄 Gerando CSV com query: {sql_query[:100]}...")
                from sqlalchemy import text
                from datetime import datetime
                with engine.connect() as conn:
                    result = conn.execute(text(sql_query))
                    rows = result.fetchall()
                    columns = result.keys()
                    data = [list(row) for row in rows]
                print(f"📊 Dados obtidos: {len(data)} registros")
                from src.infrastructure.sql_exporters.data_csv_exporter import DataCsvExporter
                file_bytes = DataCsvExporter.export(data, list(columns))
                filename = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                export_dir = "downloads/exports"
                os.makedirs(export_dir, exist_ok=True)
                filepath = os.path.join(export_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(file_bytes)
                filepath_normalized = filepath.replace("\\", "/")
                download_url = f"http://127.0.0.1:8000/{filepath_normalized}"
                return f"✅ CSV gerado com sucesso! {len(data)} registros processados.\n\n📥 <a href='{download_url}' download>Clique aqui para baixar o arquivo</a>"
            except Exception as e:
                error_msg = f"Erro ao gerar CSV: {str(e)}"
                print(f"❌ {error_msg}")
                import traceback
                traceback.print_exc()
                return error_msg

        pdf_tool = FunctionTool.from_defaults(
            fn=generate_data_pdf,
            name="generate_pdf_tool",
            description=(
                "Gera um arquivo PDF com dados de uma consulta SQL. "
                "Só use esta ferramenta se o usuário pedir explicitamente para exportar ou baixar os dados em PDF. "
                "Nunca gere documentos sem solicitação clara do usuário."
            )
        )

        excel_tool = FunctionTool.from_defaults(
            fn=generate_data_excel,
            name="generate_excel_tool",
            description=(
                "Gera um arquivo Excel com dados de uma consulta SQL. "
                "Só use esta ferramenta se o usuário pedir explicitamente para exportar ou baixar os dados em Excel. "
                "Nunca gere documentos sem solicitação clara do usuário."
            )
        )

        csv_tool = FunctionTool.from_defaults(
            fn=generate_data_csv,
            name="generate_csv_tool",
            description=(
                "Gera um arquivo CSV com dados de uma consulta SQL. "
                "Só use esta ferramenta se o usuário pedir explicitamente para exportar ou baixar os dados em CSV. "
                "Nunca gere documentos sem solicitação clara do usuário."
            )
        )

        def get_db_schema_info() -> str:
            """
            Retorna informações sobre tabelas, colunas e tipos do banco de dados.
            """
            from sqlalchemy import inspect
            inspector = inspect(engine)
            schema_info = []
            for table_name in inspector.get_table_names():
                columns = inspector.get_columns(table_name)
                col_str = ", ".join([f"{col['name']} ({col['type']})" for col in columns])
                schema_info.append(f"Tabela: {table_name}\nColunas: {col_str}")
            return "\n\n".join(schema_info)

        schema_tool = FunctionTool.from_defaults(
            fn=get_db_schema_info,
            name="get_db_schema_info",
            description="Retorna informações sobre tabelas, colunas e tipos do banco de dados. Use para descobrir a estrutura do banco."
        )

        tools = [sql_query_tool, pdf_tool, excel_tool, csv_tool, schema_tool]

        memory = ChatMemoryBuffer.from_defaults(token_limit=1500, tokenizer_fn=Settings.tokenizer)
        
        system_prompt = """
Sempre que o usuário pedir dados, priorize mostrar os resultados em texto/tabela. Só gere arquivos (PDF, Excel, CSV) se o usuário pedir explicitamente para exportar ou baixar. Nunca gere documentos sem solicitação clara. Se for gerar arquivo, responda apenas com o link de download em Markdown e uma frase breve.
Exemplo: 📥 [Clique aqui para baixar o arquivo](URL)
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
                            result_text = ' '.join(text_parts)
                            print(f"[DEBUG] Texto extraído dos blocos: {result_text}")
                            # Se o texto contém uma URL mas não está em Markdown, converte para hyperlink
                            import re
                            url_match = re.search(r'(https?://\S+)', result_text)
                            markdown_match = re.search(r'\[.*?\]\(https?://.*?\)', result_text)
                            if url_match and not markdown_match:
                                url = url_match.group(1)
                                # Adiciona texto padrão para download
                                result_text = f"📥 [Clique aqui para baixar o arquivo]({url})"
                            return result_text
                if hasattr(chat_message, 'content'):
                    try:
                        content = chat_message.content
                        if content:
                            print(f"[DEBUG] Conteúdo extraído: {content}")
                            return str(content)
                    except Exception:
                        pass
            elif hasattr(response, 'result') and callable(response.result):
                result = str(response.result())
                print(f"[DEBUG] Resultado extraído (callable): {result}")
                return result
            elif hasattr(response, 'result'):
                result = str(response.result)
                print(f"[DEBUG] Resultado extraído: {result}")
                return result
            result = str(response)
            print(f"[DEBUG] Resultado extraído (str): {result}")
            return result
        except Exception as e:
            print(f"⚠️ Erro ao extrair texto: {e}")
            return "Desculpe, houve um erro ao processar a resposta."


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
