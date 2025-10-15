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
import logging

TOOL_EMOJI = os.getenv("TOOL_EMOJI", "1").lower() not in ("0", "false", "no")
logger = logging.getLogger(__name__)


class LazyLlamaIndexChatAgent(IChatAgent):
    def __init__(self, config: Dict[str, str]):
    self._config = config

    def process_query(self, query: str, context_messages=None) -> str:
        import warnings
        warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited")
        warnings.filterwarnings("ignore", message=".*Task.*was destroyed but it is pending")

        
        if context_messages and isinstance(context_messages, list):
            context_messages = context_messages[-8:]  # pega as 8 últimas mensagens
            context_str = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in context_messages if 'role' in msg and 'content' in msg
            ])
            query = f"{context_str}\n{query}"

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
                logger.warning("Nenhuma resposta gerada pelo agente para a query")
                return "Desculpe, não consegui processar a resposta adequadamente. Por favor, tente reformular sua pergunta."

            text = self._extract_response_text(response)
            return self._clean_response(text)

        except Exception:
            logger.exception("Erro ao processar a query no LazyLlamaIndexChatAgent")
            raise

    async def process_query_async(self, query: str) -> str:
        """Async wrapper for synchronous process_query for compatibility.
        Uses asyncio.to_thread so callers can await without blocking the loop.
        """
        return await asyncio.to_thread(self.process_query, query)
    
    def _create_agent_in_loop(self) -> ReActAgent:
        engine = create_engine(
            self._config['db_uri'],
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
        db = SQLDatabase(engine, include_tables=None, sample_rows_in_table_info=2)
        
        model_name = "gemini-2.5-flash-lite"
        
        # Respect environment override for max tokens, otherwise choose a safer default
        default_max_tokens = int(os.getenv('AGENT_MAX_TOKENS', '2048'))
        llm = GoogleGenAI(
            model=model_name,
            api_key=self._config['google_api_key'],
            temperature=0.2,
            max_tokens=default_max_tokens,
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
        
        try:
            from sqlalchemy import event
            from datetime import datetime
            from .execution_context import get_current

            
            try:
                sess, reqid = get_current()
                if reqid:
                    engine.info['request_id'] = reqid
                    if sess and hasattr(sess, 'session_id'):
                        engine.info['session_id'] = getattr(sess.session_id, 'value', None)
            except Exception:
                pass

            def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                try:
                    if not statement or 'SELECT' not in statement.upper():
                        return
                    session_obj, reqid = get_current()
                    if session_obj:
                        try:
                            session_obj.stats.update(session_obj.stats.message_count, session_obj.stats.query_count + 1)
                            session_obj._last_activity = datetime.now()
                            logger.info("Incremented query_count to %d for session %s", getattr(session_obj.session_id, 'value', 'n/a'), session_obj.stats.query_count)
                        except Exception:
                            logger.exception("Erro ao incrementar query_count nas estatísticas da session")
                except Exception:
                    logger.exception("Erro no listener after_cursor_execute")

            event.listen(engine, 'after_cursor_execute', _after_cursor_execute)
        except Exception:
            logger.exception("Erro ao configurar listener de queries para o engine")


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
                prefix = "📄 " if TOOL_EMOJI else ""
                logger.info(f"{prefix}Gerando PDF com query: {sql_query[:100]}...")
                from sqlalchemy import text, inspect, exc
                from datetime import datetime
                with engine.connect() as conn:
                    try:
                        # Cooperative cancellation: abort if request marked as cancelled
                        try:
                            from .execution_context import is_cancelled_current
                            if is_cancelled_current():
                                return "Operação cancelada pelo usuário"
                        except Exception:
                            pass
                        result = conn.execute(text(sql_query))
                    except exc.ProgrammingError as pe:
                        try:
                            inspector = inspect(engine)
                            tables = inspector.get_table_names()
                        except Exception:
                            tables = []
                        logger.warning("SQL ProgrammingError while executing query for PDF: %s", pe)
                        return (
                            "Erro ao executar a consulta SQL: parece que a tabela ou coluna não existe. "
                            f"Detalhe do erro: {pe}. Tabelas disponíveis: {', '.join(tables) if tables else 'desconhecidas'}."
                        )
                    rows = result.fetchall()
                    columns = result.keys()
                    data = [dict(zip(columns, row)) for row in rows]
                # Re-check cancellation after DB op
                try:
                    from .execution_context import is_cancelled_current
                    if is_cancelled_current():
                        return "Operação cancelada pelo usuário"
                except Exception:
                    pass
                logger.info(f"📊 Dados obtidos: {len(data)} registros")
                from src.infrastructure.sql_exporters.data_pdf_exporter import DataPdfExporter
                file_bytes = DataPdfExporter.export(data, title)
                try:
                    from .exporters.exporter_factory import ExporterFactory
                    filename = ExporterFactory.build_filename('documentoPDF', 'pdf')
                except Exception:
                    filename = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                export_dir = "downloads/exports"
                os.makedirs(export_dir, exist_ok=True)
                filepath = os.path.join(export_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(file_bytes)
                filepath_normalized = filepath.replace("\\", "/")
                # Verify file exists before returning a download link
                if not os.path.exists(filepath):
                    logger.warning("Arquivo PDF gerado não encontrado após escrita: %s", filepath)
                    return (
                        "Percebi que tentei gerar o PDF, mas o arquivo não foi encontrado no servidor após a operação. "
                        "Deseja que eu tente gerar o arquivo novamente?"
                    )
                download_url = f"http://127.0.0.1:8000/{filepath_normalized}"
                # Return Markdown link (agent/system expects Markdown links)
                return f"✅ PDF gerado com sucesso! {len(data)} registros processados.\n\n📥 [Clique aqui para baixar o arquivo]({download_url})"
            except Exception as e:
                error_msg = f"Erro ao gerar PDF: {str(e)}"
                logger.exception("Erro ao gerar PDF: %s", e)
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
                prefix = "📄 " if TOOL_EMOJI else ""
                logger.info(f"{prefix}Gerando Excel com query: {sql_query[:100]}...")
                from sqlalchemy import text, inspect, exc
                from datetime import datetime
                with engine.connect() as conn:
                        try:
                            # Cooperative cancellation: abort if request marked as cancelled
                            try:
                                from .execution_context import is_cancelled_current
                                if is_cancelled_current():
                                    return "Operação cancelada pelo usuário"
                            except Exception:
                                pass
                            result = conn.execute(text(sql_query))
                    except exc.ProgrammingError as pe:
                        # Likely invalid table or column name; list available tables for the user
                        try:
                            inspector = inspect(engine)
                            tables = inspector.get_table_names()
                        except Exception:
                            tables = []
                        logger.warning("SQL ProgrammingError while executing query: %s", pe)
                        return (
                            "Erro ao executar a consulta SQL: parece que a tabela ou coluna não existe. "
                            f"Detalhe do erro: {pe}. Tabelas disponíveis: {', '.join(tables) if tables else 'desconhecidas'}."
                        )
                    rows = result.fetchall()
                    columns = result.keys()
                    data = [list(row) for row in rows]
                # Re-check cancellation after DB op
                try:
                    from .execution_context import is_cancelled_current
                    if is_cancelled_current():
                        return "Operação cancelada pelo usuário"
                except Exception:
                    pass
                logger.info(f"📊 Dados obtidos: {len(data)} registros")
                from src.infrastructure.sql_exporters.data_excel_exporter import DataExcelExporter
                file_bytes = DataExcelExporter.export(data, list(columns))
                try:
                    from .exporters.exporter_factory import ExporterFactory
                    filename = ExporterFactory.build_filename('documentoExcel', 'xlsx')
                except Exception:
                    filename = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                export_dir = "downloads/exports"
                os.makedirs(export_dir, exist_ok=True)
                filepath = os.path.join(export_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(file_bytes)
                filepath_normalized = filepath.replace("\\", "/")
                # Verify file exists before returning a download link
                if not os.path.exists(filepath):
                    logger.warning("Arquivo Excel gerado não encontrado após escrita: %s", filepath)
                    return (
                        "Percebi que tentei gerar o Excel, mas o arquivo não foi encontrado no servidor após a operação. "
                        "Deseja que eu tente gerar o arquivo novamente?"
                    )
                download_url = f"http://127.0.0.1:8000/{filepath_normalized}"
                # Return Markdown link (agent/system expects Markdown links)
                return f"✅ Excel gerado com sucesso! {len(data)} registros processados.\n\n📥 [Clique aqui para baixar o arquivo]({download_url})"
            except Exception as e:
                error_msg = f"Erro ao gerar Excel: {str(e)}"
                logger.exception("Erro ao gerar Excel: %s", e)
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
                prefix = "📄 " if TOOL_EMOJI else ""
                logger.info(f"{prefix}Gerando CSV com query: {sql_query[:100]}...")
                from sqlalchemy import text, inspect, exc
                from datetime import datetime
                with engine.connect() as conn:
                    try:
                        result = conn.execute(text(sql_query))
                    except exc.ProgrammingError as pe:
                        try:
                            inspector = inspect(engine)
                            tables = inspector.get_table_names()
                        except Exception:
                            tables = []
                        logger.warning("SQL ProgrammingError while executing query for CSV: %s", pe)
                        return (
                            "Erro ao executar a consulta SQL: parece que a tabela ou coluna não existe. "
                            f"Detalhe do erro: {pe}. Tabelas disponíveis: {', '.join(tables) if tables else 'desconhecidas'}."
                        )
                    rows = result.fetchall()
                    columns = result.keys()
                    data = [list(row) for row in rows]
                logger.info(f"📊 Dados obtidos: {len(data)} registros")
                from src.infrastructure.sql_exporters.data_csv_exporter import DataCsvExporter
                file_bytes = DataCsvExporter.export(data, list(columns))
                try:
                    from .exporters.exporter_factory import ExporterFactory
                    filename = ExporterFactory.build_filename('documentoCSV', 'csv')
                except Exception:
                    filename = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                export_dir = "downloads/exports"
                os.makedirs(export_dir, exist_ok=True)
                filepath = os.path.join(export_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(file_bytes)
                filepath_normalized = filepath.replace("\\", "/")
                # Verify file exists before returning a download link
                if not os.path.exists(filepath):
                    logger.warning("Arquivo CSV gerado não encontrado após escrita: %s", filepath)
                    return (
                        "Percebi que tentei gerar o CSV, mas o arquivo não foi encontrado no servidor após a operação. "
                        "Deseja que eu tente gerar o arquivo novamente?"
                    )
                download_url = f"http://127.0.0.1:8000/{filepath_normalized}"
                # Return Markdown link (agent/system expects Markdown links)
                return f"✅ CSV gerado com sucesso! {len(data)} registros processados.\n\n📥 [Clique aqui para baixar o arquivo]({download_url})"
            except Exception as e:
                error_msg = f"Erro ao gerar CSV: {str(e)}"
                logger.exception("Erro ao gerar CSV: %s", e)
                return error_msg

        pdf_tool = FunctionTool.from_defaults(
            fn=generate_data_pdf,
            name="generate_pdf_tool",
            description=(
                "Gera um arquivo PDF com dados de uma consulta SQL. "
                "Só use esta ferramenta se o usuário pedir explicitamente para exportar ou baixar os dados em PDF. "
                "Sempre gere um novo arquivo quando solicitado pelo usuário, mesmo que já exista um arquivo semelhante gerado anteriormente. "
                "Nunca gere documentos sem solicitação clara do usuário."
            )
        )

        excel_tool = FunctionTool.from_defaults(
            fn=generate_data_excel,
            name="generate_excel_tool",
            description=(
                "Gera um arquivo Excel com dados de uma consulta SQL. "
                "Só use esta ferramenta se o usuário pedir explicitamente para exportar ou baixar os dados em Excel. "
                "Sempre gere um novo arquivo quando solicitado pelo usuário, mesmo que já exista um arquivo semelhante gerado anteriormente. "
                "Nunca gere documentos sem solicitação clara do usuário."
            )
        )

        csv_tool = FunctionTool.from_defaults(
            fn=generate_data_csv,
            name="generate_csv_tool",
            description=(
                "Gera um arquivo CSV com dados de uma consulta SQL. "
                "Só use esta ferramenta se o usuário pedir explicitamente para exportar ou baixar os dados em CSV. "
                "Sempre gere um novo arquivo quando solicitado pelo usuário, mesmo que já exista um arquivo semelhante gerado anteriormente. "
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

        # Validate SQL tool: the agent should call this before executing any
        # SQL to ensure referenced tables/columns exist.
        def validate_sql(sql_text: str) -> str:
            try:
                from sqlalchemy import inspect
                inspector = inspect(engine)
                available_tables = inspector.get_table_names()
                import re
                found = set()
                for m in re.finditer(r"\bFROM\s+([a-zA-Z0-9_\.\[\]\`\"]+)|\bJOIN\s+([a-zA-Z0-9_\.\[\]\`\"]+)", sql_text, re.IGNORECASE):
                    g1 = m.group(1) or m.group(2)
                    if g1:
                        # strip quotes/brackets
                        tbl = g1.strip('`"[]')
                        if '.' in tbl:
                            tbl = tbl.split('.')[-1]
                        found.add(tbl)
                missing = [t for t in found if t not in available_tables]
                if missing:
                    return f"INVALID: tabelas não encontradas: {', '.join(missing)}. Tabelas disponíveis: {', '.join(available_tables)}"
                return "OK"
            except Exception as e:
                return f"ERROR validating SQL: {e}"

        validate_tool = FunctionTool.from_defaults(
            fn=validate_sql,
            name="validate_sql_tool",
            description=(
                "Valida se as tabelas referenciadas em uma consulta SQL existem no banco. "
                "Retorna 'OK' ou 'INVALID: ...' com sugestão. Use antes de executar SQL."
            )
        )

    tools = [sql_query_tool, pdf_tool, excel_tool, csv_tool, schema_tool, validate_tool]

        memory = ChatMemoryBuffer.from_defaults(token_limit=1500, tokenizer_fn=Settings.tokenizer)
        
        # Build a concise schema summary and add to the system prompt so the
        # model can use exact table/column names when producing SQL.
        schema_summary = ""
        try:
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            parts = []
            for t in tables[:20]:
                try:
                    cols = [c['name'] for c in inspector.get_columns(t)][:6]
                    parts.append(f"{t}({', '.join(cols)}{'...' if len(cols) > 6 else ''})")
                except Exception:
                    parts.append(t)
            schema_summary = "\n".join(parts)
        except Exception:
            schema_summary = "(não foi possível ler o esquema do banco)"

        system_prompt = """
Sempre que o usuário pedir dados, priorize mostrar os resultados em texto/tabela. Só gere arquivos (PDF, Excel, CSV) se o usuário pedir explicitamente para exportar ou baixar. Nunca gere documentos sem solicitação clara. Se for gerar arquivo, responda apenas com o link de download em Markdown e uma frase breve.
Exemplo: 📥 [Clique aqui para baixar o arquivo](URL)
"""

# Enforce strict tool usage and filename format to avoid hallucinated links
        system_prompt += (
            "\n\nRegras IMPORTANTES:\n"
            "- Sempre que precisar gerar um arquivo (PDF/Excel/CSV), chame a ferramenta correspondente (generate_pdf_tool, generate_excel_tool, generate_csv_tool).\n"
            "- NUNCA invente ou retorne um link manualmente. Retorne APENAS o link que a ferramenta gerar.\n"
            "- Os links válidos devem apontar para http://127.0.0.1:8000/downloads/exports/<filename> onde <filename> segue o padrão:\n"
            "  documentoPDF_YYYYMMDD_HHMMSS_<SHORTID>.pdf\n"
            "  documentoExcel_YYYYMMDD_HHMMSS_<SHORTID>.xlsx\n"
            "  documentoCSV_YYYYMMDD_HHMMSS_<SHORTID>.csv\n"
            "- Se a ferramenta não tiver sido executada ou o arquivo não existir, pergunte ao usuário se deseja que você gere o arquivo agora."
        )

        # Encourage the agent to validate SQL before executing it and provide
        # the schema summary for exact names.
        system_prompt += (
            "\n\nIMPORTANTE: Antes de executar QUALQUER SQL gerado, chame a ferramenta 'validate_sql_tool'\n"
            "com a consulta SQL exata. Se a ferramenta retornar 'OK', execute a consulta. "
            "Se retornar 'INVALID', reescreva a consulta usando as tabelas válidas listadas abaixo.\n\n"
            "Esquema do banco (tabelas e colunas):\n" + schema_summary + "\n"
        )

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
                            logger.debug(f"Texto extraído dos blocos: {result_text}")
                            # Se o texto contém uma URL mas não está em Markdown, converte para hyperlink
                            import re
                            url_match = re.search(r'(https?://\S+)', result_text)
                            markdown_match = re.search(r'\[.*?\]\(https?://.*?\)', result_text)
                            if url_match and not markdown_match:
                                url = url_match.group(1)
                                # Before returning a download link, verify the file exists
                                try:
                                    from urllib.parse import urlparse, unquote
                                    p = urlparse(url)
                                    # Only validate local server links
                                    if p.hostname in (None, '127.0.0.1', 'localhost'):
                                        local_path = unquote(p.path.lstrip('/'))
                                        abs_path = os.path.join(os.getcwd(), local_path)
                                        if not os.path.exists(abs_path):
                                            logger.warning("Link mencionado pelo agente não encontrado: %s -> %s", url, abs_path)
                                            return (
                                                "Percebi que a resposta menciona um arquivo para download, "
                                                "mas o arquivo não foi encontrado no servidor. Quer que eu gere o arquivo agora?"
                                            )
                                except Exception:
                                    # If validation fails for any reason, fall back to returning the URL
                                    logger.debug("Falha ao validar URL de download: %s", url)

                                # Adiciona texto padrão para download
                                result_text = f"📥 [Clique aqui para baixar o arquivo]({url})"
                            return result_text
                if hasattr(chat_message, 'content'):
                    try:
                        content = chat_message.content
                        if content:
                            logger.debug(f"Conteúdo extraído: {content}")
                            return str(content)
                    except Exception:
                        pass
            elif hasattr(response, 'result') and callable(response.result):
                result = str(response.result())
                logger.debug("Resultado extraído (callable): %s", result)
                return result
            elif hasattr(response, 'result'):
                result = str(response.result)
                logger.debug("Resultado extraído: %s", result)
                return result
            result = str(response)
            logger.debug(f"Resultado extraído (str): {result}")
            return result
        except Exception as e:
            logger.exception("Erro ao extrair texto da resposta do agente")
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

        # return a wrapped agent that exposes an async process_query
        from .adapters import AsyncAgentAdapter
        return AsyncAgentAdapter(LazyLlamaIndexChatAgent(config))
