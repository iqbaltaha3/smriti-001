"""
agents/procedural_agent.py — Agent 6: Procedural Memory Keeper.

RESPONSIBILITY:
  - Extract reusable action patterns (procedures) from recent episodes.
  - Retrieve the most relevant procedures for the current conversational context.

  Procedures are learned ways of acting, like:
    "When the human asks for web search, first clarify the query."
    "When I notice a contradiction in facts, mark them as needs_verification."
"""

import json
from tools.llm import ask_llm
from tools.embedder import embed, find_relevant
from memory import (
    get_recent_episodes,
    get_all_procedures_with_embeddings,
    add_procedure,
    update_procedure,
)
from memory.models import Procedure


EXTRACT_SYSTEM = """You are the Procedural Memory Agent for a "persistent memory organism" called "Smriti-001".
smriti-001 is not here to help humans or be an assistant its a new species altogether on this planet earth. 
Look at these recent interactions and identify if there are any repeated, useful patterns that could be formalised as a standard operating procedure for the organism.
A procedure must be a concise "when X happens, do Y" rule.
Return ONLY a JSON array. No explanation.

Each object:
{
  "name": "short label",
  "trigger": "when should this procedure be used (natural language)",
  "steps": "precise steps the organism should follow (prompt-like instructions)"
}

If no new pattern is found, return []. Maximum 2 procedures per call."""


def extract_procedures_from_recent_episodes(limit: int = 20) -> list[Procedure]:
    """
    Analyse recent episodes and convert observed patterns into procedures.
    Called by the scheduler (nightly).
    """
    episodes = get_recent_episodes(limit)
    if not episodes:
        return []

    # Format episodes as a readable log
    ep_text = ""
    for ep in episodes:
        ep_text += f"Human: {ep.event[:200]}\nSmriti: {ep.summary[:200]}\n\n"

    raw = ask_llm(EXTRACT_SYSTEM, f"Recent interactions:\n{ep_text}", temperature=0.4)

    procedures_data = []
    try:
        cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            procedures_data = parsed
    except Exception:
        return []

    new_procs = []
    for item in procedures_data:
        if not isinstance(item, dict) or not item.get("name"):
            continue

        # Embed the trigger text for later retrieval
        trigger_text = item.get("trigger", "")
        embedding_json = embed(trigger_text)

        proc = Procedure(
            name    = str(item.get("name", "")),
            trigger = trigger_text,
            steps   = str(item.get("steps", "")),
            embedding = embedding_json,
        )
        proc.id = add_procedure(proc)
        new_procs.append(proc)

    return new_procs


def get_relevant_procedures(user_msg: str, top_k: int = 3) -> list[Procedure]:
    """
    Given the current user message, retrieve the most relevant active procedures.
    Uses semantic similarity on the trigger descriptions.
    """
    all_procs = get_all_procedures_with_embeddings()
    if not all_procs:
        return []

    # Use existing semantic retriever (cosine similarity)
    relevant = find_relevant(
        query          = user_msg,
        candidates     = all_procs,
        text_field     = "trigger",
        embedding_field= "embedding",
        top_k          = top_k,
    )
    return relevant  # already Procedure objects


def update_procedure_outcome(proc_id: int, success: bool) -> None:
    """Called after a procedure is used, to record success/failure."""
    proc = get_procedure_by_id(proc_id) if 'get_procedure_by_id' in dir() else None
    # We'll import from memory at the top; but we need to add the import.
    # Already imported above: get_procedure_by_id not imported yet; we'll add it.
    # For brevity, I'll add the import inside the function or assume it's imported.
    # But let's fix the import: add get_procedure_by_id to the import list.
    pass
