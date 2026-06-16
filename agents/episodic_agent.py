"""
agents/episodic_agent.py — Agent 2: Episodic Memory Keeper.

RESPONSIBILITY:
  Given a raw conversation turn (human message + Smriti's response),
  structure it into a rich Episode record and store it.

  This agent does FIVE things:
    1. Ask LLM to score importance (1-10) based on growth value
    2. Ask LLM to generate tags (comma-separated categories)
    3. Ask LLM to estimate emotional valence (-1 to 1) and arousal (0 to 1)
    4. Embed the episode text for future semantic retrieval
    5. Store the Episode (including affective dimensions)
"""

import json
from tools.llm import ask_llm
from tools.embedder import embed
from memory import add_episode
from memory.models import Episode


SYSTEM = """You are the Episodic Memory Agent for Smriti-001, a digital organism.
Your job: analyse a conversation turn and return ONLY a JSON object.
No explanation. No preamble. Just valid JSON.

Return this exact structure:
{
  "importance": <integer 1-10>,
  "tags": "<comma-separated categories e.g. science,tools,personal>",
  "valence": <float -1.0 to 1.0, negative to positive emotion>,
  "arousal": <float 0.0 to 1.0, low to high intensity>
}

Importance scale:
1-3 = trivial small talk
4-6 = useful exchange, some learning
7-8 = significant new knowledge or skill discussed
9-10 = major capability, weakness, or identity-shaping event

Valence: negative values for frustration, sadness, criticism; positive for joy, curiosity, achievement.
Arousal: low for calm, routine; high for excitement, stress, urgency."""


def store_episode(human: str, human_msg: str,
                  smriti_response: str) -> Episode:
    """
    Structure and store one conversation turn as an Episode.

    Returns the Episode model so the caller can see what was stored.
    """
    # ── Step 1: Ask LLM to score, tag, and assess affect ──────────────────────
    prompt = (
        f"Human message: {human_msg[:400]}\n"
        f"Smriti response: {smriti_response[:400]}"
    )
    raw = ask_llm(SYSTEM, prompt, temperature=0.2)

    # Parse the JSON — Pydantic will catch type errors downstream
    meta = {
        "importance": 5,
        "tags": "conversation",
        "valence": 0.0,
        "arousal": 0.0
    }
    try:
        cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        parsed = json.loads(cleaned)
        meta["importance"] = int(parsed.get("importance", 5))
        meta["tags"]       = str(parsed.get("tags", "conversation"))
        meta["valence"]    = float(parsed.get("valence", 0.0))
        meta["arousal"]    = float(parsed.get("arousal", 0.0))
    except Exception:
        pass  # defaults are fine

    # ── Step 2: Embed the episode text ────────────────────────────────────────
    embed_text = f"{human_msg} {smriti_response}"
    embedding_json = embed(embed_text)

    # ── Step 3: Build and store the Episode model ─────────────────────────────
    ep = Episode(
        human      = human,
        event      = human_msg[:500],
        summary    = smriti_response[:400],
        importance = meta["importance"],
        tags       = meta["tags"],
        embedding  = embedding_json,
        valence    = meta["valence"],
        arousal    = meta["arousal"],
    )
    ep.id = add_episode(ep)
    return ep