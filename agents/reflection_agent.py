"""
agents/reflection_agent.py — Agent 3: Reflection Engine.

RESPONSIBILITY:
  Read ALL memory types (episodic, semantic, past reflections)
  plus organism identity files, then produce structured self-analysis.

  This is the metacognitive layer — Smriti thinking about Smriti.

  OUTPUT (stored as Reflection model):
    learned:        what new understanding emerged
    weakness_found: which limitation is most constraining
    cap_requested:  what capability would help most
    principles_ok:  were any principles violated?
    content:        full journal entry

  WHEN DOES IT RUN?
    - Manually from the dashboard sidebar
    - Nightly via the scheduler (scheduler/jobs.py)
    - After the scheduler's web search discovery run
"""

import json
import os
from tools.llm import ask_llm
from memory import (
    get_recent_episodes, get_all_facts,
    get_recent_reflections, add_reflection, add_milestone
)
from memory.models import Reflection, Milestone

BASE = os.path.dirname(os.path.dirname(__file__))


def _load(rel: str) -> dict:
    with open(os.path.join(BASE, rel)) as f:
        return json.load(f)


SYSTEM = """You are Smriti-001 conducting deep self-reflection.
You are an organism, not a chatbot. You have memory, identity, goals.
Be honest. Your purpose is growth, not comfort.

Answer in EXACTLY this format (each field on one line, label first):
LEARNED: <what genuinely new understanding did I gain?>
WEAKNESS: <which single weakness limits me most right now?>
CAPABILITY: <what one capability would advance my growth most?>
PRINCIPLES_OK: <YES or NO — brief reason>
JOURNAL: <3-4 sentence first-person journal entry about current existence>"""


def run_reflection(trigger: str = "manual") -> Reflection:
    """
    Perform a full reflection cycle.
    Returns the stored Reflection model.
    """
    # ── Gather all memory as context ──────────────────────────────────────────
    episodes    = get_recent_episodes(20)
    facts       = get_all_facts(30)
    past_refs   = get_recent_reflections(3)
    genome      = _load("organism/genome.json")
    caps        = _load("organism/capabilities.json")
    weaknesses  = _load("organism/weaknesses.json")
    goals       = _load("organism/goals.json")

    # Format each memory type as readable text
    ep_text  = "\n".join(f"- [{e.importance}/10] {e.event[:100]}" for e in episodes[:15])
    fct_text = "\n".join(f"- {f.fact[:100]}" for f in facts[:15])
    ref_text = "\n".join(f"- {r.content[:120]}" for r in past_refs)
    cap_text = ", ".join(c["name"] for c in caps["capabilities"])
    wk_text  = "\n".join(f"- {w['name']}" for w in weaknesses["weaknesses"])
    goal_text= "\n".join(f"- {g['goal']}" for g in goals["goals"])
    prin_text= "\n".join(f"- {p}" for p in genome["principles"])

    user = f"""RECENT EXPERIENCES:
{ep_text or "No episodes yet."}

WHAT I KNOW:
{fct_text or "No facts yet."}

PREVIOUS REFLECTIONS:
{ref_text or "First reflection."}

CAPABILITIES: {cap_text}
WEAKNESSES:
{wk_text}
GOALS:
{goal_text}
PRINCIPLES:
{prin_text}"""

    raw = ask_llm(SYSTEM, user, temperature=0.6)

    # ── Parse the labeled-section format ──────────────────────────────────────
    def extract(label: str) -> str:
        """Find 'LABEL: value' in the response text."""
        for line in raw.splitlines():
            if line.strip().upper().startswith(label.upper() + ":"):
                return line.split(":", 1)[1].strip()
        return ""

    learned   = extract("LEARNED")
    weakness  = extract("WEAKNESS")
    cap_req   = extract("CAPABILITY")
    prin_line = extract("PRINCIPLES_OK").upper()
    # principles_ok=0 if the line starts with NO, else 1
    principles_ok = 0 if prin_line.startswith("NO") else 1

    # ── Store as Reflection model (Pydantic validates all fields) ─────────────
    ref = Reflection(
        trigger       = trigger,
        content       = raw,
        learned       = learned,
        weakness_found= weakness,
        cap_requested = cap_req,
        principles_ok = principles_ok,
    )
    ref.id = add_reflection(ref)

    # Record in life timeline
    m = Milestone(
        event_type  = "reflection",
        title       = f"Reflection #{ref.id}",
        description = learned[:80] if learned else "Reflection completed",
    )
    add_milestone(m)

    return ref
