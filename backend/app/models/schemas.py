from pydantic import BaseModel
from typing import Optional


class UploadRequest(BaseModel):
    title: str
    content: str
    metadata: Optional[dict] = None


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    message: str
