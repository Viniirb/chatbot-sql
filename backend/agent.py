import os
import traceback
import uuid
import asyncio
import warnings
from typing import Optional, List

# Suprimir warnings específicos do Pydantic
warnings.filterwarnings("ignore", message=".*validate_default.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*UnsupportedFieldAttributeWarning.*")

import pandas as pd
from dotenv import load_dotenv
from fpdf import FPDF
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Importações do LlamaIndex
from llama_index.core import Settings, SQLDatabase
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.core.tools import QueryEngineTool, FunctionTool
from llama_index.core.agent import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.base.llms.types import ChatMessage, MessageRole

load_dotenv()

# --- Configurações de API e DB ---
db_uri = os.getenv("DATABASE_URL")
google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

if not db_uri:
    raise ValueError("A variável de ambiente DATABASE_URL não foi definida.")
if not google_api_key:
    raise ValueError("A variável de ambiente GOOGLE_API_KEY ou GEMINI_API_KEY não foi definida.")

engine: Optional[Engine] = None
db: Optional[SQLDatabase] = None

try:
    if 'mssql' in db_uri:
        engine = create_engine(
            db_uri, 
            fast_executemany=True,
            pool_pre_ping=True,  # Verificar conexões antes de usar
            pool_recycle=3600,   # Reciclar conexões a cada hora
            echo=False           # Não mostrar SQL no console (produção)
        )
    else:
        engine = create_engine(
            db_uri,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
    
    # Testar a conexão
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    
    # Configurar SQLDatabase com parâmetros otimizados
    db = SQLDatabase(
        engine, 
        include_tables=None,  # Incluir todas as tabelas por padrão
        sample_rows_in_table_info=3  # Mostrar até 3 linhas de exemplo
    )
    print(f"✅ Conexão com banco de dados estabelecida com sucesso.")
except Exception as e:
    print(f"❌ ERRO CRÍTICO: Conexão com o DB falhou: {e}. Verifique a URI e drivers.")
    engine = None
    db = None

# --- Configuração do LLM e LlamaIndex ---
llm = GoogleGenAI(
    model_name="models/gemini-2.5-flash", 
    api_key=google_api_key,
    temperature=0.1,  # Baixa temperatura para maior precisão em SQL
    max_tokens=4096,
    top_p=0.95
)

# Configuração do modelo de embedding
embed_model = GoogleGenAIEmbedding(
    model_name="models/embedding-001", 
    api_key=google_api_key,
    embed_batch_size=10  # Processar embeddings em lotes menores
)

# Configurações globais do LlamaIndex
Settings.llm = llm
Settings.embed_model = embed_model
Settings.chunk_size = 1024
Settings.chunk_overlap = 200

# --- Ferramentas Personalizadas (Tools) ---
def print_data_to_user(data: str) -> str:
    """Retorna dados tabulares ou fatos diretamente como a resposta final para o usuário."""
    return data

def export_query_to_excel(query: str) -> str:
    """Executa uma consulta SQL SELECT e retorna um link de download para um arquivo Excel."""
    global engine
    if engine is None:
        return "❌ Erro: Conexão com o banco de dados não inicializada."
    
    try:
        # Validação mais rigorosa da query
        query_clean = query.strip()
        if not query_clean.upper().startswith("SELECT"):
            return "❌ Erro: Apenas consultas SELECT podem ser exportadas."
        
        # Verificar se não contém comandos perigosos
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        query_upper = query_clean.upper()
        if any(keyword in query_upper for keyword in dangerous_keywords):
            return "❌ Erro: Query contém comandos não permitidos para exportação."
        
        # Executar query com limite de segurança
        with engine.connect() as conn:
            df = pd.read_sql_query(sql=query_clean, con=conn)
        
        if df.empty:
            return "⚠️ A consulta não retornou resultados para exportar."
        
        if len(df) > 100000:
            return f"⚠️ Resultado muito grande ({len(df)} linhas). Limite a consulta a no máximo 100.000 registros."
        
        filename = f"resultado_{uuid.uuid4().hex[:8]}.xlsx"
        filepath = os.path.join("downloads", filename)
        os.makedirs("downloads", exist_ok=True)
        
        df.to_excel(filepath, index=False, engine='openpyxl')
        download_link = f"http://127.0.0.1:8000/{filepath.replace(os.sep, '/')}"
        
        return f"✅ Excel gerado com {len(df)} linhas e {len(df.columns)} colunas.\n⬇️ [Clique aqui para baixar]({download_link})"
        
    except Exception as e:
        print(f"Erro na exportação Excel: {e}")
        traceback.print_exc()
        return f"❌ Erro ao exportar para Excel: {str(e)}"

def export_query_to_csv(query: str) -> str:
    """Executa uma consulta SQL SELECT e retorna um link de download para um arquivo CSV."""
    global engine
    if engine is None:
        return "❌ Erro: Conexão com o banco de dados não inicializada."
    
    try:
        # Validação da query
        query_clean = query.strip()
        if not query_clean.upper().startswith("SELECT"):
            return "❌ Erro: Apenas consultas SELECT podem ser exportadas."
        
        # Verificar comandos perigosos
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        query_upper = query_clean.upper()
        if any(keyword in query_upper for keyword in dangerous_keywords):
            return "❌ Erro: Query contém comandos não permitidos para exportação."
        
        os.makedirs("downloads", exist_ok=True)
        filename = f"resultado_{uuid.uuid4().hex[:8]}.csv"
        filepath = os.path.join("downloads", filename)
        
        total_rows = 0
        with engine.connect() as conn:
            first_chunk = True
            # Processar em chunks para arquivos grandes
            for chunk in pd.read_sql_query(query_clean, con=conn, chunksize=50000):
                if first_chunk and chunk.empty:
                    return "⚠️ A consulta não retornou resultados para exportar."
                
                chunk.to_csv(
                    filepath, 
                    mode='w' if first_chunk else 'a', 
                    header=first_chunk, 
                    index=False, 
                    sep=';', 
                    encoding='utf-8-sig'
                )
                total_rows += len(chunk)
                first_chunk = False
                
                # Limite de segurança
                if total_rows > 500000:
                    return f"⚠️ Exportação limitada a 500.000 registros por segurança. Total processado: {total_rows} linhas."
        
        download_link = f"http://127.0.0.1:8000/{filepath.replace(os.sep, '/')}"
        return f"✅ CSV gerado com {total_rows} linhas.\n⬇️ [Clique aqui para baixar]({download_link})"
        
    except Exception as e:
        print(f"Erro na exportação CSV: {e}")
        traceback.print_exc()
        return f"❌ Erro ao exportar para CSV: {str(e)}"

def export_query_to_pdf(query: str) -> str:
    """Executa uma consulta SQL SELECT e retorna um link de download para um arquivo PDF."""
    global engine
    if engine is None:
        return "❌ Erro: Conexão com o banco de dados não inicializada."
    
    try:
        # Validação da query
        query_clean = query.strip()
        if not query_clean.upper().startswith("SELECT"):
            return "❌ Erro: Apenas consultas SELECT podem ser exportadas."
        
        # Verificar comandos perigosos
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        query_upper = query_clean.upper()
        if any(keyword in query_upper for keyword in dangerous_keywords):
            return "❌ Erro: Query contém comandos não permitidos para exportação."
        
        # Executar query
        with engine.connect() as conn:
            df = pd.read_sql_query(sql=query_clean, con=conn)
        
        if df.empty:
            return "⚠️ A consulta não retornou resultados para exportar."
        
        # Limite para PDF (formato não é ideal para muitos dados)
        if len(df) > 1000:
            return f"⚠️ Muitas linhas para PDF ({len(df)}). Use CSV ou Excel para mais de 1.000 registros."
        
        if len(df.columns) > 8:
            return f"⚠️ Muitas colunas para PDF ({len(df.columns)}). Use CSV ou Excel para mais de 8 colunas."
        
        # Criar PDF
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font('Arial', '', 9)
        
        # Calcular largura das colunas
        available_width = 277  # A4 paisagem menos margens
        col_width = available_width / len(df.columns)
        max_col_width = 35  # Largura máxima por coluna
        col_width = min(col_width, max_col_width)
        
        # Cabeçalho
        pdf.set_font('Arial', 'B', 10)
        for col in df.columns:
            # Truncar nomes de colunas muito longos
            col_name = str(col)[:15] + "..." if len(str(col)) > 15 else str(col)
            pdf.cell(col_width, 8, col_name, border=1, align='C')
        pdf.ln()

        # Dados
        pdf.set_font('Arial', '', 8)
        for _, row in df.iterrows():
            for item in row.values:
                # Truncar conteúdo muito longo
                content = str(item) if item is not None else ""
                if len(content) > 20:
                    content = content[:17] + "..."
                pdf.cell(col_width, 6, content, border=1, align='L')
            pdf.ln()

        filename = f"relatorio_{uuid.uuid4().hex[:8]}.pdf"
        filepath = os.path.join("downloads", filename)
        os.makedirs("downloads", exist_ok=True)
        pdf.output(filepath)
        
        download_link = f"http://127.0.0.1:8000/{filepath.replace(os.sep, '/')}"
        return f"✅ PDF gerado com {len(df)} linhas e {len(df.columns)} colunas.\n⬇️ [Clique aqui para baixar]({download_link})"
        
    except Exception as e:
        print(f"Erro na exportação PDF: {e}")
        traceback.print_exc()
        return f"❌ Erro ao exportar para PDF: {str(e)}"

# --- Criação das Ferramentas e do Agente ---
sql_query_engine = None
all_tools = []

if db:
    # Configurar o query engine com parâmetros otimizados
    sql_query_engine = NLSQLTableQueryEngine(
        sql_database=db,
        llm=llm,
        embed_model=embed_model,
        synthesize_response=True,  # Sintetizar resposta mais clara
        streaming=False,           # Desabilitar streaming para maior estabilidade
        return_raw=False          # Retornar resposta processada
    )
    
    sql_query_tool = QueryEngineTool.from_defaults(
        query_engine=sql_query_engine, 
        name="sql_query_tool",
        description=(
            "Converte uma pergunta em linguagem natural para uma consulta SQL T-SQL "
            "e a executa no banco de dados SQL Server. Retorna o resultado da consulta formatado. "
            "Use esta ferramenta para qualquer pergunta sobre dados no banco de dados."
        )
    )
    all_tools.append(sql_query_tool)
    print(f"✅ Query engine SQL configurado com sucesso.")
else:
    print(f"⚠️ Query engine SQL não pôde ser configurado devido a problemas de conexão.")

# Criar ferramentas personalizadas usando FunctionTool
custom_tools = [
    FunctionTool.from_defaults(
        fn=print_data_to_user,
        name="print_data_to_user",
        description="Retorna dados tabulares ou fatos diretamente como a resposta final para o usuário."
    ),
    FunctionTool.from_defaults(
        fn=export_query_to_excel,
        name="export_query_to_excel", 
        description="Executa uma consulta SQL SELECT e retorna um link de download para um arquivo Excel."
    ),
    FunctionTool.from_defaults(
        fn=export_query_to_csv,
        name="export_query_to_csv",
        description="Executa uma consulta SQL SELECT e retorna um link de download para um arquivo CSV."
    ),
    FunctionTool.from_defaults(
        fn=export_query_to_pdf,
        name="export_query_to_pdf",
        description="Executa uma consulta SQL SELECT e retorna um link de download para um arquivo PDF."
    )
]
all_tools.extend(custom_tools)

# Configurar memória com buffer otimizado
memory = ChatMemoryBuffer.from_defaults(
    token_limit=4000,
    tokenizer_fn=Settings.tokenizer
)

# System prompt melhorado
system_prompt = """
Você é um assistente especialista em análise de dados e SQL Server (T-SQL). 
Suas responsabilidades:

1. 🎯 PRINCIPAL: Use sempre a ferramenta `sql_query_tool` para responder perguntas sobre dados
2. 📊 APRESENTAÇÃO: Após obter dados, use `print_data_to_user` para mostrar os resultados formatados
3. 📁 EXPORTAÇÃO: Use ferramentas de exportação (Excel/CSV/PDF) APENAS quando explicitamente solicitado
4. 💬 IDIOMA: Responda sempre em português brasileiro
5. 🔧 SQL: Use sintaxe T-SQL (TOP N, não LIMIT; GETDATE(), não NOW())
6. 📈 ANÁLISE: Forneça insights quando apropriado sobre os dados retornados

SEMPRE siga este fluxo:
1. Entenda a pergunta do usuário
2. Use sql_query_tool para buscar dados
3. Use print_data_to_user para apresentar os resultados
4. Adicione insights ou explicações relevantes

Seja preciso, claro e útil!
"""

if all_tools:
    chat_agent = ReActAgent(
        tools=all_tools,
        llm=llm,
        memory=memory,
        verbose=True,
        system_prompt=system_prompt,
        max_iterations=10  # Limitar iterações para evitar loops
    )
    print(f"✅ Agente ReAct configurado com {len(all_tools)} ferramentas.")
else:
    print(f"❌ Erro: Nenhuma ferramenta disponível para configurar o agente.")
    chat_agent = None

# --- Funções da API ---
async def generate_chat_title(prompt: str) -> str:
    """Gera um título para a conversa baseado no prompt inicial."""
    try:
        if not prompt.strip():
            return "Nova Conversa"
            
        title_prompt = (
            f"Crie um título curto e descritivo (máximo 6 palavras) em português brasileiro "
            f"para uma conversa sobre: '{prompt[:200]}'"
        )
        
        response = await llm.acomplete(title_prompt)
        title = response.text.strip().replace('"', "").replace("'", "")
        
        # Limitar tamanho do título
        if len(title) > 50:
            title = title[:47] + "..."
            
        return title if title else "Nova Conversa"
        
    except Exception as e:
        print(f"⚠️ Erro ao gerar título: {e}")
        return "Nova Conversa"

async def get_response(user_query: str):
    """Processa a consulta do usuário através do agente."""
    try:
        if not user_query.strip():
            return {"success": False, "error": "Query vazia fornecida."}
            
        if chat_agent is None:
            return {
                "success": False, 
                "error": "Agente não inicializado. Verifique a configuração do banco de dados."
            }
        
        # Adicionar timeout para evitar travamentos
        response = await asyncio.wait_for(
            chat_agent.achat(user_query),
            timeout=120  # 2 minutos de timeout
        )
        
        return {"success": True, "data": str(response)}
        
    except asyncio.TimeoutError:
        error_msg = "⏱️ Timeout: A consulta demorou muito para ser processada. Tente uma pergunta mais específica."
        print(error_msg)
        return {"success": False, "error": error_msg}
        
    except Exception as e:
        error_msg = f"Erro ao processar sua pergunta: {str(e)}"
        print(f"❌ Erro inesperado no agente: {e}")
        traceback.print_exc()
        return {"success": False, "error": error_msg}