import os
from dotenv import load_dotenv
import pandas as pd
import uuid
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import initialize_agent, AgentType
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.tools import tool
import traceback
from typing import Optional
from fpdf import FPDF

load_dotenv()

db_uri = os.getenv("DATABASE_URL")
google_api_key = os.getenv("GOOGLE_API_KEY")

if not db_uri:
    raise ValueError("A variável de ambiente DATABASE_URL não foi definida.")
    
try:
    db = SQLDatabase.from_uri(db_uri)
except Exception as e:
    print(f"ERRO: LangChain não conseguiu conectar ao DB: {e}. Verifique a URI e drivers.")
    db = None

engine: Optional[Engine] = None
if db_uri:
    try:
        if 'mssql' in db_uri:
            engine = create_engine(db_uri, fast_executemany=True)
        else:
            engine = create_engine(db_uri)
        print("Motor do SQLAlchemy criado com sucesso para o Pandas.")
    except Exception as e:
        print(f"ERRO: Não foi possível criar o motor do SQLAlchemy. O erro pode ser de DRIVER (ex: pyodbc para SQL Server): {e}")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    google_api_key=google_api_key, 
    convert_system_message_to_human=True
)

@tool
def nl_to_sql(question: str) -> str:
    """
    Converte um pedido em linguagem natural em uma consulta SQL (T-SQL para SQL Server) baseada no esquema atual do banco.
    Regras: Retorne APENAS a consulta SQL, use T-SQL (TOP N, GETDATE()), utilize apenas tabelas existentes.
    """
    if not db:
        return "Erro: Conexão com o banco de dados indisponível."
        
    try:
        schema = db.get_table_info()
        system = (
            "Você é um gerador de consultas para SQL Server (T-SQL). Regras: "
            "(1) Use somente tabelas/colunas do esquema fornecido. "
            "(2) Prefira SELECT; não use INSERT/UPDATE/DELETE a menos que explicitamente solicitado. "
            "(3) Retorne apenas a consulta SQL, sem explicações, comentários ou markdown. "
            "(4) Use TOP N em vez de LIMIT. (5) Utilize funções do SQL Server quando necessário."
        )

        few_shots = (
            "Exemplos T-SQL (apenas SQL):\n"
            "SELECT TOP 100 Nome AS Nome FROM Filiais;\n\n"
            "SELECT DATENAME(month, Data) AS Mes, COUNT(*) AS Total\n"
            "FROM Pedidos\n"
            "WHERE YEAR(Data) = YEAR(GETDATE())\n"
            "GROUP BY DATENAME(month, Data), MONTH(Data)\n"
            "ORDER BY MONTH(Data);\n\n"
            "SELECT TOP 50 c.Nome, p.Numero, p.Valor\n"
            "FROM Clientes c\n"
            "JOIN Pedidos p ON p.ClienteId = c.Id\n"
            "ORDER BY p.Data DESC;\n\n"
            "SELECT\n"
            "  p.Id, p.Valor,\n"
            "  ROW_NUMBER() OVER (PARTITION BY p.ClienteId ORDER BY p.Data DESC) AS rn\n"
            "FROM Pedidos p;\n\n"
            "SELECT * FROM Pedidos WHERE Data >= DATEADD(DAY, -30, CAST(GETDATE() AS date));\n"
        )

        prompt = (
            f"{system}\n\nEsquema (tabelas e colunas):\n{schema}\n\n"
            f"{few_shots}\n"
            f"Pedido do usuário (pt-BR):\n{question}\n\nSQL:" 
        )

        res = llm.invoke(prompt)
        sql = res.content if hasattr(res, "content") else str(res)
        sql = sql.replace("```sql", "").replace("```", "").strip()
        return sql
    except Exception as e:
        traceback.print_exc()
        return f"Erro ao gerar SQL: {e}"

@tool
def refine_sql(instruction_and_sql: str) -> str:
    """
    Refina uma consulta SQL existente com base em instruções em linguagem natural.
    Entrada: texto contendo instruções e a query original após a palavra-chave 'SQL:'.
    Saída: somente a consulta T-SQL final.
    """
    if not db:
        return "Erro: Conexão com o banco de dados indisponível."
        
    try:
        schema = db.get_table_info()
        system = (
            "Você é um refatorador de T-SQL para SQL Server. Retorne apenas a SQL final, sem comentários."
        )
        prompt = (
            f"{system}\n\nEsquema:\n{schema}\n\n"
            f"Instruções + Query:\n{instruction_and_sql}\n\nSQL:" 
        )
        res = llm.invoke(prompt)
        sql = res.content if hasattr(res, "content") else str(res)
        sql = sql.replace("```sql", "").replace("```", "").strip()
        return sql
    except Exception as e:
        traceback.print_exc()
        return f"Erro ao refinar SQL: {e}"
    
