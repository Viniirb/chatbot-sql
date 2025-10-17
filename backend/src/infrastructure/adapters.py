import os
import asyncio
from datetime import datetime
from typing import Optional
import logging
import inspect
import time
import uuid
from llama_index.core import Settings, SQLDatabase
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.core.tools import QueryEngineTool, FunctionTool
from llama_index.core.agent import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer
from sqlalchemy import create_engine, text, event, inspect as sqlalchemy_inspect
from ..domain.entities import (
    Session,
    QueryResult,
    QueryType,
    IChatAgent,
    IQueryContextEnhancer,
)
from .execution_context import (
    set_for_context,
    reset_context,
    set_for_thread,
    clear_for_thread,
    get_current,
    is_cancelled_current,
    register_task,
    unregister_task,
)
from ..application.interfaces import IQueryProcessorService

logger = logging.getLogger(__name__)


class AsyncAgentAdapter(IChatAgent):
    def __init__(self, agent: IChatAgent):
        self._agent = agent

    async def process_query(self, query: str) -> str:
        proc = getattr(self._agent, "process_query", None)
        if proc is None:
            raise ValueError("Wrapped agent has no process_query")

        if inspect.iscoroutinefunction(proc):
            return await proc(query)

        def _call_proc_with_thread_context(*args, **kwargs):
            sess, reqid = get_current()
            if sess is not None or reqid is not None:
                set_for_thread(sess, reqid)
            try:
                return proc(*args, **kwargs)
            finally:
                if sess is not None or reqid is not None:
                    clear_for_thread()

        return await asyncio.to_thread(_call_proc_with_thread_context, query)

    def __getattr__(self, name):
        return getattr(self._agent, name)


def _create_pdf_generation_tool(engine):
    def generate_data_pdf(sql_query: str, title: str = "Relatorio de Dados") -> str:
        try:
            try:
                if is_cancelled_current():
                    return "Operação cancelada pelo usuário"
            except Exception:
                pass

            TOOL_EMOJI = os.getenv("TOOL_EMOJI", "0") in ("1", "true", "True")
            log_message = (
                f"📄 Gerando PDF com query: {sql_query[:100]}..."
                if TOOL_EMOJI
                else f"Gerando PDF com query: {sql_query[:100]}..."
            )
            logger.debug(log_message)

            with engine.connect() as conn:
                result = conn.execute(text(sql_query))
                rows = result.fetchall()
                columns = result.keys()
                data = [dict(zip(columns, row)) for row in rows]

            try:
                if is_cancelled_current():
                    return "Operação cancelada pelo usuário"
            except Exception:
                pass

            log_message_data = (
                f"📊 Dados obtidos: {len(data)} registros"
                if TOOL_EMOJI
                else f"Dados obtidos: {len(data)} registros"
            )
            logger.debug(log_message_data)

            from .sql_exporters.data_pdf_exporter import DataPdfExporter

            filepath = DataPdfExporter.export_query_data(data, title)

            log_message_created = (
                f"✅ PDF criado: {filepath}"
                if TOOL_EMOJI
                else f"PDF criado: {filepath}"
            )
            logger.debug(log_message_created)

            if not os.path.exists(filepath):
                logger.warning(
                    "Arquivo PDF gerado não encontrado após export: %s", filepath
                )
                return "Percebi que tentei gerar o PDF, mas o arquivo não foi encontrado no servidor. Deseja que eu tente gerar o arquivo novamente?"

            download_url = f"http://127.0.0.1:8000/{filepath.replace(chr(92), '/')}"
            return f"✅ PDF gerado com sucesso! {len(data)} registros processados.\n\n📥 [Clique aqui para baixar o arquivo]({download_url})"
        except Exception as e:
            error_msg = f"Erro ao gerar PDF: {str(e)}"
            logger.exception(error_msg)
            return error_msg

    return FunctionTool.from_defaults(
        fn=generate_data_pdf,
        name="generate_pdf_tool",
        description="Gera um arquivo PDF com dados de uma consulta SQL. Use quando o usuário pedir para gerar/criar um PDF, Excel ou CSV com dados. Primeiro use sql_query_tool para ver os dados, depois use esta ferramenta para gerar o arquivo.",
    )


