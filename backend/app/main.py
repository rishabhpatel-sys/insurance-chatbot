import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create app and include routers
app = FastAPI(title="Insurance Chatbot (Demo)")

# Allow CORS for local demo frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include chat routes
from backend.app.routes.chat_routes import router as chat_router
app.include_router(chat_router)
