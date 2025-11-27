"""
Search utilities for the RAG backend.
Encapsulates embedding, Qdrant upload, query, and an in-memory fallback search.
"""
from typing import List, Dict, Optional, Tuple
import numpy as np
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

# Initialize the default model once and re-use it (SentenceTransformers is thread-safe for inference)
MODEL = SentenceTransformer("all-MiniLM-L6-v2")


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Return embedding vectors for a list of texts."""
    vectors = MODEL.encode(texts, convert_to_numpy=True)
    return [v.tolist() for v in vectors]


def prepare_facts_with_vectors(facts: List[Dict]) -> List[Dict]:
    """Ensure each fact has an embedding vector stored under 'vector' key."""
    for fact in facts:
        if "vector" not in fact:
            fact["vector"] = MODEL.encode(fact["text"]).tolist()
    return facts


def create_or_recreate_collection(client: QdrantClient, collection_name: str, facts: List[Dict], distance: str = "Cosine") -> None:
    """Create (or recreate) a Qdrant collection and upload the facts with vectors.

    Parameters:
    - client: an initialized QdrantClient
    - collection_name: name of collection
    - facts: facts already prepared with vectors
    - distance: distance metric for Qdrant
    """
    if not facts:
        logger.warning("No facts to upload to Qdrant")
        return

    vector_size = len(facts[0]["vector"])

    try:
        client.recreate_collection(collection_name=collection_name, vectors_config={"size": vector_size, "distance": distance})
        vectors = [fact["vector"] for fact in facts]
        payloads = [{"text": fact["text"]} for fact in facts]
        ids = [fact["id"] for fact in facts]
        client.upload_collection(collection_name=collection_name, vectors=vectors, payload=payloads, ids=ids, wait=True)
        logger.info("Facts uploaded to Qdrant collection %s", collection_name)
    except Exception:
        logger.exception("Failed to create or upload to Qdrant collection")
        raise


def query_qdrant(client: QdrantClient, collection_name: str, question_vec: List[float], limit: int = 1) -> Optional[Dict]:
    """Query Qdrant using a precomputed question vector and return the best payload.
    Returns None on error or no results.
    """
    try:
        res = client.query_points(collection_name=collection_name, query=question_vec, with_payload=True, limit=limit)
        if res is None or not getattr(res, "result", None) or len(res.result) == 0:
            return None
        top = res.result[0]
        payload = top.payload if hasattr(top, "payload") else None
        if isinstance(payload, dict) and "text" in payload:
            return {"text": payload["text"], "id": getattr(top, "id", None), "score": getattr(top, "score", None)}
        return None
    except Exception:
        logger.exception("Error while querying Qdrant")
        return None


def local_similarity_search(facts: List[Dict], question_vec: List[float], threshold: float = 0.45) -> Optional[Dict]:
    """Perform a cosine-similarity search among in-memory fact vectors.
    Returns the best match (fact dict) if above threshold, else None.
    """
    try:
        # Ensure fact vectors exist; compute if missing
        for fact in facts:
            if "vector" not in fact:
                fact["vector"] = MODEL.encode(fact["text"]).tolist()
        vectors = np.array([fact["vector"] for fact in facts])
        q = np.array(question_vec)
        denom = np.linalg.norm(q) * np.linalg.norm(vectors, axis=1)
        # Avoid division by zero
        denom[denom == 0] = 1e-12
        sims = (vectors @ q) / denom
        best_idx = int(np.argmax(sims))
        best_score = float(sims[best_idx])
        best_fact = facts[best_idx]
        if best_score >= threshold:
            return {"text": best_fact["text"], "id": best_fact.get("id"), "score": best_score}
        return None
    except Exception:
        logger.exception("Local similarity search failed")
        return None
