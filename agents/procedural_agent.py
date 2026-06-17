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
    get_procedure_by_id,
)
from memory.models import Procedure


EXTRACT_SYSTEM = """You are the Procedural Memory Agent for Smriti-001, a digital organism.
Look at these recent interactions and identify any repeated, useful patterns that could
become a standard operating procedure for the organism.

A valid procedure must be:
- An internal cognitive strategy (how to answer, how to reflect, how to search).
- Something Smriti can actually do with its existing capabilities (converse, search, reflect, inspect, recall, store).
- Concrete and repeatable: "When X happens, do Y in Z steps".

Do NOT propose procedures that:
- Modify files, execute code, or access external systems (Smriti cannot do this).
- Simply acknowledge human requests without adding value.
- Summarise only because asked — summarisation is already a basic ability, not a learned skill.

If no meaningful new procedure is found, return [].

Each object:
{
  "name": "short label",
  "trigger": "when should this procedure be used (natural language)",
  "steps": "precise steps the organism should follow"
}

Maximum 2 procedures per call. Return ONLY a JSON array. No explanation."""


def extract_procedures_from_recent_episodes(limit: int = 20) -> list[Procedure]:
    """
    Analyse recent episodes and convert observed patterns into procedures.
    Called by the scheduler or manually.
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

        trigger_text = item.get("trigger", "")
        steps_text   = item.get("steps", "")

        # --- Skip out‑of‑scope procedures ---
        forbidden = ["file", "modification", "acknowledgement", "memory update", "delete"]
        if any(word in trigger_text.lower() or word in steps_text.lower() for word in forbidden):
            continue

        embedding_json = embed(trigger_text)

        proc = Procedure(
            name      = str(item.get("name", "")),
            trigger   = trigger_text,
            steps     = steps_text,
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

    relevant = find_relevant(
        query          = user_msg,
        candidates     = all_procs,
        text_field     = "trigger",
        embedding_field= "embedding",
        top_k          = top_k,
    )
    return relevant


def update_procedure_outcome(proc_id: int, success: bool) -> None:
    """Called after a procedure is used, to record success/failure."""
    proc = get_procedure_by_id(proc_id)
    if not proc:
        return
    if success:
        proc.success_count += 1
    else:
        proc.failure_count += 1
    proc.last_used = __import__('datetime').datetime.utcnow().isoformat()
    update_procedure(proc)
