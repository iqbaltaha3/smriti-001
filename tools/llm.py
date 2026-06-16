"""
tools/llm.py — The single LLM call all agents use.

WHY ONE FUNCTION?
  DRY principle. If we swap Gemma for Llama or Mistral,
  we change ONE place. No agent file ever touches requests directly.

ask_llm(system, user, temperature) → str
  system:      who the model IS (role, principles, rules)
  user:        what the model SEES (data, question, context)
  temperature: 0.1 = precise/deterministic, 0.7 = creative/exploratory
"""

import os
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL      = os.getenv("SMRITI_MODEL", "gemma3:12b")


def ask_llm(system: str, user: str, temperature: float = 0.7) -> str:
    """Single Ollama call. Returns the model's response as a plain string."""
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model":   MODEL,
                "stream":  False,
                "options": {"temperature": temperature},
                "messages": [
                    {"role": "system",  "content": system},
                    {"role": "user",    "content": user},
                ],
            },
            timeout=120,  # 12B models can be slow — give them 2 min
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Cannot reach Ollama at {OLLAMA_URL}. "
            "Run: ollama serve"
        )
