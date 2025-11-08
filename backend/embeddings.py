# backend/embeddings.py
from sentence_transformers import SentenceTransformer
MODEL_NAME = "all-MiniLM-L6-v2"
_model = None

def _load():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def embed_text(text):
    model = _load()
    vec = model.encode(text, convert_to_numpy=True)
    return vec.tolist()
