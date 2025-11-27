"""
A minimal FastAPI service which serves as a RAG (Retrieval-Augmented Generation) backend.

Features:
- Stores a small dataset of textual facts in a Qdrant vector database.
- Uses SentenceTransformers to create embeddings for facts and queries.
- Provides a POST /query/ endpoint that accepts a user question and returns the nearest fact.

Setup:
- Run Qdrant locally (example Docker below) or point to a remote Qdrant instance with env vars.
- Install Python packages in your virtual environment:
    pip install -r requirements.txt

Run the server:
    uvicorn main:app --reload

Docker (Quick Qdrant start):
    docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant

"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from qdrant_client import QdrantClient
import numpy as np
from sentence_transformers import SentenceTransformer
from backend import search as search_mod
from backend import classifier as classifier_mod
from backend import llm as llm_mod
import requests

import os
import logging
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Logging for clarity
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic model for request body
class QueryRequest(BaseModel):
    question: str

# Create a FastAPI app
app = FastAPI(title="Simple RAG with Qdrant & SentenceTransformers")

# Load SentenceTransformers model for embeddings
# Note: This downloads the model on first run (internet required)
logger.info("Loading sentence-transformers model (all-MiniLM-L6-v2). This may take a moment...")
model = SentenceTransformer("all-MiniLM-L6-v2")
logger.info("Model loaded.")

# Sample facts that will be stored in the vector DB
FACTS = [
    {"id": 1, "text": "Om has 2 apples"},
    {"id": 2, "text": "Pavan has 82 apples"},
    {"id": 3, "text": "Sahil has 3 apples"},
]

# Qdrant configuration via environment variables (fallback to localhost)
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", 6333))
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "apples")
QDRANT_DISTANCE = os.environ.get("QDRANT_DISTANCE", "Cosine")  # or 'Dot' or 'Euclid'
FALLBACK_TO_LLM_FOR_LEGAL = os.environ.get("FALLBACK_TO_LLM_FOR_LEGAL", "false").lower() == "true"

# Create a Qdrant client (HTTP by default)
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
# Flag whether Qdrant is available. If not, fallback to local in-memory search.
qdrant_available = True

# Allow cross-origin requests from the frontend developer server (default: http://localhost:3000)
frontend_origin = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    global qdrant_available
    """Prepare the Qdrant collection: create and upload points with embeddings.

    The collection is recreated on startup for simplicity.
    In production, you may want to persist and update instead of recreating.
    """
    try:
        # Prepare fact vectors using the shared helper in search_mod
        search_mod.prepare_facts_with_vectors(FACTS)

        vector_size = len(FACTS[0]["vector"])

        # Recreate the collection (drop if exists then create)
        logger.info(
            f"Creating Qdrant collection: {QDRANT_COLLECTION} (size={vector_size}, distance={QDRANT_DISTANCE})"
        )
        client.recreate_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config={"size": vector_size, "distance": QDRANT_DISTANCE},
        )

        # Prepare separate lists for upload_collection (vectors, payload, ids)
        vectors = [fact["vector"] for fact in FACTS]
        payloads = [{"text": fact["text"]} for fact in FACTS]
        ids = [fact["id"] for fact in FACTS]

        logger.info("Uploading facts to Qdrant collection")
        client.upload_collection(
            collection_name=QDRANT_COLLECTION,
            vectors=vectors,
            payload=payloads,
            ids=ids,
            wait=True,
        )
        logger.info("Upload complete.")

    except Exception as e:
        logger.exception(
            "Failed to create/upload collection to Qdrant. Ensure Qdrant is reachable and running. Falling back to in-memory search."
        )
        qdrant_available = False


@app.post("/query/")
async def query_facts(req: QueryRequest):
    global qdrant_available
    """
    Accept a JSON body with 'question' string, embed it, search in Qdrant, and return the best match.

    Example request body:
        { "question": "How many apples does Pavan have?" }

    Returns a JSON response with the matching 'answer' or a polite fallback message.
    """
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must be a non-empty string")

    # Embed user question
    question_vec = model.encode(question).tolist()

    # Compute a local similarity check first; if there's a strong dataset match, return it regardless of intent
    local_best = search_mod.local_similarity_search(FACTS, question_vec, threshold=0.7)
    if local_best:
        return {"answer": local_best["text"], "source": f"in-memory:fact-id={local_best.get('id')}", "mode": "retrieved"}

    # Query qdrant collection for nearest point with payload, or fallback to local search
    results = None
    if classifier_mod.is_legal_question(question):
        # Legal question -> try the vector DB or fallback
        if qdrant_available:
            # use standardized query helper if available
            results = search_mod.query_qdrant(client, QDRANT_COLLECTION, question_vec, limit=1)
            if results:
                return {"answer": results["text"], "source": f"qdrant:{QDRANT_COLLECTION} id={results.get('id')}", "mode": "legal"}
            # If results is None, fall through to in-memory search

        # Fallback: compute cosine similarity with in-memory FACTS embeddings
        best = search_mod.local_similarity_search(FACTS, question_vec)
        if best:
            return {"answer": best["text"], "source": f"in-memory:fact-id={best.get('id')}", "mode": "legal"}
        if FALLBACK_TO_LLM_FOR_LEGAL:
            llm_res = llm_mod.call_llm(question, provider=os.environ.get("LLM_PROVIDER", "gemini"))
            # Provide the LLM response but mark source as llm and mode as legal-llm
            return {"answer": llm_res.get("answer"), "source": llm_res.get("source"), "mode": "legal-llm"}
        return {"answer": "No relevant info found.", "source": "none", "mode": "legal"}
    else:
        # Non-legal question -> call LLM provider
        llm_res = llm_mod.call_llm(question, provider=os.environ.get("LLM_PROVIDER", "gemini"))
        return {"answer": llm_res.get("answer"), "source": llm_res.get("source"), "mode": llm_res.get("mode")}

    # Qdrant returns QueryResponse — single object when using query_points for a vector
    # If there are no results or score below a reasonable threshold, return polite fallback
    if results is None or not getattr(results, "result", None) or len(results.result) == 0:
        return {"answer": "No relevant info found.", "source": "none", "mode": "legal"}

    # Extract top result payload text
    top = results.result[0]
    payload = top.payload if hasattr(top, "payload") else None
    text = payload.get("text") if isinstance(payload, dict) else None

    if not text:
        return {"answer": "No relevant info found.", "source": "none", "mode": "legal"}

    return {"answer": text, "source": f"qdrant:{QDRANT_COLLECTION} id={top.id}", "mode": "legal"}


# Basic root endpoint to confirm server is up
@app.get("/")
async def root():
    return {"status": "ok", "collection": QDRANT_COLLECTION}


@app.get("/health")
async def health():
    # Return whether the backend sees GEMINI configuration and Qdrant availability
    return {
        "status": "ok",
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "gemini_model": os.environ.get("GEMINI_MODEL", "<not-set>"),
        "qdrant_available": qdrant_available,
    }


@app.get("/diagnostics")
async def diagnostics():
    """Provide non-secret diagnostics for local development.

    Returns a JSON object with booleans and minimal strings to help debugging:
    - gemini_configured: whether GEMINI_API_KEY or GEMINI_BEARER_TOKEN are present
    - gemini_model: the configured GEMINI_MODEL
    - gemini_sdk_installed: whether 'google.generativeai' SDK is importable
    - gemini_sdk_version: SDK version string if available (not the key)
    - gemini_url: the constructed API URL (if configured)
    - gemini_url_reachable: boolean if the API URL is reachable (HEAD request; no auth)
    - gemini_url_error: short error message if a reachability check failed
    - qdrant_available: current Qdrant availability flag
    """
    api_key, bearer_token, model, api_url = llm_mod.get_gemini_config()
    configured = llm_mod.is_gemini_configured()
    # Check for SDK availability
    sdk_installed = False
    sdk_version = None
    try:
        import google.generativeai as genai  # type: ignore
        sdk_installed = True
        sdk_version = getattr(genai, "__version__", None)
    except Exception:
        sdk_installed = False

    # Try a lightweight reachability check for the API URL (no auth sent)
    gemini_url_reachable = None
    gemini_url_error = None
    if api_url:
        try:
            r = requests.head(api_url, timeout=2)
            gemini_url_reachable = r.status_code < 500
            if not gemini_url_reachable:
                gemini_url_error = f"status={r.status_code}"
        except Exception as e:
            gemini_url_reachable = False
            gemini_url_error = str(e)[:200]

    return {
        "gemini_configured": bool(configured),
        "gemini_model": model,
        "gemini_sdk_installed": bool(sdk_installed),
        "gemini_sdk_version": sdk_version,
        "gemini_url": api_url,
        "gemini_url_reachable": gemini_url_reachable,
        "gemini_url_error": gemini_url_error,
        "qdrant_available": qdrant_available,
    }


if __name__ == "__main__":
    # Run server only if started directly (e.g., `python main.py`)
    # Using uvicorn directly is recommended:
    # /path/to/venv/bin/uvicorn main:app --reload
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
