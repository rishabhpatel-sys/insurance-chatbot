Insurance Chatbot (RAG) Demo

This repository contains a minimal demo of an insurance chatbot using:

- FastAPI (Python) backend
- LangChain for RAG orchestration
- Qdrant as vector DB (docker-compose included)
- OpenAI embeddings & LLM
- A tiny static frontend to demo the chat UI
- A Next.js streaming demo with document upload support

This is a demo intended for 5-10 users and ~20 documents.

Prerequisites

- Docker & docker-compose
- Python 3.10+
- OpenAI API key

Quick start (dev)

1. Copy .env.example to .env and set OPENAI_API_KEY and optionally QDRANT url/credentials.
   cp .env.example .env
2. Start Qdrant:
   docker-compose up -d
3. Create a virtualenv and install backend deps:
   python -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
4. Start the backend:
   uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
5. Open frontend/index.html in your browser (or serve it) and point the API host to http://localhost:8000
6. (Optional) Start the Next.js frontend for the streaming demo and upload page:
   cd frontend/next-app && npm install && npm run dev
   Then open http://localhost:3000 and visit /upload to add documents.

Notes

- The backend expects OPENAI_API_KEY in env. The ingestion endpoint accepts JSON {"title": "...", "content": "..."} for demo simplicity.
- Use the Next.js app at /upload to upload .txt or .md documents and improve the RAG context.

Files of interest

- backend/app/main.py - FastAPI application and endpoints
- backend/app/services/ingest_service.py - ingestion and indexing helpers
- backend/app/services/chat_service.py - chat endpoint and RAG logic
- backend/app/routes/chat_routes.py - API routes
- frontend/index.html - minimal chat UI that talks to backend
- frontend/next-app/pages/index.js - Next.js streaming chat UI
- frontend/next-app/pages/upload.js - Next.js document upload page
- docker-compose.yml - starts Qdrant for local dev

Next steps

- Upload real policy/claim documents via /upload
- Test chat by sending queries to /chat
