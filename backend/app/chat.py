import os
from typing import List, Dict
import json
from openai import OpenAI

from langchain.embeddings import init_embeddings
from qdrant_client import QdrantClient

# Import helper to get qdrant client
from backend.app.ingest import get_qdrant_client, QDRANT_COLLECTION

SYSTEM_PROMPT = """
You are an insurance assistant. Answer user questions concisely and accurately using only the provided context. "Do not" invent facts. If the answer is not contained in the context, say you don't know and suggest next steps (contact agent or upload policy number).
"""

PROMPT_TMPL = """
{system}

Context:
{context}

User: {user_message}

Assistant:"""


def retrieve_context(query: str, k: int = 6) -> List[Dict]:
    # Create clients
    q_client = get_qdrant_client()
    embedding_model = os.environ.get("OPENAI_EMBEDDING_MODEL", "openai:text-embedding-3-small")
    embedder = init_embeddings(embedding_model)

    # Embed query
    query_vector = embedder.embed_query(query)

    # Query Qdrant directly
    resp = q_client.query_points(collection_name=QDRANT_COLLECTION, query=query_vector, limit=k, with_payload=True)

    # Parse results (QueryResponse.points)
    context_items = []
    points = getattr(resp, 'points', None) or getattr(resp, 'result', None) or []
    for point in (points or [])[:k]:
        # point may be ScoredPoint or Record
        payload = getattr(point, 'payload', None) or (point.get('payload') if isinstance(point, dict) else {}) or {}
        score = getattr(point, 'score', None) or (point.get('score') if isinstance(point, dict) else None)
        context_items.append({"text": payload.get('text', ''), "score": float(score) if score is not None else None, "metadata": payload})

    return context_items


def build_prompt(user_message: str, contexts: List[Dict]) -> str:
    ctx_texts = []
    for i, c in enumerate(contexts):
        title = c.get("metadata", {}).get("title", f"source_{i}")
        chunk_idx = c.get("metadata", {}).get("chunk_index")
        ctx_texts.append(f"[{title} | chunk={chunk_idx}] {c.get('text')}")
    context_block = "\n---\n".join(ctx_texts) if ctx_texts else "No context available."

    return PROMPT_TMPL.format(system=SYSTEM_PROMPT, context=context_block, user_message=user_message)


def answer_query(user_message: str) -> Dict:
    # Retrieve
    contexts = retrieve_context(user_message, k=6)
    prompt = build_prompt(user_message, contexts)

    # Call OpenAI via new SDK
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError('OPENAI_API_KEY not set')
    client = OpenAI(api_key=openai_api_key)
    model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=512,
    )

    # Extract text
    answer = ''
    choices = getattr(resp, 'choices', None) or (resp.get('choices') if isinstance(resp, dict) else None)
    if choices:
        first = choices[0]
        # first may be an object with .message or a dict
        if hasattr(first, 'message'):
            msg = first.message
            answer = getattr(msg, 'content', None) or (msg.get('content') if isinstance(msg, dict) else '') or ''
        else:
            answer = first.get('message', {}).get('content', '')

    # Build sources
    sources = []
    for c in contexts[:3]:
        m = c.get("metadata", {})
        sources.append({"title": m.get("title"), "chunk_index": m.get("chunk_index")})

    return {"answer": answer, "sources": sources}


# Streaming version
def stream_answer(user_message: str):
    """Generator that yields SSE-formatted chunks for streaming responses."""
    contexts = retrieve_context(user_message, k=6)
    prompt = build_prompt(user_message, contexts)

    openai_api_key = os.environ.get('OPENAI_API_KEY')
    if not openai_api_key:
        yield f"event: error\ndata: OPENAI_API_KEY not set\n\n"
        return
    client = OpenAI(api_key=openai_api_key)
    model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

    try:
        # Use context manager to get stream manager which is iterable
        with client.chat.completions.stream(
            model=model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            temperature=0.0,
        ) as stream:
            sent_text = ""  # track what has been sent so we avoid sending duplicates (full content events)
            for event in stream:
                data = None
                try:
                    # Prefer incremental ContentDeltaEvent (attribute 'delta')
                    if hasattr(event, 'delta') and getattr(event, 'delta'):
                        data = getattr(event, 'delta')
                    # Some events include full content in 'content' when finished; treat carefully
                    elif hasattr(event, 'content') and getattr(event, 'content'):
                        # full_content = getattr(event, 'content')
                        data = getattr(event, 'content')
                    # dict-like fallback
                    elif isinstance(event, dict):
                        if 'choices' in event:
                            first = event['choices'][0]
                            delta = first.get('delta')
                            if delta:
                                data = delta.get('content') or delta.get('text')
                            else:
                                data = first.get('message', {}).get('content')
                    if not data and hasattr(event, 'get'):
                        data = event.get('text') or event.get('content')
                except Exception:
                    data = str(event)

                if data:
                    # Determine the new part to send to avoid duplicates when final full content arrives
                    s = str(data)
                    new_part = s
                    if s.startswith(sent_text):
                        # event contains cumulative content; send only the suffix
                        new_part = s[len(sent_text):]
                    elif sent_text and sent_text.endswith(s):
                        # already ended with this fragment -> skip
                        new_part = ""
                    # else assume s is an incremental fragment (append as-is)

                    if new_part:
                        # yield each line as SSE data event
                        for line in new_part.splitlines():
                            yield f"data: {line}\n"
                        yield "\n"
                        sent_text += new_part
    except Exception as e:
        yield f"event: error\ndata: {str(e)}\n\n"
    finally:
        # send sources as final event
        sources = []
        for c in contexts[:3]:
            m = c.get("metadata", {})
            sources.append({"title": m.get("title"), "chunk_index": m.get("chunk_index")})
        yield f"event: sources\ndata: {json.dumps(sources)}\n\n"
