from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
import html

from backend.app.controllers.chat_controller import upload_document, chat, chat_stream, sse_chat, get_source_html
from backend.app.models.schemas import UploadRequest, ChatRequest
from backend.app.services.ingest_service import get_qdrant_client, QDRANT_COLLECTION

router = APIRouter()


@router.post("/upload-document")
async def upload_document_route(req: UploadRequest):
    return upload_document(req)


@router.post("/chat")
async def chat_route(req: ChatRequest):
    return chat(req)


@router.post('/chat-stream')
async def chat_stream_route(req: ChatRequest):
    gen = chat_stream(req)
    return StreamingResponse(gen, media_type='text/event-stream')


@router.get('/sse')
async def sse_route(message: str = Query(...)):
    gen = sse_chat(message)
    return StreamingResponse(gen, media_type='text/event-stream')


@router.get('/source')
async def get_source(title: str, chunk_index: int):
    # Use ingest service to get client
    q_client = get_qdrant_client()
    # Simple scroll to find text
    resp = q_client.scroll(collection_name=QDRANT_COLLECTION, limit=50)
    points = getattr(resp, 'result', None) or resp[0] if isinstance(resp, tuple) else resp
    found_text = None
    source_path = None
    if points:
        for p in points:
            payload = getattr(p, 'payload', {}) or {}
            if payload.get('title') == title and int(payload.get('chunk_index', -1)) == int(chunk_index):
                found_text = payload.get('text', '')
                source_path = payload.get('source')
                break
    if not found_text:
        return HTMLResponse(content=f"<h1>Not found</h1><p>No snippet for {html.escape(title)} chunk {chunk_index}</p>", status_code=404)

    body = f"<html><head><meta charset=\"utf-8\"><title>{html.escape(title)} - chunk {chunk_index}</title></head><body style=\"font-family:Arial,sans-serif;margin:20px;\">"
    body += f"<h1>{html.escape(title)} (chunk {chunk_index})</h1>"
    if source_path:
        body += f"<p><em>Source file: {html.escape(source_path)}</em></p>"
    body += f"<pre style=\"white-space:pre-wrap;line-height:1.4;\">{html.escape(found_text)}</pre>"
    body += "</body></html>"
    return HTMLResponse(content=body, status_code=200)


@router.get('/health')
async def health_route():
    return {"status": "ok"}
