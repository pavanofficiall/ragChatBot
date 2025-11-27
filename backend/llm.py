"""
LLM-client wrapper functions.
This module provides a small adapter to call a configured LLM provider.

Behavior:
- If GEMINI_API_KEY is set and GEMINI_API_URL provided, call the provider.
- If credentials are missing, return a mocked response so frontend testing can continue.

Do NOT hardcode API keys in this code. The module reads keys from environment variables.
"""
from typing import Optional, Dict
import os
import logging
import requests

logger = logging.getLogger(__name__)

def get_gemini_config():
    """Return a tuple of (api_key, bearer_token, model, api_url) read from environment dynamically.
    This helps avoid importing stale values if env vars are set after process starts.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    bearer = os.environ.get("GEMINI_BEARER_TOKEN")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    api_url = os.environ.get("GEMINI_API_URL")
    if not api_url:
        model_path = model if model.startswith("models/") else f"models/{model}"
        api_url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent"
    return api_key, bearer, model, api_url

def is_gemini_configured():
    api_key, bearer, model, api_url = get_gemini_config()
    return bool(api_key or bearer)  # True if either key or bearer token present


def call_llm(question: str, provider: str = "gemini") -> Dict:
    """Call the configured LLM provider and return a dictionary with `answer` and `source`.

    Returns a sensible mocked reply if no key or endpoint is configured.
    """
    provider = provider.lower()
    if provider == "gemini":
        # Read GEMINI settings at call-time
        GEMINI_API_KEY, GEMINI_BEARER_TOKEN, GEMINI_MODEL, GEMINI_API_URL = get_gemini_config()
        if not GEMINI_API_KEY and not GEMINI_BEARER_TOKEN:
            # No key / endpoint - return a mocked response for testing
            logger.warning("GEMINI not configured at call time; returning mock response")
            return {"answer": "LLM not configured (mock reply).", "source": "mock", "mode": "llm"}

        # If the official Google Generative AI SDK is installed, prefer it for a more robust interaction
        try:
            import google.generativeai as genai  # type: ignore
            if GEMINI_API_KEY:
                genai.configure(api_key=GEMINI_API_KEY)
            elif GEMINI_BEARER_TOKEN:
                # SDK may prefer ADC or API key; if only bearer token is available, attempt ADC
                os.environ['GOOGLE_OAUTH_ACCESS_TOKEN'] = GEMINI_BEARER_TOKEN
                genai.configure()
            try:
                logger.info('Using google.generativeai SDK for generation')
                # Prefer the ChatSession method for conversational text output
                try:
                    sdk_model = GEMINI_MODEL if GEMINI_MODEL.startswith("models/") else f"models/{GEMINI_MODEL}"
                    model = genai.GenerativeModel(sdk_model)
                except Exception:
                    # Some SDK variants prefer get_model
                    model = genai.get_model(sdk_model)
                chat = model.start_chat()
                resp = chat.send_message(question)
                sdk_text = None
                if hasattr(resp, 'text') and resp.text:
                    sdk_text = resp.text
                elif isinstance(resp, dict):
                    sdk_text = resp.get('output') or resp.get('text') or (resp.get('candidates') and resp['candidates'][0].get('content'))
                elif isinstance(resp, str):
                    sdk_text = resp
                if sdk_text:
                    return {"answer": sdk_text, "source": "llm:gemini-sdk", "mode": "llm"}
            except Exception:
                logger.exception('SDK-based LLM call failed; falling back to REST attempts')
        except Exception:
            logger.debug('google.generativeai SDK not available; using REST fallback')

        # Prepare headers and request body depending on the endpoint
        headers = {"Content-Type": "application/json"}
        params = None
        # For Google Generative Language, you can pass `key` as query param or use OAuth/Bearer token
            # For Google Generative Language, prefer passing the API key in the `key` query param (basic usage).
            # If you prefer to use an OAuth bearer token, set GEMINI_BEARER_TOKEN and it will be used instead.
        if "googleapis" in GEMINI_API_URL:
            # prefer using `key` query param for API key, if provided
            if GEMINI_API_KEY:
                params = {"key": GEMINI_API_KEY}
            # If a bearer token is provided, prefer Authorization header (OAuth style)
            if GEMINI_BEARER_TOKEN:
                headers["Authorization"] = f"Bearer {GEMINI_BEARER_TOKEN}"
            # If we're calling a Google Generative Language v1beta or v1beta2 endpoint, use the expected body
            if "/v1beta/" in GEMINI_API_URL or "/v1beta2/" in GEMINI_API_URL or "/v1/" in GEMINI_API_URL:
                # v1beta endpoints historically accept variations: 'prompt', 'input', 'instances', or chat 'messages'.
                candidate_bodies = [
                    {"prompt": {"text": question}},
                    {"prompt": {"content": [{"type": "text", "text": question}]}},
                    {"input": question},
                    {"input": {"text": question}},
                    {"instances": [{"input": question}]},
                    {"instances": [{"input": {"text": question}}]},
                    {"messages": [{"author": "user", "content": [{"type": "text", "text": question}]}]},
                    # instances/content style often used in REST endpoints
                    {"instances": [{"content": [{"type": "text", "text": question}]}]},
                    {"text": question},
                ]
            else:
                # Generic provider: try Authorization header bearer token or model/prompt format
                candidate_bodies = [
                    {"model": GEMINI_MODEL, "prompt": {"text": question}},
                    {"input": question},
                    {"instances": [{"input": question}]},
                ]
        else:
            # Generic provider: try Authorization header bearer token
            if GEMINI_API_KEY:
                headers["Authorization"] = f"Bearer {GEMINI_API_KEY}"
            body = {"input": question}
        try:
            # Try each candidate body in order until one succeeds
            r = None
            body = None
            last_err = None
            for try_body in candidate_bodies:
                logger.debug('Trying body=%s url=%s headers=%s params=%s', try_body, GEMINI_API_URL, headers, params)
                body = try_body
                r = requests.post(GEMINI_API_URL, json=body, headers=headers, params=params, timeout=20)
                try:
                    r.raise_for_status()
                    break
                except requests.exceptions.HTTPError as e:
                    logger.error('LLM response status=%s body=%s while using body=%s', r.status_code, r.text, try_body)
                    last_err = e
            if r is None:
                raise Exception('LLM request loop failed to produce a response')
            if last_err and r.status_code >= 400:
                # We will enter fallback URL attempts below
                raise last_err
            # Capture raw response for debugging if it fails
            try:
                r.raise_for_status()
            except requests.exceptions.HTTPError as e:
                logger.error('LLM initial response status=%s body=%s', r.status_code, r.text)
                raise
            data = r.json()
            # The response format differs by API; this is a best-effort extraction logic
            answer = None
            # If the response follows a Google-style pattern with 'candidates'
            if isinstance(data, dict):
                if "candidates" in data and isinstance(data["candidates"], list) and data["candidates"]:
                    answer = data["candidates"][0].get("content") or data["candidates"][0].get("output")
                # Some Google endpoints use 'output' or 'content'
                elif "output" in data and isinstance(data["output"], list) and len(data["output"])>0:
                    # Example: output[0].content[0].text
                    try:
                        answer = data["output"][0]["content"][0].get("text")
                    except Exception:
                        answer = None
                elif "text" in data:
                    answer = data.get("text")
                elif "candidates" in data and isinstance(data["candidates"], list):
                    # fallback to stringifying the first candidate
                    try:
                        answer = str(data["candidates"][0])
                    except Exception:
                        answer = None
            # If still not found, check for generic keys
            # Some other APIs use 'output' or 'message'
            if not answer:
                answer = data.get("output") or data.get("content") or data.get("message") or data.get("text") or str(data)
            return {"answer": answer, "source": "llm:gemini", "mode": "llm"}
        except requests.exceptions.HTTPError as http_err:
            # If 404, try alternate URL patterns that some GenAI APIs use
            logger.warning("Initial Gemini request resulted in HTTPError: %s", http_err)
            fallback_attempts = []
            # Try switching between v1beta generateContent and v1 generate and :generateText
            if ":generateContent" in GEMINI_API_URL:
                fallback_attempts.append(GEMINI_API_URL.replace(":generateContent", ":generate"))
                fallback_attempts.append(GEMINI_API_URL.replace(":generateContent", ":generateText"))
            if ":generate" in GEMINI_API_URL:
                fallback_attempts.append(GEMINI_API_URL.replace(":generate", ":generateContent"))
                fallback_attempts.append(GEMINI_API_URL.replace(":generate", ":generateText"))
            if ":generateText" in GEMINI_API_URL:
                fallback_attempts.append(GEMINI_API_URL.replace(":generateText", ":generateContent"))
                fallback_attempts.append(GEMINI_API_URL.replace(":generateText", ":generate"))
            # Try v1beta2 variant
            if "/v1beta/" in GEMINI_API_URL:
                fallback_attempts.append(GEMINI_API_URL.replace("/v1beta/", "/v1beta2/"))
            if "/v1beta2/" in GEMINI_API_URL:
                fallback_attempts.append(GEMINI_API_URL.replace("/v1beta2/", "/v1beta/"))
            # Try v1 variant
            if "/v1beta/" in GEMINI_API_URL or "/v1beta2/" in GEMINI_API_URL:
                fallback_attempts.append(GEMINI_API_URL.replace("/v1beta/", "/v1/") if "/v1beta/" in GEMINI_API_URL else GEMINI_API_URL.replace("/v1beta2/", "/v1/"))

            for attempt in fallback_attempts:
                try:
                    logger.info('Retrying Gemini generation with fallback URL: %s headers=%s params=%s body=%s', attempt, headers, params, body)
                    r2 = requests.post(attempt, json=body, headers=headers, params=params, timeout=20)
                    try:
                        r2.raise_for_status()
                    except requests.exceptions.HTTPError:
                        logger.error('LLM fallback response status=%s body=%s', r2.status_code, r2.text)
                        raise
                    data2 = r2.json()
                    # similarity parsing as above
                    answer2 = None
                    if isinstance(data2, dict):
                        if "candidates" in data2 and isinstance(data2["candidates"], list) and data2["candidates"]:
                            answer2 = data2["candidates"][0].get("content") or data2["candidates"][0].get("output")
                        elif "output" in data2 and isinstance(data2["output"], list) and len(data2["output"])>0:
                            try:
                                answer2 = data2["output"][0]["content"][0].get("text")
                            except Exception:
                                answer2 = None
                        elif "text" in data2:
                            answer2 = data2.get("text")
                    if not answer2:
                        answer2 = data2.get("output") or data2.get("content") or data2.get("message") or data2.get("text") or str(data2)
                    return {"answer": answer2, "source": "llm:gemini", "mode": "llm"}
                except Exception:
                    logger.exception("Fallback attempt failed for URL: %s", attempt)
            # All retry attempts failed
            logger.exception("Error during LLM call: all attempts failed")
            return {"answer": "LLM request failed (fallback mock).", "source": "llm:gemini-failed", "mode": "llm"}
        except Exception as e:
            logger.exception("Error during LLM call")
            return {"answer": "LLM request failed (fallback mock).", "source": "llm:gemini-failed", "mode": "llm"}
        # Done

    # Fallback for unrecognized provider
    logger.warning("Unknown LLM provider '%s' - returning mock response", provider)
    return {"answer": "LLM provider unknown (mock).", "source": "mock", "mode": "llm"}
