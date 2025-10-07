"""
Script de teste para verificar a configuração do Chatbot SQL
"""
import os
import asyncio
import warnings
from dotenv import load_dotenv

# Suprimir warnings específicos do Pydantic
warnings.filterwarnings("ignore", message=".*validate_default.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*UnsupportedFieldAttributeWarning.*")

# Carrega variáveis de ambiente
load_dotenv()

async def test_configuration():
    """Testa se todas as configurações estão corretas."""
    print("🔍 Testando configurações do Chatbot SQL...")
    
    # 1. Verificar variáveis de ambiente
    print("\n1️⃣ Verificando variáveis de ambiente:")
    
    db_uri = os.getenv("DATABASE_URL")
    google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    if not db_uri:
        print("❌ DATABASE_URL não definida")
        return False
    else:
        print(f"✅ DATABASE_URL: {db_uri[:20]}...")
    
    if not google_api_key:
        print("❌ GOOGLE_API_KEY ou GEMINI_API_KEY não definida")
        return False
    else:
        print(f"✅ API Key encontrada: {google_api_key[:10]}...")
    
    # 2. Testar imports
    print("\n2️⃣ Testando imports:")
    
    try:
        from llama_index.core import Settings
        from llama_index.llms.google_genai import GoogleGenAI
        from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
        print("✅ LlamaIndex imports OK")
    except ImportError as e:
        print(f"❌ Erro nos imports LlamaIndex: {e}")
        return False
    
    try:
        import google.generativeai as genai
        print("✅ Google GenerativeAI import OK")
    except ImportError as e:
        print(f"❌ Erro no import Google AI: {e}")
        return False
    
    try:
        from sqlalchemy import create_engine, text
        print("✅ SQLAlchemy import OK")
    except ImportError as e:
        print(f"❌ Erro no import SQLAlchemy: {e}")
        return False
    
    # 3. Testar LLM
    print("\n3️⃣ Testando LLM Gemini:")
    
    try:
        llm = GoogleGenAI(
            model_name="models/gemini-2.5-flash",
            api_key=google_api_key,
            temperature=0.1
        )
        
        response = await llm.acomplete("Diga apenas 'OK' se você está funcionando")
        print(f"✅ Gemini LLM resposta: {response.text.strip()}")
        
    except Exception as e:
        print(f"❌ Erro no teste do Gemini: {e}")
        return False
    
    # 4. Testar conexão com banco
    print("\n4️⃣ Testando conexão com banco:")
    
    try:
        if 'mssql' in db_uri:
            engine = create_engine(db_uri, fast_executemany=True, pool_pre_ping=True)
        else:
            engine = create_engine(db_uri, pool_pre_ping=True)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            if test_value == 1:
                print("✅ Conexão com banco de dados OK")
            else:
                print("❌ Conexão retornou valor inesperado")
                return False
                
    except Exception as e:
        print(f"❌ Erro na conexão com banco: {e}")
        return False
    
    # 5. Testar agente (importação)
    print("\n5️⃣ Testando importação do agente:")
    
    try:
        from agent import chat_agent, get_response
        if chat_agent is not None:
            print("✅ Agente inicializado com sucesso")
        else:
            print("❌ Agente não foi inicializado")
            return False
            
    except Exception as e:
        print(f"❌ Erro na importação do agente: {e}")
        return False
    
    print("\n🎉 Todos os testes passaram! O sistema está configurado corretamente.")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_configuration())
    if not success:
        print("\n❌ Alguns testes falharam. Verifique a configuração.")
        exit(1)
    else:
        print("\n✅ Sistema pronto para uso!")