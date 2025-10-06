import os
from dotenv import load_dotenv
import pandas as pd
import uuid
from sqlalchemy import create_engine # Manter o import, embora não seja mais usado nas tools
from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import initialize_agent, AgentType
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.tools import tool
import traceback

load_dotenv()

db_uri = os.getenv("DATABASE_URL")
google_api_key = os.getenv("GOOGLE_API_KEY")

db = SQLDatabase.from_uri(db_uri)

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=google_api_key, convert_system_message_to_human=True)

# As ferramentas nl_to_sql e refine_sql permanecem as mesmas...
@tool
def nl_to_sql(question: str) -> str:
    """
    Converte um pedido em linguagem natural em uma consulta SQL (T-SQL para SQL Server) baseada no esquema atual do banco.
    Regras:
    - Retorne APENAS a consulta SQL (sem explicações, sem markdown).
    - Prefira SELECT; não use INSERT/UPDATE/DELETE a menos que o usuário peça explicitamente.
    - Use recursos do SQL Server (por exemplo, TOP N em vez de LIMIT, funções T-SQL).
    - Utilize apenas tabelas/colunas existentes no esquema fornecido.
    - Quando o usuário pedir "apenas o Nome", retorne somente a coluna correspondente com alias solicitado, ex.: SELECT Nome AS Nome FROM ...
    """
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
            "-- Apenas a coluna Nome com alias\n"
            "SELECT TOP 100 Nome AS Nome FROM Filiais;\n\n"
            "-- Contagem por mês no ano atual\n"
            "SELECT DATENAME(month, Data) AS Mes, COUNT(*) AS Total\n"
            "FROM Pedidos\n"
            "WHERE YEAR(Data) = YEAR(GETDATE())\n"
            "GROUP BY DATENAME(month, Data), MONTH(Data)\n"
            "ORDER BY MONTH(Data);\n\n"
            "-- Junção entre tabelas por chave estrangeira\n"
            "SELECT TOP 50 c.Nome, p.Numero, p.Valor\n"
            "FROM Clientes c\n"
            "JOIN Pedidos p ON p.ClienteId = c.Id\n"
            "ORDER BY p.Data DESC;\n\n"
            "-- Janela (ranking)\n"
            "SELECT\n"
            "  p.Id, p.Valor,\n"
            "  ROW_NUMBER() OVER (PARTITION BY p.ClienteId ORDER BY p.Data DESC) AS rn\n"
            "FROM Pedidos p;\n\n"
            "-- Últimos 30 dias\n"
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
        return f"Erro ao gerar SQL: {e}"

@tool
def refine_sql(instruction_and_sql: str) -> str:
    """
    Refina uma consulta SQL existente com base em instruções em linguagem natural.
    Entrada: texto contendo instruções e a query original após a palavra-chave 'SQL:'.
    Ex.: "Mantenha a mesma lógica e traga apenas a coluna Nome com alias Nome.\nSQL: SELECT Id, Nome, Cidade FROM Filiais"
    Saída: somente a consulta T-SQL final (sem explicações/markdown).
    Regras: preserve SQL Server (TOP, funções T-SQL) e o significado original salvo instrução contrária.
    """
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
        return f"Erro ao refinar SQL: {e}"


