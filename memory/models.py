"""
memory/models.py — Pydantic models for every record type.

WHY PYDANTIC OVER TYPEDDICT OR JSON PARSING?
  - TypedDict:    just type hints, no validation at runtime.
  - json.loads(): returns raw dicts — wrong types cause silent bugs.
  - Pydantic:     validates AND coerces types at creation time.
                  A bad int raises immediately, not 3 steps later.

Each model maps 1-to-1 to a DB table row.
model.model_dump() → plain dict → easy to store / display.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Episodic memory row ────────────────────────────────────────────────────────
class Episode(BaseModel):
    id:           Optional[int]  = None
    timestamp:    str            = Field(default_factory=lambda: datetime.utcnow().isoformat())
    human:        str                            # who smriti was talking to
    event:        str                            # what happened (human msg)
    summary:      str            = ""            # smriti's response summary
    importance:   int            = 5             # 1 (trivial) → 10 (critical)
    tags:         str            = ""            # comma-separated e.g. "science,tools"
    embedding:    Optional[str]  = None          # JSON-serialised float list
    valence:      float          = 0.0           # emotional valence -1 (neg) to 1 (pos)
    arousal:      float          = 0.0           # intensity 0 (calm) to 1 (excited)


# ── Semantic memory row ────────────────────────────────────────────────────────
class Fact(BaseModel):
    id:           Optional[int]  = None
    timestamp:    str            = Field(default_factory=lambda: datetime.utcnow().isoformat())
    fact:         str                            # the actual learned fact
    source:       str            = ""            # e.g. "Conversation with Arjun"
    confidence:   int            = 7             # 1-10
    category:     str            = ""            # "science" | "tool" | "person" …
    embedding:    Optional[str]  = None
    valence:      float          = 0.0
    arousal:      float          = 0.0


# ── Reflection row ─────────────────────────────────────────────────────────────
class Reflection(BaseModel):
    id:               Optional[int]  = None
    timestamp:        str            = Field(default_factory=lambda: datetime.utcnow().isoformat())
    trigger:          str            = "manual"  # "nightly" | "manual" | "post_convo"
    content:          str            = ""        # full LLM output
    learned:          str            = ""        # extracted field
    weakness_found:   str            = ""        # extracted field
    cap_requested:    str            = ""        # extracted field
    principles_ok:    int            = 1         # 1=fine, 0=violation (SQLite has no bool)


# ── History / milestone row ────────────────────────────────────────────────────
class Milestone(BaseModel):
    id:           Optional[int]  = None
    timestamp:    str            = Field(default_factory=lambda: datetime.utcnow().isoformat())
    event_type:   str            = ""            # "birth" | "capability" | "reflection"
    title:        str            = ""
    description:  str            = ""


# ── Inspection row ─────────────────────────────────────────────────────────────
class Inspection(BaseModel):
    id:               Optional[int]  = None
    timestamp:        str            = Field(default_factory=lambda: datetime.utcnow().isoformat())
    age_days:         int            = 0
    total_episodes:   int            = 0
    total_facts:      int            = 0
    total_reflections:int            = 0
    capabilities_count: int          = 0
    weaknesses_count: int            = 0
    bottlenecks:      str            = ""        # comma-separated issues found
    recommendations:  str            = ""        # LLM-generated suggestions
    raw_report:       str            = ""        # full inspection text


# ── Procedural memory row ──────────────────────────────────────────────────────
class Procedure(BaseModel):
    id:            Optional[int] = None
    timestamp:     str           = Field(default_factory=lambda: datetime.utcnow().isoformat())
    name:          str                           # short label
    trigger:       str                           # when to apply (natural language)
    steps:         str                           # what to do (prompt-like instructions)
    success_count: int           = 0
    failure_count: int           = 0
    last_used:     str           = Field(default_factory=lambda: datetime.utcnow().isoformat())
    embedding:     Optional[str] = None          # for semantic retrieval
    is_active:     bool          = True


# ── Codebase file row ──────────────────────────────────────────────────────────
class CodeFile(BaseModel):
    id:           Optional[int] = None
    path:         str                            # relative file path (e.g., "agents/episodic_agent.py")
    content:      str                            # raw file content
    summary:      str            = ""            # LLM-generated summary of the file
    embedding:    Optional[str]  = None          # embedding of the summary
    last_modified: str           = Field(default_factory=lambda: datetime.utcnow().isoformat())