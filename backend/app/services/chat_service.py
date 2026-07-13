import os
import json
from typing import List, Dict
from openai import OpenAI
from langchain.embeddings import init_embeddings

from backend.app.services.ingest_service import get_qdrant_client, QDRANT_COLLECTION

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
    q_client = get_qdrant_client()
    embedding_model = os.environ.get("OPENAI_EMBEDDING_MODEL", "openai:text-embedding-3-small")
    embedder = init_embeddings(embedding_model)

    query_vector = embedder.embed_query(query)
    resp = q_client.query_points(collection_name=QDRANT_COLLECTION, query=query_vector, limit=k, with_payload=True)

    context_items = []
    points = getattr(resp, 'points', None) or getattr(resp, 'result', None) or []
    for point in (points or [])[:k]:
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
    contexts = retrieve_context(user_message, k=6)
    prompt = build_prompt(user_message, contexts)

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

    answer = ''
    choices = getattr(resp, 'choices', None) or (resp.get('choices') if isinstance(resp, dict) else None)
    if choices:
        first = choices[0]
        if hasattr(first, 'message'):
            msg = first.message
            answer = getattr(msg, 'content', None) or (msg.get('content') if isinstance(msg, dict) else '') or ''
        else:
            answer = first.get('message', {}).get('content', '')

    sources = []
    for c in contexts[:3]:
        m = c.get("metadata", {})
        sources.append({"title": m.get("title"), "chunk_index": m.get("chunk_index")})

    return {"answer": answer, "sources": sources}


def stream_answer(user_message: str):
    contexts = retrieve_context(user_message, k=6)
    prompt = build_prompt(user_message, contexts)

    openai_api_key = os.environ.get('OPENAI_API_KEY')
    if not openai_api_key:
        yield f"event: error\ndata: OPENAI_API_KEY not set\n\n"
        return
    client = OpenAI(api_key=openai_api_key)
    model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

    try:
        with client.chat.completions.stream(
            model=model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            temperature=0.0,
        ) as stream:
            sent_text = ""
            for event in stream:
                data = None
                try:
                    if hasattr(event, 'delta') and getattr(event, 'delta'):
                        data = getattr(event, 'delta')
                    elif hasattr(event, 'content') and getattr(event, 'content'):
                        data = getattr(event, 'content')
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
                    s = str(data)
                    new_part = s
                    if s.startswith(sent_text):
                        new_part = s[len(sent_text):]
                    elif sent_text and sent_text.endswith(s):
                        new_part = ""

                    if new_part:
                        for line in new_part.splitlines():
                            yield f"data: {line}\n"
                        yield "\n"
                        sent_text += new_part
    except Exception as e:
        yield f"event: error\ndata: {str(e)}\n\n"
    finally:
        sources = []
        for c in contexts[:3]:
            m = c.get("metadata", {})
            sources.append({"title": m.get("title"), "chunk_index": m.get("chunk_index")})
        yield f"event: sources\ndata: {json.dumps(sources)}\n\n"
