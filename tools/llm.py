"""
tools/llm.py – LLM wrapper with Groq (primary) and Ollama (fallback).
Retries on rate limit with exponential backoff.
"""
import os
import time
import requests

GROQ_MODEL = "llama-3.1-8b-instant"
MAX_RETRIES = 3
RETRY_DELAY = 5

def ask_llm(system: str, user: str, temperature: float = 0.7) -> str:
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {groq_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": GROQ_MODEL,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": 1024,
                    },
                    timeout=60,
                )
                if resp.status_code == 429:
                    wait = RETRY_DELAY * attempt
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
            except requests.exceptions.HTTPError:
                if resp.status_code == 429:
                    continue
                raise
        raise RuntimeError("Groq rate limit exceeded after retries.")

    # Fallback to local Ollama
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    MODEL = os.getenv("SMRITI_MODEL", "gemma3:12b")
    resp = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": MODEL,
            "stream": False,
            "options": {"temperature": temperature},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()
