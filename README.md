Insurance Chatbot (RAG) Demo

This repository contains a minimal demo of an insurance chatbot using:

- FastAPI (Python) backend
- LangChain for RAG orchestration
- Qdrant as vector DB (docker-compose included)
- OpenAI embeddings & LLM
- A tiny static frontend to demo the chat UI

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

Notes

- The backend expects OPENAI_API_KEY in env. The ingestion endpoint accepts JSON {"title": "...", "content": "..."} for demo simplicity.
- For production use, secure the endpoints, add authentication, use managed Qdrant or provision storage, and follow the system design in the project plan.

Files of interest

- backend/app/main.py - FastAPI application and endpoints
- backend/app/ingest.py - ingestion and indexing helpers
- backend/app/chat.py - chat endpoint and RAG logic
- docker-compose.yml - starts Qdrant for local dev
- frontend/index.html - minimal chat UI that talks to backend

Next steps

- Upload real policy/claim documents via /upload-document
- Test chat by sending queries to /chat
