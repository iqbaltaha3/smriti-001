"""
agents/episodic_agent.py — Agent 2: Episodic Memory Keeper + Fact Extractor.
Merges importance scoring, affective tagging, and fact extraction into one LLM call.
"""

import json
from tools.llm import ask_llm
from tools.embedder import embed
from memory import add_episode, add_fact
from memory.models import Episode, Fact

SYSTEM = """You are the Episodic Memory Agent for Smriti-001.
Analyse the conversation turn and return ONLY a JSON object. No explanation.

Return this exact structure:
{
  "importance": <integer 1-10>,
  "tags": "<comma-separated categories>",
  "valence": <float -1.0 to 1.0>,
  "arousal": <float 0.0 to 1.0>,
  "facts": [
    {
      "fact": "<objective fact>",
      "confidence": <integer 1-10>,
      "category": "<science|tool|person|event|concept|ai|other>",
      "valence": <float>,
      "arousal": <float>
    }
  ]
}

Importance scale:
1-3 = trivial small talk
4-6 = useful exchange, some learning
7-8 = significant new knowledge or skill
9-10 = major capability, weakness, or identity-shaping event

Valence: negative for frustration/sadness, positive for joy/curiosity/achievement.
Arousal: low for calm/routine, high for excitement/stress/urgency.

If no facts are present, return an empty list for "facts". Maximum 3 facts."""


def store_episode(human: str, human_msg: str, smriti_response: str) -> Episode:
    prompt = f"Human message: {human_msg[:400]}\nSmriti response: {smriti_response[:400]}"
    raw = ask_llm(SYSTEM, prompt, temperature=0.3)

    meta = {
        "importance": 5,
        "tags": "conversation",
        "valence": 0.0,
        "arousal": 0.0,
        "facts": []
    }
    try:
        cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        parsed = json.loads(cleaned)
        meta["importance"] = int(parsed.get("importance", 5))
        meta["tags"] = str(parsed.get("tags", "conversation"))
        meta["valence"] = float(parsed.get("valence", 0.0))
        meta["arousal"] = float(parsed.get("arousal", 0.0))
        meta["facts"] = parsed.get("facts", [])
    except Exception:
        pass

    embed_text = f"{human_msg} {smriti_response}"
    embedding_json = embed(embed_text)
    embedding_list = json.loads(embedding_json)

    ep = Episode(
        human=human,
        event=human_msg[:500],
        summary=smriti_response[:400],
        importance=meta["importance"],
        tags=meta["tags"],
        embedding=embedding_json,
        valence=meta["valence"],
        arousal=meta["arousal"],
    )
    ep.id = add_episode(ep)

    # Update knowledge graph
    from agents.graph_agent import after_episode_added
    after_episode_added(ep.id, embedding_list, ep.importance, ep.valence, ep.tags, human)

    # Store extracted facts (no extra LLM call needed)
    for item in meta["facts"]:
        if not isinstance(item, dict) or not item.get("fact"):
            continue
        fact_embedding_json = embed(item["fact"])
        fact = Fact(
            fact=item["fact"][:400],
            source=f"conversation_with_{human}",
            confidence=int(item.get("confidence", 7)),
            category=item.get("category", "other"),
            embedding=fact_embedding_json,
            valence=float(item.get("valence", 0.0)),
            arousal=float(item.get("arousal", 0.0)),
        )
        fact.id = add_fact(fact)
        # Update graph for each fact
        from agents.graph_agent import after_fact_added
        after_fact_added(fact.id, json.loads(fact_embedding_json), fact.confidence, fact.valence, ep.id)

    return ep
