import os
from dotenv import load_dotenv
from sqlalchemy.exc import OperationalError
from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.agent_toolkits import create_sql_agent

load_dotenv()

db_uri = os.getenv("DATABASE_URL")
google_api_key = os.getenv("GOOGLE_API_KEY")

db = SQLDatabase.from_uri(
    db_uri,
    lazy_table_reflection=True
)

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=google_api_key, convert_system_message_to_human=True)

sql_agent_executor = create_sql_agent(llm, db=db, agent_type="openai-tools", verbose=True)

def get_response(user_query: str):
    try:
        response = sql_agent_executor.invoke({"input": user_query})
        return {"success": True, "data": response.get("output")}

    except OperationalError as oe:
        print(f"ERRO DE CONEXÃO COM O BANCO DE DADOS: {oe}")
        return {"success": False, "error": "Não foi possível se comunicar com o banco de dados no momento."}
        
    except Exception as e:
        print(f"Ocorreu um erro inesperado no agente: {e}")
        return {"success": False, "error": "Ocorreu um erro ao processar sua pergunta."}