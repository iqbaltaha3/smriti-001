"""
agents/inspection_agent.py — Agent 4: System Inspector.

RESPONSIBILITY:
  Read organism state + selected memory (episodes, reflections) and
  produce a structured system health snapshot:
    - Counts and stats from all 5 DBs
    - Bottleneck detection (memory growth rate, repetitive episodes, etc.)
    - LLM-generated recommendations for improving the organism
    - Stored as Inspection record for trend analysis over time

  WHAT IS A BOTTLENECK (for an AI organism)?
    - Episodic memory growing too fast (need compression)
    - Same weaknesses appearing in multiple reflections (not being addressed)
    - No new capabilities in 7+ days (evolution stalled)
    - Very few facts despite many conversations (semantic agent underperforming)
    - Reflection not running (organism not self-examining)

  DATA ACCESS:
    - All 5 DB counts (full access)
    - Last 10 episodes (to spot patterns)
    - Last 3 reflections (to check for recurring weaknesses)
    - Organism JSON files (identity, capabilities, weaknesses)
"""

import json
import os
from datetime import date
from tools.llm import ask_llm
from memory import (
    count_episodes, count_facts, count_reflections,
    get_recent_episodes, get_recent_reflections,
    get_recent_inspections, add_inspection, add_milestone
)
from memory.models import Inspection, Milestone

BASE = os.path.dirname(os.path.dirname(__file__))


def _load(rel: str) -> dict:
    with open(os.path.join(BASE, rel)) as f:
        return json.load(f)


def _age_days(birth_date_str: str) -> int:
    if not birth_date_str:
        return 0
    try:
        bd = date.fromisoformat(birth_date_str[:10])
        return (date.today() - bd).days
    except Exception:
        return 0


SYSTEM = """You are the System Inspector for Smriti-001, a digital organism.
Analyse the system health data and identify bottlenecks.
Return ONLY a JSON object. No preamble.

{
  "bottlenecks": "<comma-separated list of issues, or 'none'>",
  "recommendations": "<2-3 specific actionable recommendations>",
  "health_score": <integer 1-10>
}"""


def run_inspection() -> Inspection:
    """
    Perform a full system health inspection.
    Returns the stored Inspection model.
    """
    identity  = _load("organism/identity.json")
    caps      = _load("organism/capabilities.json")
    weaknesses= _load("organism/weaknesses.json")

    # Gather numeric stats
    n_episodes    = count_episodes()
    n_facts       = count_facts()
    n_reflections = count_reflections()
    n_caps        = len(caps["capabilities"])
    n_weak        = len(weaknesses["weaknesses"])
    age           = _age_days(identity.get("birth_date"))

    # Sample memory for qualitative inspection
    recent_eps  = get_recent_episodes(10)
    recent_refs = get_recent_reflections(3)
    past_ins    = get_recent_inspections(2)   # compare against previous inspections

    ep_text  = "\n".join(f"- [{e.importance}/10] {e.event[:80]}" for e in recent_eps)
    ref_text = "\n".join(f"- weakness: {r.weakness_found}" for r in recent_refs if r.weakness_found)
    prev_text= "\n".join(f"- {i.bottlenecks}" for i in past_ins if i.bottlenecks)

    # Ask LLM to find bottlenecks and recommend improvements
    user = f"""ORGANISM STATE:
Age: {age} days
Episodes: {n_episodes}
Facts: {n_facts}
Reflections: {n_reflections}
Capabilities: {n_caps}
Known weaknesses: {n_weak}

RECENT EPISODES (last 10):
{ep_text or "none"}

WEAKNESSES FROM RECENT REFLECTIONS:
{ref_text or "none"}

PREVIOUS INSPECTION BOTTLENECKS:
{prev_text or "no previous inspections"}

QUESTION: What bottlenecks exist? What should be improved?"""

    raw = ask_llm(SYSTEM, user, temperature=0.3)

    # Parse JSON response
    bottlenecks     = "none"
    recommendations = ""
    try:
        cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        parsed = json.loads(cleaned)
        bottlenecks     = str(parsed.get("bottlenecks", "none"))
        recommendations = str(parsed.get("recommendations", ""))
    except Exception:
        bottlenecks     = "parse_error"
        recommendations = raw[:200]

    ins = Inspection(
        age_days            = age,
        total_episodes      = n_episodes,
        total_facts         = n_facts,
        total_reflections   = n_reflections,
        capabilities_count  = n_caps,
        weaknesses_count    = n_weak,
        bottlenecks         = bottlenecks,
        recommendations     = recommendations,
        raw_report          = raw,
    )
    ins.id = add_inspection(ins)

    # Record in timeline
    m = Milestone(
        event_type  = "inspection",
        title       = f"System inspection #{ins.id}",
        description = f"Bottlenecks: {bottlenecks[:80]}",
    )
    add_milestone(m)

    return ins
