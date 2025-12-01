import os
import requests
from typing import List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


GENESIS_CHAT = os.getenv("GENESIS_API", "http://ai.genesis.live/openai/chat/completions")
GENESIS_EMBED = os.getenv("GENESIS_EMBED", "http://ai.genesis.live/ollama/api/embed")
MODEL = os.getenv("GENESIS_MODEL", "llama:latest")
API_KEY = os.getenv("API_KEY", None)


session = requests.Session()
retries = Retry(total=3, backoff_factor=0.3, status_forcelist=(500,502,504))
session.mount('http://', HTTPAdapter(max_retries=retries))


HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["Authorization"] = f"Bearer {API_KEY}"




def chat(messages: List[dict]) -> str:
    payload = {"model": MODEL, "messages": messages}
    r = session.post(GENESIS_CHAT, json=payload, headers=HEADERS, timeout=30)
    r.raise_for_status()
    import sys
    print(f"DEBUG: API Response: '{r.text}'", file=sys.stderr)
    j = r.json()
    # Adapt to server response structure
    if "choices" in j and len(j["choices"])>0:
        content = j["choices"][0]["message"]["content"]
        return content
    # fallback
    raise RuntimeError("Unexpected response from chat endpoint: %s" % str(j))




def embed(inputs: List[str]) -> List[List[float]]:
    payload = {"model": MODEL, "input": inputs}
    r = session.post(GENESIS_EMBED, json=payload, headers=HEADERS, timeout=30)
    r.raise_for_status()
    j = r.json()
    # Expected: {"embeddings": [[...],[...]]}
    if "embeddings" in j:
        return j["embeddings"]
    # Try other shapes
    return j