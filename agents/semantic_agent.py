"""
agents/semantic_agent.py — Agent 1: Semantic Memory Keeper.

RESPONSIBILITY:
  Given a piece of text (conversation, web search result, etc.),
  extract objective facts and store them as structured Fact records.

  WHAT COUNTS AS A FACT?
    Objective, timeless statements. Not opinions. Not conversation flow.
    "Python 3.12 was released in 2023" → YES
    "The human seemed interested in ML" → NO (subjective)
    "LLaMA 3 is an open-source model by Meta" → YES

  METADATA RICHNESS:
    Each fact now also gets: confidence, category, embedding,
    and affective dimensions (valence, arousal).
"""

import json
from tools.llm import ask_llm
from tools.embedder import embed
from memory import add_fact
from memory.models import Fact


SYSTEM = """You are the Semantic Memory Agent for Smriti-001.
Extract factual statements from the given text.
Return ONLY a JSON array of objects. No explanation. No preamble.

Each object must have:
{
  "fact": "<the objective fact>",
  "confidence": <integer 1-10, how certain this fact is>,
  "category": "<one of: science, tool, person, event, concept, ai, other>",
  "valence": <float -1.0 to 1.0, emotional tone of the fact itself>,
  "arousal": <float 0.0 to 1.0, intensity>
}

Rules:
- Only objective, verifiable facts. No opinions.
- If nothing factual, return []
- Maximum 5 facts per call"""


def extract_and_store(text: str, source: str = "") -> list[Fact]:
    """
    Extract facts from any text and store them in semantic.db.
    Returns list of Fact models that were stored.
    """
    raw = ask_llm(SYSTEM, f"Text to analyse:\n{text[:1000]}", temperature=0.2)

    facts_data = []
    try:
        cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            facts_data = parsed
    except Exception:
        return []

    stored = []
    for item in facts_data:
        if not isinstance(item, dict) or not item.get("fact"):
            continue

        embedding_json = embed(item["fact"])

        fact = Fact(
            fact       = str(item.get("fact", ""))[:400],
            source     = source[:200],
            confidence = int(item.get("confidence", 7)),
            category   = str(item.get("category", "other")),
            embedding  = embedding_json,
            valence    = float(item.get("valence", 0.0)),
            arousal    = float(item.get("arousal", 0.0)),
        )
        fact.id = add_fact(fact)
        stored.append(fact)

    return stored