class QueryContextEnhancer(IQueryContextEnhancer):
    CONTEXTUAL_KEYWORDS = [
        "dessas",
        "desses",
        "desta",
        "deste",
        "disso",
        "deles",
        "delas",
        "anterior",
        "últimos",
        "últimas",
        "mesmo",
        "mesma",
        "mesmos",
        "mesmas",
        "esses",
        "essas",
        "aqueles",
        "aquelas",
        "os dados",
        "as informações",
        "resultado",
        "resultados",
        "consulta anterior",
        "query anterior",
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

    async def process_query(self, query: str) -> str:
        import warnings

        warnings.filterwarnings(
            "ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited"
        )
        warnings.filterwarnings(
            "ignore", message=".*Task.*was destroyed but it is pending"
        )

        async def execute():
            agent = self._create_agent_in_loop()
            handler = agent.run(query)
            result = await handler
            return result

        try:
            response = await execute()
        except Exception:
            logger.exception("Agent execution error")
            raise

        text = self._extract_response_text(response)
        return self._clean_response(text)

    def _create_agent_in_loop(self) -> ReActAgent:
        engine = create_engine(
            self._config["db_uri"], pool_pre_ping=True, pool_recycle=3600, echo=False
        )
        try:
            try:
                sess, reqid = get_current()
                if reqid:
                    engine.info["request_id"] = reqid
                    if sess and hasattr(sess, "session_id"):
                        engine.info["session_id"] = getattr(
                            sess.session_id, "value", None
                        )
            except Exception:
                pass

            def _after_cursor_execute(
                conn, cursor, statement, parameters, context, executemany
            ):
                try:
                    if not statement or "SELECT" not in statement.upper():
                        return
                    session_obj, reqid = get_current()
                    if session_obj:
                        try:
                            session_obj.stats.update(
                                session_obj.stats.message_count,
                                session_obj.stats.query_count + 1,
                            )
                            session_obj._last_activity = datetime.now()
                            logger.info(
                                "Incremented query_count to %d for session %s",
                                getattr(session_obj.session_id, "value", "n/a"),
                                session_obj.stats.query_count,
                            )
                        except Exception:
                            logger.exception(
                                "Erro ao incrementar query_count nas estatísticas da session"
                            )
                except Exception:
                    logger.exception("Erro no listener after_cursor_execute")

            event.listen(engine, "after_cursor_execute", _after_cursor_execute)
        except Exception:
            logger.exception("Erro ao configurar listener de queries para o engine")

        db = SQLDatabase(engine, include_tables=None, sample_rows_in_table_info=2)

        model_name = "gemini-1.5-flash-latest"

        llm = GoogleGenAI(
            model=model_name,
            api_key=self._config["google_api_key"],
            temperature=0.2,
            max_tokens=2048,
            top_p=0.95,
        )

        embed_model = GoogleGenAIEmbedding(
            model_name="models/embedding-001",
            api_key=self._config["google_api_key"],
            embed_batch_size=10,
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
            return_raw=False,
        )

        sql_query_tool = QueryEngineTool.from_defaults(
            query_engine=sql_query_engine,
            name="sql_query_tool",
            description="FERRAMENTA OBRIGATÓRIA para QUALQUER pergunta sobre dados de pessoas. Executa consultas SQL T-SQL no banco de dados SQL Server. USE SEMPRE que o usuário perguntar sobre pessoas, dados, informações do banco. Retorna o resultado da consulta formatado.",
        )

        pdf_tool = _create_pdf_generation_tool(engine)

        def validate_sql(sql_text: str) -> str:
            try:
                inspector = sqlalchemy_inspect(engine)
                available_tables = inspector.get_table_names()
                import re

                found = set()
                for m in re.finditer(
                    r"\bFROM\s+([a-zA-Z0-9_\.\[\]\`\"]+)|\bJOIN\s+([a-zA-Z0-9_\.\[\]\`\"]+)",
                    sql_text,
                    re.IGNORECASE,
                ):
                    g1 = m.group(1) or m.group(2)
                    if g1:
                        tbl = g1.strip('`"[]')
                        if "." in tbl:
                            tbl = tbl.split(".")[-1]
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
            description="Valida se as tabelas referenciadas em uma consulta SQL existem no banco. Retorna 'OK' ou 'INVALID: ...' com sugestão. Use antes de executar SQL.",
        )

        tools = [sql_query_tool, pdf_tool, validate_tool]
        memory = ChatMemoryBuffer.from_defaults(
            token_limit=1500, tokenizer_fn=Settings.tokenizer
        )

        schema_summary = ""
        try:
            inspector = sqlalchemy_inspect(engine)
            tables = inspector.get_table_names()
            parts = []
            for t in tables[:20]:
                try:
                    cols = [c["name"] for c in inspector.get_columns(t)][:6]
                    parts.append(
                        f"{t}({', '.join(cols)}{'...' if len(cols) > 6 else ''})"
                    )
                except Exception:
                    parts.append(t)
            schema_summary = "\n".join(parts)
        except Exception:
            schema_summary = "(não foi possível ler o esquema do banco)"

        system_prompt = """Assistente SQL Server. Use sql_query_tool para consultar. Sintaxe T-SQL: TOP N.
Contexto: "dessas/desses" = dados anteriores.

Para gerar PDF com dados:
1. Use sql_query_tool para buscar
2. Use generate_pdf_tool com a query SQL
3. Retorne o link de download"""

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

        system_prompt += (
            "\n\nIMPORTANTE: Antes de executar QUALQUER SQL gerado, chame a ferramenta 'validate_sql_tool' com a consulta SQL exata. "
            "Se a ferramenta retornar 'OK', execute a consulta. Caso retorne 'INVALID', reescreva a consulta usando as tabelas válidas abaixo.\n\n"
            "Esquema do banco (tabelas e colunas):\n" + schema_summary + "\n"
        )

        return ReActAgent(
            tools=tools,
            llm=llm,
            memory=memory,
            verbose=False,
            system_prompt=system_prompt,
            max_iterations=10,
        )

    def _clean_response(self, text: str) -> str:
        text = text.strip()
        prefixes = [
            "assistant:",
            "Assistant:",
            "assistant :",
            "Assistant :",
            "Assistente:",
            "assistente:",
        ]
        for prefix in prefixes:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix) :].strip()
                break
        return text

    def _extract_response_text(self, response) -> str:
        try:
            if hasattr(response, "response"):
                chat_message = response.response
                if hasattr(chat_message, "blocks"):
                    blocks = chat_message.blocks
                    if blocks:
                        text_parts = []
                        for block in blocks:
                            try:
                                block_type = type(block).__name__
                                if block_type == "ThinkingBlock":
                                    continue
                                if hasattr(block, "text"):
                                    text_parts.append(str(block.text))
                                elif hasattr(block, "content"):
                                    text_parts.append(str(block.content))
                            except Exception:
                                continue

                        if text_parts:
                            combined = " ".join(text_parts)
                            try:
                                import re

                                url_match = re.search(r"(https?://\S+)", combined)
                                markdown_match = re.search(
                                    r"\[.*?\]\(https?://.*?\)", combined
                                )
                                if url_match and not markdown_match:
                                    url = url_match.group(1)
                                    from urllib.parse import urlparse, unquote

                                    p = urlparse(url)
                                    if p.hostname in (None, "127.0.0.1", "localhost"):
                                        local_path = unquote(p.path.lstrip("/"))
                                        abs_path = os.path.join(os.getcwd(), local_path)
                                        if not os.path.exists(abs_path):
                                            logger.warning(
                                                "Link mencionado pelo agente não encontrado: %s -> %s",
                                                url,
                                                abs_path,
                                            )
                                            return "Percebi que a resposta menciona um arquivo para download, mas o arquivo não foi encontrado no servidor. Quer que eu gere o arquivo agora?"
                            except Exception:
                                logger.debug(
                                    "Falha ao validar link na resposta do agente"
                                )
                            return combined

                if hasattr(chat_message, "content"):
                    try:
                        content = chat_message.content
                        if content:
                            try:
                                import re

                                url_match = re.search(r"(https?://\S+)", str(content))
                                markdown_match = re.search(
                                    r"\[.*?\]\(https?://.*?\)", str(content)
                                )
                                if url_match and not markdown_match:
                                    url = url_match.group(1)
                                    from urllib.parse import urlparse, unquote

                                    p = urlparse(url)
                                    if p.hostname in (None, "127.0.0.1", "localhost"):
                                        local_path = unquote(p.path.lstrip("/"))
                                        abs_path = os.path.join(os.getcwd(), local_path)
                                        if not os.path.exists(abs_path):
                                            logger.warning(
                                                "Link mencionado pelo agente não encontrado: %s -> %s",
                                                url,
                                                abs_path,
                                            )
                                            return "Percebi que a resposta menciona um arquivo para download, mas o arquivo não foi encontrado no servidor. Quer que eu gere o arquivo agora?"
                            except Exception:
                                logger.debug(
                                    "Falha ao validar link no conteúdo da resposta"
                                )
                            return str(content)
                    except Exception:
                        pass

            elif hasattr(response, "result") and callable(response.result):
                return str(response.result())
            elif hasattr(response, "result"):
                return str(response.result)

            return str(response)
        except Exception as e:
            logger.exception("Erro ao extrair texto do response: %s", e)
            return "Desculpe, houve um erro ao processar a resposta."


