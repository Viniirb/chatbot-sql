# 🤖 Chatbot com Banco de Dados SQL

Este é um projeto de um chatbot full-stack que utiliza um modelo de linguagem (Google Gemini) para traduzir perguntas em linguagem natural para consultas SQL e interagir com um banco de dados.

## 🚀 Como Rodar o Projeto

### Backend (Python + FastAPI)

1. Navegue até a pasta `backend`: `cd backend`
2. Crie e ative um ambiente virtual: `python -m venv venv` e `.\venv\Scripts\activate`
3. Instale as dependências: `pip install -r requirements.txt`
4. Crie um arquivo `.env` baseado no exemplo e preencha com suas chaves.
5. Inicie o servidor: `uvicorn main:app --reload`

### Frontend (React + TypeScript + Vite)

1. Navegue até a pasta `frontend`: `cd frontend`
2. Instale as dependências: `npm install`
3. Inicie o servidor de desenvolvimento: `npm run dev`

---