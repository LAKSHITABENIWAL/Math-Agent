# backend/db_utils.py
from dotenv import load_dotenv
load_dotenv()

import os
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest_models

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)

print("db_utils: QDRANT_URL =", QDRANT_URL)

_qdrant_client: Optional[QdrantClient] = None

def get_qdrant_client() -> QdrantClient:
    """Create QdrantClient lazily and return it. Use a short timeout to fail fast if network blocks."""
    global _qdrant_client
    if _qdrant_client is None:
        try:
            # set a small timeout (seconds) so client creation / initial calls don't hang indefinitely
            # QdrantClient accepts timeout kwarg which is forwarded to httpx
            _qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=10)
        except Exception as e:
            print("Error creating QdrantClient:", repr(e))
            raise
    return _qdrant_client


def ensure_collection(collection_name="math_kb", vector_size=384, recreate=False):
    """
    Create or optionally recreate the collection.
    Set recreate=True only for dev (will remove existing data).
    """
    client = get_qdrant_client()
    try:
        existing = client.get_collections()
        names = [c.name for c in getattr(existing, "collections", [])]
        if collection_name in names:
            if recreate:
                print(f"Recreating collection {collection_name} (dev only).")
                client.recreate_collection(
                    collection_name=collection_name,
                    vectors_config=rest_models.VectorParams(size=vector_size, distance=rest_models.Distance.COSINE),
                )
            else:
                print(f"Collection {collection_name} already exists.")
        else:
            print(f"Creating collection {collection_name}.")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=rest_models.VectorParams(size=vector_size, distance=rest_models.Distance.COSINE),
            )
    except Exception as e:
        print("Qdrant ensure_collection error:", repr(e))
        raise

def upsert_points(collection_name, points):
    client = get_qdrant_client()
    from qdrant_client.models import PointStruct
    point_structs = [PointStruct(id=p["id"], vector=p["vector"], payload=p.get("payload", {})) for p in points]
    client.upsert(collection_name=collection_name, points=point_structs)

def search_vectors(collection_name, query_vector, top=3):
    client = get_qdrant_client()
    try:
        hits = client.search(collection_name=collection_name, query_vector=query_vector, limit=top)
    except Exception as e:
        print("Qdrant search error:", repr(e))
        return []
    res = []
    for h in hits:
        res.append({"id": h.id, "score": h.score, "payload": h.payload})
    return res
