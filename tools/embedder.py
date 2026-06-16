"""
tools/embedder.py — Semantic embedding for episodes and facts.

HOW EMBEDDINGS WORK:
  A sentence-transformer converts any text into a list of ~384 floats.
  Two semantically similar sentences produce SIMILAR lists.
  "Dogs love bones" and "Canines enjoy treats" → nearly identical vectors.

  We measure similarity using COSINE SIMILARITY:
    score = dot_product(A, B) / (|A| × |B|)
    1.0 = identical meaning, 0.0 = unrelated

WHY THIS BEATS "LAST 10 EPISODES":
  Last-10 is positional — it retrieves whatever was recent.
  Embeddings retrieve whatever is RELEVANT to the current question.
  If you talked about Python 20 days ago and ask about it today,
  the embedding search finds it. Last-10 would miss it entirely.

MODEL: all-MiniLM-L6-v2
  384 dimensions, ~80MB, runs on CPU in <100ms. Perfect for local use.
  Install: pip install sentence-transformers
"""

import json
import math
from typing import Optional


# Lazy load — only import when first needed (slow to import)
_model = None

def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        # Downloads once (~80MB), then cached locally
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed(text: str) -> str:
    """
    Embed a piece of text. Returns a JSON string of floats.
    We store as JSON in SQLite because SQLite has no vector type.
    e.g. "[0.123, -0.456, 0.789, ...]"
    """
    model = _get_model()
    vector = model.encode(text).tolist()   # numpy array → plain Python list
    return json.dumps(vector)


def cosine_similarity(a: str, b: str) -> float:
    """
    Compute cosine similarity between two JSON-encoded embedding strings.
    Returns float in [-1, 1]. Higher = more similar.
    """
    va = json.loads(a)
    vb = json.loads(b)

    # Dot product
    dot = sum(x * y for x, y in zip(va, vb))

    # Magnitudes
    mag_a = math.sqrt(sum(x * x for x in va))
    mag_b = math.sqrt(sum(x * x for x in vb))

    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def find_relevant(query: str, candidates: list, text_field: str,
                  embedding_field: str = "embedding", top_k: int = 5) -> list:
    """
    Given a query string and a list of Pydantic models (or dicts),
    return the top_k most semantically similar ones.

    HOW IT WORKS:
      1. Embed the query text.
      2. For each candidate that has a stored embedding, compute cosine similarity.
      3. Sort by similarity descending, return top_k.

    candidates:      list of Pydantic model instances (Episode, Fact, etc.)
    text_field:      fallback — if no embedding, embed the text_field value on-the-fly
    embedding_field: the field name storing the JSON embedding string
    """
    query_emb = embed(query)
    scored = []

    for item in candidates:
        # Support both Pydantic models (item.field) and dicts (item["field"])
        emb = getattr(item, embedding_field, None) if hasattr(item, embedding_field) else item.get(embedding_field)

        if not emb:
            # No stored embedding — embed the text field on the fly (slower)
            text = getattr(item, text_field, "") if hasattr(item, text_field) else item.get(text_field, "")
            if not text:
                continue
            emb = embed(text)

        score = cosine_similarity(query_emb, emb)
        scored.append((score, item))

    # Sort by similarity, highest first
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_k]]