@tool
def export_query_to_excel(query: str) -> str:
    """
    Executa uma consulta SQL SELECT, salva os resultados em um arquivo Excel (.xlsx) e retorna um link para download.
    Use esta ferramenta quando o usuário pedir para exportar dados, criar uma planilha ou um arquivo excel.
    O input deve ser uma consulta SQL SELECT válida.
    """
    # --- 2. ADICIONE OS PRINTS DE DEBUG ---
    print("\n--- [DEBUG] INICIANDO 'export_query_to_excel' ---")
    print(f"[DEBUG] Query recebida: {query}")
    print(f"[DEBUG] URI do Banco de Dados: {db_uri}")
    
    try:
        if not query.strip().upper().startswith("SELECT"):
            print("[DEBUG] Erro: A query não é um SELECT.")
            return "Erro: Apenas consultas SELECT podem ser exportadas para Excel."

        max_rows = int(os.getenv("MAX_EXPORT_ROWS", "100000"))
        
        print("[DEBUG] Executando a consulta de contagem de linhas...")
        row_count_df = pd.read_sql_query(f"SELECT COUNT(*) FROM ({query}) AS subquery", db_uri)
        total_rows = row_count_df.iloc[0, 0]
        print(f"[DEBUG] Total de linhas encontrado: {total_rows}")

        if total_rows > max_rows:
            print(f"[DEBUG] Erro: Total de linhas ({total_rows}) excede o máximo ({max_rows}).")
            return (
                f"A consulta retornaria {total_rows} linhas, o que excede o limite de {max_rows}. "
                "Refine o filtro antes de exportar ou use a exportação para CSV."
            )
        
        print("[DEBUG] Executando a consulta principal para obter os dados...")
        df = pd.read_sql_query(query, db_uri)
        print("[DEBUG] Dados carregados no DataFrame com sucesso.")

        filename = f"resultado_{uuid.uuid4()}.xlsx"
        filepath = os.path.join("downloads", filename)
        os.makedirs("downloads", exist_ok=True)
        
        print(f"[DEBUG] Salvando o arquivo em: {filepath}")
        df.to_excel(filepath, index=False, engine='openpyxl')
        print("[DEBUG] Arquivo Excel salvo com sucesso.")

        base_url = "http://127.0.0.1:8000"
        download_link = f"{base_url}/{filepath.replace(os.sep, '/')}"

        print("--- [DEBUG] FINALIZANDO 'export_query_to_excel' COM SUCESSO ---")
        return f"Arquivo Excel gerado com sucesso. O usuário pode fazer o download aqui: {download_link}"
    except Exception as e:
        # --- 3. CAPTURE E IMPRIMA O ERRO COMPLETO ---
        print("\n--- [DEBUG] OCORREU UMA EXCEÇÃO! ---")
        print(f"[DEBUG] Tipo da Exceção: {type(e).__name__}")
        print(f"[DEBUG] Mensagem da Exceção: {e}")
        print("[DEBUG] Traceback completo:")
        traceback.print_exc() # Imprime o stack trace completo no console
        print("--- [DEBUG] FIM DA EXCEÇÃO ---\n")
        return f"Ocorreu um erro ao exportar para Excel: {e}. Informe o usuário sobre o erro."

    """
    Executa uma consulta SQL SELECT, salva os resultados em um arquivo Excel (.xlsx) e retorna um link para download.
    Use esta ferramenta quando o usuário pedir para exportar dados, criar uma planilha ou um arquivo excel.
    O input deve ser uma consulta SQL SELECT válida.
    """

    print("\n--- [DEBUG] INICIANDO 'export_query_to_excel' ---")
    print(f"[DEBUG] Query recebida: {query}")
    print(f"[DEBUG] URI do Banco de Dados: {db_uri}")

    try:
        if not query.strip().upper().startswith("SELECT"):
            return "Erro: Apenas consultas SELECT podem ser exportadas para Excel."

        max_rows = int(os.getenv("MAX_EXPORT_ROWS", "100000"))
        
        row_count_df = pd.read_sql_query(f"SELECT COUNT(*) FROM ({query}) AS subquery", db_uri)
        total_rows = row_count_df.iloc[0, 0]

        if total_rows > max_rows:
            return (
                f"A consulta retornaria {total_rows} linhas, o que excede o limite de {max_rows}. "
                "Refine o filtro antes de exportar ou use a exportação para CSV."
            )
        
        df = pd.read_sql_query(query, db_uri)

        filename = f"resultado_{uuid.uuid4()}.xlsx"
        filepath = os.path.join("downloads", filename)
        os.makedirs("downloads", exist_ok=True)
        
        df.to_excel(filepath, index=False, engine='openpyxl')

        base_url = "http://127.0.0.1:8000"
        download_link = f"{base_url}/{filepath.replace(os.sep, '/')}"

        return f"Arquivo Excel gerado com sucesso. O usuário pode fazer o download aqui: {download_link}"
    except Exception as e:
        return f"Ocorreu um erro ao exportar para Excel: {e}. Informe o usuário sobre o erro."

@tool
def export_query_to_csv(query: str) -> str:
    """
    Executa uma consulta SQL SELECT e salva os resultados em um arquivo CSV (.csv), otimizando para grandes volumes.
    Use esta ferramenta quando o usuário pedir CSV ou quando a planilha Excel exceder o limite.
    O input deve ser uma consulta SQL SELECT válida.
    """
    try:
        if not query.strip().upper().startswith("SELECT"):
            return "Erro: Apenas consultas SELECT podem ser exportadas para CSV."

        os.makedirs("downloads", exist_ok=True)
        filename = f"resultado_{uuid.uuid4()}.csv"
        filepath = os.path.join("downloads", filename)

        # --- CORREÇÃO FINAL: Passar a URI do banco diretamente para o Pandas ---
        first_chunk = True
        for chunk in pd.read_sql_query(query, db_uri, chunksize=50000):
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
             df_empty = pd.read_sql_query(query + " WHERE 1=0", db_uri)
             df_empty.to_csv(filepath, index=False, sep=';', encoding='utf-8-sig')

        base_url = "http://127.0.0.1:8000"
        download_link = f"{base_url}/{filepath.replace(os.sep, '/')}"
        return f"Arquivo CSV gerado com sucesso. O usuário pode fazer o download aqui: {download_link}"
    except Exception as e:
        return f"Ocorreu um erro ao exportar para CSV: {e}. Informe o usuário sobre o erro."

# O restante do arquivo permanece o mesmo
sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)
sql_tools = sql_toolkit.get_tools()
all_tools = sql_tools + [nl_to_sql, refine_sql, export_query_to_excel, export_query_to_csv]

agent_executor = initialize_agent(
    tools=all_tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=12,
    early_stopping_method="generate",
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
        instruction = "Responda sempre em português do Brasil. "
        response = await agent_executor.ainvoke({"input": instruction + user_query})
        return {"success": True, "data": response.get("output")}
    except Exception as e:
        print(f"Ocorreu um erro inesperado no agente: {e}")
        return {"success": False, "error": "Ocorreu um erro ao processar sua pergunta."}