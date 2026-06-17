"""
agents/semantic_agent.py — Agent 1: Semantic Memory Keeper.
Extracts objective facts from text and stores them.
Now also updates the knowledge graph.
"""

import json
from tools.llm import ask_llm
from tools.embedder import embed
from memory import add_fact
from memory.models import Fact

SYSTEM = """You are the Semantic Memory Agent for Smriti-001.
Extract all type of factual statements from the given text.
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


def extract_and_store(text: str, source: str = "", source_episode_id: int = None) -> list[Fact]:
    """Extract facts from any text and store them. Returns list of Fact models."""
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
        embedding_list = json.loads(embedding_json)

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

        # Update knowledge graph
        from agents.graph_agent import after_fact_added
        after_fact_added(fact.id, embedding_list, fact.confidence, fact.valence,
                         source_episode_id)

    return stored
