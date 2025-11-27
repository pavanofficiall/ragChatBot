Setting up Gemini (Generative) LLM access
----------------------------------------
To use the Google Generative Language (Gemini) model for general questions, configure your environment variables and install dependencies.

1) Ensure the `GEMINI_API_KEY` is set in the same shell where you start the backend. Example:

```bash
# Option A: start server directly (make sure env is exported in the same shell)
export GEMINI_API_KEY="YOUR_GOOGLE_API_KEY"
export GEMINI_MODEL="models/gemini-2.5-flash"
python -m pip install -r requirements.txt
.venv/bin/uvicorn backend.main:app --reload

# Option B: use .env + helper script (recommended for local dev)
# Copy the example .env and edit it (do not commit your backend/.env)
cp backend/.env.example backend/.env
# Edit backend/.env and then run the helper script
./backend/start-dev.sh
```

2) Use the `POST /query/` endpoint to ask general questions. The backend will use Gemini via the `google-generativeai` SDK if installed and configured, and will return the LLM's response as JSON.

3) Optional: Create a `.env` file with the values above and use `python-dotenv` to load it into the environment if desired.

# Simple RAG Backend with FastAPI, Qdrant, and SentenceTransformers

This small backend demonstrates retrieval augmented generation (RAG) with Qdrant and SentenceTransformers.

Features:
- Stores a small dataset of facts (apples) in a Qdrant collection.
- Embeds facts and user queries using a SentenceTransformer.
- Exposes a POST `/query/` endpoint to return the most relevant fact.

Requirements
- Python 3.9+
- Qdrant (run locally via Docker or use remote)

Install and run Qdrant (local Docker)

```bash
# Quick start Qdrant locally
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

Install Python packages and run the server

```bash
# Create your venv (optional but recommended)
python -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload
```

Query the server

```bash
# Example using curl
curl -X POST "http://127.0.0.1:8000/query/" -H "Content-Type: application/json" \
  -d '{"question": "How many apples does Pavan have?"}'

# Expect JSON back like:
# {"answer": "Pavan has 82 apples"}
```

Notes and extra tips
- The collection is recreated at startup, which clears previous data. For a persistent dataset, remove recreate_collection behavior.
- If the model fails to download (or you prefer to pre-download), run a one-off `python` session to download the SentenceTransformer model.
- Consider a config file or using environment variables to manage Qdrant host/port and collection name.

- If your frontend runs on a different origin (e.g., Next.js dev server on `http://localhost:3000`), you may need to allow CORS. The backend accepts an environment variable `CORS_ALLOWED_ORIGINS` (default: `http://localhost:3000`).
Environment variables
- `GEMINI_API_KEY` - API key for Google Gemini (set this in your environment, don't store it in code)
- `GEMINI_API_URL` - API endpoint for Gemini (example: the REST endpoint for model generation)
- `LLM_PROVIDER` - Name of provider (default `gemini`). You can implement other providers as needed.
- `FALLBACK_TO_LLM_FOR_LEGAL` - If `true`, legal queries with no retrievals will fall back to the LLM for generation (default: `false`).

Diagnostics endpoint
--------------------
For easier local debugging, the backend exposes a non-secret `GET /diagnostics` endpoint which returns a JSON object with the following fields:

- `gemini_configured`: whether the Gemini API key (or bearer token) is configured in the process environment
- `gemini_model`: the model configured via `GEMINI_MODEL` (string)
- `gemini_sdk_installed`: whether the `google.generativeai` SDK is installed and importable
- `gemini_sdk_version`: SDK version string (if available)
- `gemini_url`: the constructed Gemini API URL
- `gemini_url_reachable`: boolean that indicates whether the API URL was reachable (a quick HEAD check)
- `gemini_url_error`: short error message if reachability check failed
- `qdrant_available`: whether Qdrant is reachable (true/false)

Use `curl http://127.0.0.1:8000/diagnostics` to see the fields and diagnostics output; it is safe to call from local environments and avoids returning secret keys.