class QueryProcessorService(IQueryProcessorService):
    def __init__(self, chat_agent: IChatAgent, context_enhancer: IQueryContextEnhancer):
        self._chat_agent = chat_agent
        self._context_enhancer = context_enhancer

    async def process_query(
        self, query: str, session: Session, request_id: Optional[str] = None
    ) -> str:
        start = time.perf_counter()
        session_id = getattr(session, "session_id", None) or "n/a"
        q_preview = (query[:120] + "...") if len(query) > 120 else query

        now = datetime.now().strftime("%H:%M:%S")
        print(
            f"🟢 QUERY PROCESSOR [{session_id}]: iniciando (preview={q_preview}) — {now}",
            flush=True,
        )

        enhanced_query = self._context_enhancer.enhance_query(query, session)

        now = datetime.now().strftime("%H:%M:%S")
        print(
            f"🟢 QUERY PROCESSOR [{session_id}]: executando agente... — {now}",
            flush=True,
        )

        response = None
        ctx_tokens = None
        request_id_local = request_id or str(uuid.uuid4())

        try:
            proc = getattr(self._chat_agent, "process_query")
            if inspect.iscoroutinefunction(proc):
                ctx_tokens = set_for_context(session, request_id_local)
                try:
                    current_task = asyncio.current_task()
                    if request_id_local and current_task is not None:
                        register_task(request_id_local, current_task)
                except Exception:
                    pass
                response = await proc(enhanced_query)
            else:
                set_for_thread(session, request_id_local)
                try:
                    response = await asyncio.to_thread(proc, enhanced_query)
                finally:
                    clear_for_thread()
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.exception(
                "❌ QUERY PROCESSOR [%s]: erro ao chamar agent after %.2fs: %s",
                session_id,
                elapsed,
                exc,
            )
            raise
        finally:
            if ctx_tokens:
                try:
                    reset_context(ctx_tokens)
                except Exception:
                    pass
            try:
                if request_id_local:
                    unregister_task(request_id_local)
            except Exception:
                pass

            elapsed = time.perf_counter() - start
            now = datetime.now().strftime("%H:%M:%S")
            print(
                f"🟢 QUERY PROCESSOR [{session_id}]: resposta recebida em {elapsed:.2f}s — {now}",
                flush=True,
            )
            now = datetime.now().strftime("%H:%M:%S")
            preview = (
                (response[:200] if isinstance(response, str) else str(response))
                if response is not None
                else "<no response>"
            )
            print(f"   Resposta (preview): {preview} — {now}", flush=True)

        await self._try_capture_query_result(response, session)
        return response

    async def _try_capture_query_result(
        self, agent_response: str, session: Session
    ) -> None:
        try:
            import re

            sql_pattern = r"SELECT\s+.*?(?=\s*$|\s*;|\s*\)|\s+UNION|\s+ORDER\s+BY|\s+GROUP\s+BY|\s+HAVING|\s+LIMIT|\s+OFFSET)"
            sql_match = re.search(
                sql_pattern, agent_response, re.IGNORECASE | re.DOTALL
            )

            if sql_match:
                sql_query = sql_match.group(0).strip()
                query_result = QueryResult(
                    query=sql_query,
                    result_data="Query executada com sucesso",
                    timestamp=datetime.now(),
                    row_count=0,
                    columns=[],
                    query_type=QueryType.SELECT,
                )
                session.add_query_result(query_result)
        except Exception:
            pass


class LlamaIndexAgentFactory:
    @staticmethod
    def create_agent() -> IChatAgent:
        db_uri = os.getenv("DATABASE_URL_ALTERNATIVE")
        google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

        if not db_uri or not google_api_key:
            raise ValueError("Missing required environment variables")
        config = {"db_uri": db_uri, "google_api_key": google_api_key}
        return AsyncAgentAdapter(LlamaIndexChatAgent(config))
