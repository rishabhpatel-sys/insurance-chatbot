from fastapi import HTTPException
from backend.app.models.schemas import UploadRequest, ChatRequest
from backend.app.services.ingest_service import ingest_document, parse_uploaded_file
from backend.app.services.chat_service import answer_query, stream_answer


def upload_document(req: UploadRequest):
    try:
        num = ingest_document(req.title, req.content, req.metadata or {})
        return {"status": "ok", "chunks_indexed": num}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def upload_document_file(title: str | None = None, content: str | None = None, source: str | None = None, file=None):
    try:
        if file is not None:
            content = parse_uploaded_file(file)
            if not title:
                title = file.filename.rsplit('.', 1)[0] if file.filename else 'uploaded_document'
            source = source or file.filename

        if not title or not content:
            raise HTTPException(status_code=400, detail='Please provide a title and content or upload a supported file.')

        metadata = {"source": source} if source else {}
        num = ingest_document(title, content, metadata)
        return {"status": "ok", "chunks_indexed": num}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def chat(req: ChatRequest):
    try:
        out = answer_query(req.message)
        return {"status": "ok", "reply": out["answer"], "sources": out["sources"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def chat_stream(req: ChatRequest):
    try:
        gen = stream_answer(req.message)
        return gen
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def sse_chat(message: str):
    try:
        gen = stream_answer(message)
        return gen
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_source_html(title: str, chunk_index: int, get_qdrant_client):
    client = get_qdrant_client()
    resp = client.scroll(collection_name=client._collection_name or 'insurance_demo', limit=50)  # fallback handled in route
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
        raise HTTPException(status_code=404, detail=f"No snippet for {title} chunk {chunk_index}")

    # return dict for the route to build HTML
    return {"title": title, "chunk_index": chunk_index, "text": found_text, "source": source_path}