@tool
def print_data_to_user(data: str) -> str:
    """
    Retorna a string de dados fornecida diretamente como a Resposta Final para o usuário. 
    Use esta ferramenta SEMPRE que a ferramenta 'sql_db_query' retornar uma Observação que deve ser exibida ao usuário (dados tabulares ou lista de fatos) 
    e NÃO houver necessidade de exportação (Excel/CSV/PDF).
    """
    return data # Retorna a string diretamente.

@tool
def export_query_to_excel(query: str) -> str:
    """
    Executa uma consulta SQL SELECT, salva os resultados em um arquivo Excel (.xlsx) e retorna um link de download.
    Use para pedidos de exportação para Excel ou planilha. O input deve ser uma consulta SQL SELECT válida.
    """
    global engine
    if engine is None:
        return "Erro: O motor de conexão do banco de dados (SQLAlchemy Engine) não foi inicializado corretamente. Verifique a URI e os drivers."
        
    print("\n--- [DEBUG] INICIANDO 'export_query_to_excel' ---")
    print(f"[DEBUG] Query recebida: {query}")
    
    try:
        if not query.strip().upper().startswith("SELECT"):
            print("[DEBUG] Erro: A query não é um SELECT.")
            return "Erro: Apenas consultas SELECT podem ser exportadas para Excel."

        max_rows = int(os.getenv("MAX_EXPORT_ROWS", "100000"))
        
        with engine.begin() as conn:
            print("[DEBUG] Executando a consulta de contagem de linhas...")
            row_count_df = pd.read_sql_query(f"SELECT COUNT(*) FROM ({query}) AS subquery", con=conn.connection)
            total_rows = row_count_df.iloc[0, 0]
            print(f"[DEBUG] Total de linhas encontrado: {total_rows}")

            if total_rows > max_rows:
                print(f"[DEBUG] Erro: Total de linhas ({total_rows}) excede o máximo ({max_rows}).")
                return (
                    f"A consulta retornaria {total_rows} linhas, o que excede o limite de {max_rows}. "
                    "Refine o filtro antes de exportar ou use a exportação para CSV."
                )
            
            print("[DEBUG] Executando a consulta principal para obter os dados...")
            df = pd.read_sql_query(sql=query, con=conn.connection)
            print(f"[DEBUG] Dados carregados no DataFrame. Linhas: {len(df)}")

        filename = f"resultado_{uuid.uuid4()}.xlsx"
        filepath = os.path.join("downloads", filename)
        os.makedirs("downloads", exist_ok=True)
        
        print(f"[DEBUG] Salvando o arquivo em: {filepath}")
        df.to_excel(filepath, index=False, engine='openpyxl')
        print("[DEBUG] Arquivo Excel salvo com sucesso.")

        base_url = "http://127.0.0.1:8000"
        download_link = f"{base_url}/{filepath.replace(os.sep, '/')}"

        print("--- [DEBUG] FINALIZANDO 'export_query_to_excel' COM SUCESSO ---")
        return f"⬇️ [Clique aqui para baixar]({download_link})" 
    except Exception as e:
        print("\n--- [DEBUG] OCORREU UMA EXCEÇÃO AO EXPORTAR PARA EXCEL! ---")
        print(f"[DEBUG] Tipo da Exceção: {type(e).__name__}")
        print(f"[DEBUG] Mensagem da Exceção: {e}")
        print("[DEBUG] Traceback completo:")
        traceback.print_exc()
        print("--- [DEBUG] FIM DA EXCEÇÃO ---\n")
        return f"Ocorreu um erro ao exportar para Excel: {type(e).__name__}: {e}. Verifique drivers e URI."

@tool
def export_query_to_csv(query: str) -> str:
    """
    Executa uma consulta SQL SELECT, salva os resultados em um arquivo CSV (.csv) e retorna um link de download.
    Use para pedidos de exportação para CSV. O input deve ser uma consulta SQL SELECT válida.
    """
    global engine
    if engine is None:
        return "Erro: O motor de conexão do banco de dados (SQLAlchemy Engine) não foi inicializado corretamente. Verifique a URI e os drivers."
        
    try:
        if not query.strip().upper().startswith("SELECT"):
            return "Erro: Apenas consultas SELECT podem ser exportadas para CSV."

        os.makedirs("downloads", exist_ok=True)
        filename = f"resultado_{uuid.uuid4()}.csv"
        filepath = os.path.join("downloads", filename)
        
        with engine.begin() as conn:
            first_chunk = True
            for chunk in pd.read_sql_query(query, con=conn.connection, chunksize=50000):
                chunk.to_csv(
                    filepath,
                    mode='w' if first_chunk else 'a',
                    header=first_chunk,
                    index=False,
                    sep=';',
                    encoding='utf-8-sig'
                )
                first_chunk = False
            
            if first_chunk:
                 df_empty = pd.read_sql_query(query + " WHERE 1=0", con=conn.connection)
                 df_empty.to_csv(filepath, index=False, sep=';', encoding='utf-8-sig')

        base_url = "http://127.0.0.1:8000"
        download_link = f"{base_url}/{filepath.replace(os.sep, '/')}"
        
        return f"⬇️ [Clique aqui para baixar]({download_link})"
    except Exception as e:
        traceback.print_exc()
        return f"Ocorreu um erro ao exportar para CSV: {e}. Informe o usuário sobre o erro."


