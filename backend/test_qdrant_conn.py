from dotenv import load_dotenv
load_dotenv()
import os, traceback
from qdrant_client import QdrantClient

print("Using QDRANT_URL:", os.getenv("QDRANT_URL"))
try:
    client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"), timeout=10)
    print("Client created. Requesting collections...")
    info = client.get_collections()
    print("Collections result:", info)
except Exception:
    print("EXCEPTION creating QdrantClient:")
    traceback.print_exc()
