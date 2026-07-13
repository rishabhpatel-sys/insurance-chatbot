import os
from typing import List

# langchain text splitters are provided by the langchain_text_splitters package
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams
import uuid

QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "insurance_demo")


def get_qdrant_client():
    host = os.environ.get("QDRANT_HOST", "localhost")
    port = int(os.environ.get("QDRANT_PORT", 6333))
    api_key = os.environ.get("QDRANT_API_KEY") or None
    return QdrantClient(url=f"http://{host}:{port}", api_key=api_key)


def chunk_text(text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=200,
    )
    return splitter.split_text(text)


def ingest_document(title: str, content: str, metadata: dict = None):
    """Ingests a document into Qdrant using OpenAI embeddings via LangChain.

    Inputs:
    - title: human readable title
    - content: full text content
    - metadata: optional metadata dict stored with each chunk

    Returns: number of chunks indexed
    """
    metadata = metadata or {}
    client = get_qdrant_client()

    texts = chunk_text(content)

    # Initialize embeddings via LangChain init_embeddings helper
    from langchain.embeddings import init_embeddings
    embedding_model = os.environ.get("OPENAI_EMBEDDING_MODEL", "openai:text-embedding-3-small")
    embedder = init_embeddings(embedding_model)

    # Compute embeddings for each chunk
    vectors = embedder.embed_documents(texts)
    if not vectors:
        return 0
    vector_size = len(vectors[0])

    # Ensure collection exists
    if not client.get_collections() or not client.collection_exists(QDRANT_COLLECTION):
        try:
            client.create_collection(collection_name=QDRANT_COLLECTION, vectors_config={"size": vector_size, "distance": "Cosine"})
        except Exception:
            # If collection exists concurrently, ignore
            pass

    # Prepare points for upsert
    points = []
    for i, (text_chunk, vector) in enumerate(zip(texts, vectors)):
        pid = str(uuid.uuid4())
        payload = {**metadata, "title": title, "chunk_index": i, "text": text_chunk}
        points.append({"id": pid, "vector": vector, "payload": payload})

    # Upsert into Qdrant
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    return len(texts)