@tool
def export_query_to_pdf(query: str) -> str:
    """
    Executa uma consulta SQL SELECT e salva os resultados em um arquivo PDF (.pdf).
    Use esta ferramenta quando o usuário pedir para gerar um relatório em PDF ou documento em PDF.
    O input deve ser uma consulta SQL SELECT válida.
    """
    global engine
    if engine is None:
        return "Erro: O motor de conexão do banco de dados (SQLAlchemy Engine) não foi inicializado corretamente."
    
    print("\n--- [DEBUG] INICIANDO 'export_query_to_pdf' ---")

    try:
        if not query.strip().upper().startswith("SELECT"):
            return "Erro: Apenas consultas SELECT podem ser exportadas para PDF."

        with engine.begin() as conn:
            df = pd.read_sql_query(sql=query, con=conn.connection)
        
        if df.empty:
            return "A consulta não retornou resultados para exportar."

        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font('Arial', 'B', 10)
        
        col_width = 277 / len(df.columns)
        col_height = 8

        pdf.set_fill_color(200, 220, 255)
        for col in df.columns:
            pdf.cell(col_width, col_height, str(col), border=1, ln=0, align='C', fill=True)
        pdf.ln(col_height)
        
        pdf.set_font('Arial', '', 9)
        
        for index, row in df.iterrows():
            if pdf.get_y() > 190:
                pdf.add_page()
                pdf.set_font('Arial', 'B', 10)
                for col in df.columns:
                    pdf.cell(col_width, col_height, str(col), border=1, ln=0, align='C', fill=True)
                pdf.ln(col_height)
                pdf.set_font('Arial', '', 9)
            
            for item in row.values:
                pdf.cell(col_width, col_height, str(item), border=1, ln=0, align='L') 
            
            pdf.ln(col_height)
            
        filename = f"relatorio_{uuid.uuid4()}.pdf"
        filepath = os.path.join("downloads", filename)
        os.makedirs("downloads", exist_ok=True)
        pdf.output(filepath, 'F')

        base_url = "http://127.0.0.1:8000"
        download_link = f"{base_url}/{filepath.replace(os.sep, '/')}"

        print("--- [DEBUG] FINALIZANDO 'export_query_to_pdf' COM SUCESSO ---")
        return f"⬇️ [Clique aqui para baixar]({download_link})"

    except Exception as e:
        print("\n--- [DEBUG] OCORREU UMA EXCEÇÃO AO EXPORTAR PARA PDF! ---")
        traceback.print_exc()
        return f"Ocorreu um erro ao exportar para PDF: {e}. Certifique-se de que a query é um SELECT válido."

if db:
    sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    sql_tools = sql_toolkit.get_tools()
else:
    sql_tools = []
    print("Aviso: SQLDatabase Toolkit desabilitado porque a conexão inicial falhou.")
    
# NOVO: print_data_to_user foi adicionado aqui!
all_tools = sql_tools + [nl_to_sql, refine_sql, export_query_to_excel, export_query_to_csv, export_query_to_pdf, print_data_to_user]

agent_executor = initialize_agent(
    tools=all_tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=12,
    early_stopping_method="force",
)

async def generate_chat_title(prompt:str) -> str:
    try:
        title_prompt=f"Crie um título curto e conciso de no máximo 5 palavras em português para uma conversa que começou com a seguinte pergunta do usuário:'{prompt}'"
        response_content = await llm.ainvoke(title_prompt)
        title = response_content.content if hasattr(response_content, 'content') else str(response_content)
        return title.strip().replace("\"", "")
    except Exception as e:
        print(f"Erro ao gerar título: {e}")
        return "Nova Conversa"

async def get_response(user_query: str):
    try:
        instruction = "Responda sempre em português do Brasil. Você tem as ferramentas `export_query_to_excel`, `export_query_to_csv`, `export_query_to_pdf` e `print_data_to_user` para mostrar dados. Use a ferramenta `print_data_to_user` quando a `sql_db_query` retornar dados que devem ser exibidos ao usuário."
        response = await agent_executor.ainvoke({"input": instruction + user_query})
        return {"success": True, "data": response.get("output")}
    except Exception as e:
        print(f"Ocorreu um erro inesperado no agente: {e}")
        traceback.print_exc() 
        return {"success": False, "error": f"Ocorreu um erro ao processar sua pergunta: {e}"}
