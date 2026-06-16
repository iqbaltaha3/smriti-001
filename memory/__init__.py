"""
memory/__init__.py — Database layer for Smriti-001.

5 SQLite databases, each with one purpose:
  episodic.db    → what happened (conversations)
  semantic.db    → what I know (extracted facts)
  reflections.db → what I think about myself
  history.db     → major life milestones
  inspections.db → system health snapshots
  procedures.db  → learned action patterns (NEW)

WHY SQLITE?
  Zero setup. File-based. No server. Safe for single-user local apps.
  Each DB is a plain .db file you can open with any SQLite viewer.

PATTERN:
  Every public function accepts or returns a Pydantic model (from models.py).
  SQLite rows → dict via row_factory → Pydantic model for validation.
  This means callers ALWAYS get typed, validated data — never raw tuples.
"""

import sqlite3
import os
from typing import Optional
from .models import Episode, Fact, Reflection, Milestone, Inspection, Procedure, CodeFile

# All DB files live in the same directory as this file
_DIR = os.path.dirname(__file__)


# ── Internal helpers ───────────────────────────────────────────────────────────

def _conn(db_name: str) -> sqlite3.Connection:
    """Open a connection to a named DB. row_factory makes rows behave like dicts."""
    path = os.path.join(_DIR, db_name)
    c = sqlite3.connect(path, check_same_thread=False)
    c.row_factory = sqlite3.Row   # now row["field"] works instead of row[0]
    return c


def _row_to(model_cls, row) -> object:
    """Convert a sqlite3.Row to a Pydantic model. Safe — validates on creation."""
    return model_cls(**dict(row)) if row else None


# ── Init — create all tables ───────────────────────────────────────────────────

def init_all():
    """
    Create every table if it doesn't exist.
    Safe to call on every app start (IF NOT EXISTS = idempotent).
    """
    _init_episodic()
    _init_semantic()
    _init_reflections()
    _init_history()
    _init_inspections()
    _init_procedures()
    _init_codebase()


def _init_episodic():
    c = _conn("episodic.db")
    c.execute("""CREATE TABLE IF NOT EXISTS episodes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp   TEXT    NOT NULL,
        human       TEXT    NOT NULL,
        event       TEXT    NOT NULL,
        summary     TEXT    DEFAULT '',
        importance  INTEGER DEFAULT 5,
        tags        TEXT    DEFAULT '',
        embedding   TEXT    DEFAULT NULL,
        valence     REAL    DEFAULT 0.0,
        arousal     REAL    DEFAULT 0.0
    )""")
    c.commit(); c.close()


def _init_semantic():
    c = _conn("semantic.db")
    c.execute("""CREATE TABLE IF NOT EXISTS facts (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp   TEXT    NOT NULL,
        fact        TEXT    NOT NULL,
        source      TEXT    DEFAULT '',
        confidence  INTEGER DEFAULT 7,
        category    TEXT    DEFAULT '',
        embedding   TEXT    DEFAULT NULL,
        valence     REAL    DEFAULT 0.0,
        arousal     REAL    DEFAULT 0.0
    )""")
    c.commit(); c.close()


def _init_reflections():
    c = _conn("reflections.db")
    c.execute("""CREATE TABLE IF NOT EXISTS reflections (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp       TEXT    NOT NULL,
        trigger         TEXT    DEFAULT 'manual',
        content         TEXT    DEFAULT '',
        learned         TEXT    DEFAULT '',
        weakness_found  TEXT    DEFAULT '',
        cap_requested   TEXT    DEFAULT '',
        principles_ok   INTEGER DEFAULT 1
    )""")
    c.commit(); c.close()


def _init_history():
    c = _conn("history.db")
    c.execute("""CREATE TABLE IF NOT EXISTS timeline (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp   TEXT    NOT NULL,
        event_type  TEXT    DEFAULT '',
        title       TEXT    DEFAULT '',
        description TEXT    DEFAULT ''
    )""")
    c.commit(); c.close()


def _init_inspections():
    c = _conn("inspections.db")
    c.execute("""CREATE TABLE IF NOT EXISTS inspections (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp           TEXT    NOT NULL,
        age_days            INTEGER DEFAULT 0,
        total_episodes      INTEGER DEFAULT 0,
        total_facts         INTEGER DEFAULT 0,
        total_reflections   INTEGER DEFAULT 0,
        capabilities_count  INTEGER DEFAULT 0,
        weaknesses_count    INTEGER DEFAULT 0,
        bottlenecks         TEXT    DEFAULT '',
        recommendations     TEXT    DEFAULT '',
        raw_report          TEXT    DEFAULT ''
    )""")
    c.commit(); c.close()


def _init_procedures():
    c = _conn("procedures.db")
    c.execute("""CREATE TABLE IF NOT EXISTS procedures (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp      TEXT    NOT NULL,
        name           TEXT    NOT NULL,
        trigger        TEXT    DEFAULT '',
        steps          TEXT    DEFAULT '',
        success_count  INTEGER DEFAULT 0,
        failure_count  INTEGER DEFAULT 0,
        last_used      TEXT    DEFAULT '',
        embedding      TEXT    DEFAULT NULL,
        is_active      INTEGER DEFAULT 1
    )""")
    c.commit(); c.close()


# ── Episodic CRUD ──────────────────────────────────────────────────────────────

def add_episode(ep: Episode) -> int:
    c = _conn("episodic.db")
    cur = c.execute(
        "INSERT INTO episodes (timestamp,human,event,summary,importance,tags,embedding,valence,arousal)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (ep.timestamp, ep.human, ep.event, ep.summary,
         ep.importance, ep.tags, ep.embedding, ep.valence, ep.arousal)
    )
    c.commit(); rid = cur.lastrowid; c.close()
    return rid


def get_recent_episodes(limit: int = 50) -> list[Episode]:
    c = _conn("episodic.db")
    rows = c.execute(
        "SELECT * FROM episodes ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    c.close()
    return [Episode(**dict(r)) for r in rows]


def get_all_episodes_with_embeddings() -> list[Episode]:
    """Used by semantic retrieval — returns only rows that have an embedding."""
    c = _conn("episodic.db")
    rows = c.execute(
        "SELECT * FROM episodes WHERE embedding IS NOT NULL ORDER BY id DESC"
    ).fetchall()
    c.close()
    return [Episode(**dict(r)) for r in rows]


def count_episodes() -> int:
    c = _conn("episodic.db")
    n = c.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    c.close(); return n


def get_episode_by_id(eid: int) -> Optional[Episode]:
    c = _conn("episodic.db")
    row = c.execute("SELECT * FROM episodes WHERE id = ?", (eid,)).fetchone()
    c.close()
    return _row_to(Episode, row)


# ── Semantic CRUD ──────────────────────────────────────────────────────────────

def add_fact(fact: Fact) -> int:
    c = _conn("semantic.db")
    cur = c.execute(
        "INSERT INTO facts (timestamp,fact,source,confidence,category,embedding,valence,arousal)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (fact.timestamp, fact.fact, fact.source,
         fact.confidence, fact.category, fact.embedding, fact.valence, fact.arousal)
    )
    c.commit(); rid = cur.lastrowid; c.close()
    return rid


def get_all_facts(limit: int = 100) -> list[Fact]:
    c = _conn("semantic.db")
    rows = c.execute(
        "SELECT * FROM facts ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    c.close()
    return [Fact(**dict(r)) for r in rows]


def count_facts() -> int:
    c = _conn("semantic.db")
    n = c.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    c.close(); return n


def get_fact_by_id(fid: int) -> Optional[Fact]:
    c = _conn("semantic.db")
    row = c.execute("SELECT * FROM facts WHERE id = ?", (fid,)).fetchone()
    c.close()
    return _row_to(Fact, row)


# ── Reflection CRUD ────────────────────────────────────────────────────────────

def add_reflection(ref: Reflection) -> int:
    c = _conn("reflections.db")
    cur = c.execute(
        "INSERT INTO reflections (timestamp,trigger,content,learned,weakness_found,cap_requested,principles_ok)"
        " VALUES (?,?,?,?,?,?,?)",
        (ref.timestamp, ref.trigger, ref.content, ref.learned,
         ref.weakness_found, ref.cap_requested, ref.principles_ok)
    )
    c.commit(); rid = cur.lastrowid; c.close()
    return rid


def get_recent_reflections(limit: int = 10) -> list[Reflection]:
    c = _conn("reflections.db")
    rows = c.execute(
        "SELECT * FROM reflections ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    c.close()
    return [Reflection(**dict(r)) for r in rows]


def count_reflections() -> int:
    c = _conn("reflections.db")
    n = c.execute("SELECT COUNT(*) FROM reflections").fetchone()[0]
    c.close(); return n


# ── History CRUD ───────────────────────────────────────────────────────────────

def add_milestone(m: Milestone) -> int:
    c = _conn("history.db")
    cur = c.execute(
        "INSERT INTO timeline (timestamp,event_type,title,description) VALUES (?,?,?,?)",
        (m.timestamp, m.event_type, m.title, m.description)
    )
    c.commit(); rid = cur.lastrowid; c.close()
    return rid


def get_timeline() -> list[Milestone]:
    c = _conn("history.db")
    rows = c.execute("SELECT * FROM timeline ORDER BY id ASC").fetchall()
    c.close()
    return [Milestone(**dict(r)) for r in rows]


# ── Inspection CRUD ────────────────────────────────────────────────────────────

def add_inspection(ins: Inspection) -> int:
    c = _conn("inspections.db")
    cur = c.execute(
        "INSERT INTO inspections (timestamp,age_days,total_episodes,total_facts,"
        "total_reflections,capabilities_count,weaknesses_count,bottlenecks,"
        "recommendations,raw_report) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (ins.timestamp, ins.age_days, ins.total_episodes, ins.total_facts,
         ins.total_reflections, ins.capabilities_count, ins.weaknesses_count,
         ins.bottlenecks, ins.recommendations, ins.raw_report)
    )
    c.commit(); rid = cur.lastrowid; c.close()
    return rid


def get_recent_inspections(limit: int = 5) -> list[Inspection]:
    c = _conn("inspections.db")
    rows = c.execute(
        "SELECT * FROM inspections ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    c.close()
    return [Inspection(**dict(r)) for r in rows]


# ── Procedure CRUD (NEW) ───────────────────────────────────────────────────────

def add_procedure(proc: Procedure) -> int:
    c = _conn("procedures.db")
    cur = c.execute(
        "INSERT INTO procedures (timestamp,name,trigger,steps,success_count,failure_count,last_used,embedding,is_active)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (proc.timestamp, proc.name, proc.trigger, proc.steps,
         proc.success_count, proc.failure_count, proc.last_used,
         proc.embedding, int(proc.is_active))
    )
    c.commit(); rid = cur.lastrowid; c.close()
    return rid


def update_procedure(proc: Procedure) -> None:
    c = _conn("procedures.db")
    c.execute(
        "UPDATE procedures SET name=?, trigger=?, steps=?, success_count=?, failure_count=?, last_used=?, embedding=?, is_active=? WHERE id=?",
        (proc.name, proc.trigger, proc.steps, proc.success_count, proc.failure_count,
         proc.last_used, proc.embedding, int(proc.is_active), proc.id)
    )
    c.commit(); c.close()


def get_all_procedures(active_only: bool = True) -> list[Procedure]:
    c = _conn("procedures.db")
    if active_only:
        rows = c.execute("SELECT * FROM procedures WHERE is_active=1 ORDER BY id DESC").fetchall()
    else:
        rows = c.execute("SELECT * FROM procedures ORDER BY id DESC").fetchall()
    c.close()
    return [Procedure(**dict(r)) for r in rows]


def get_procedure_by_id(pid: int) -> Optional[Procedure]:
    c = _conn("procedures.db")
    row = c.execute("SELECT * FROM procedures WHERE id = ?", (pid,)).fetchone()
    c.close()
    return _row_to(Procedure, row)


def get_all_procedures_with_embeddings() -> list[Procedure]:
    c = _conn("procedures.db")
    rows = c.execute("SELECT * FROM procedures WHERE embedding IS NOT NULL AND is_active=1 ORDER BY id DESC").fetchall()
    c.close()
    return [Procedure(**dict(r)) for r in rows]

def _init_codebase():
    c = _conn("codebase.db")
    c.execute("""CREATE TABLE IF NOT EXISTS code_files (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        path            TEXT    NOT NULL UNIQUE,
        content         TEXT    NOT NULL,
        summary         TEXT    DEFAULT '',
        embedding       TEXT    DEFAULT NULL,
        last_modified   TEXT    NOT NULL
    )""")
    c.commit(); c.close()

# ── Codebase CRUD (NEW) ───────────────────────────────────────────────────────

def upsert_code_file(cf: CodeFile) -> int:
    """Insert or replace a code file record. Returns the row id."""
    c = _conn("codebase.db")
    # Use INSERT OR REPLACE with the unique path
    cur = c.execute(
        "INSERT OR REPLACE INTO code_files (path, content, summary, embedding, last_modified)"
        " VALUES (?,?,?,?,?)",
        (cf.path, cf.content, cf.summary, cf.embedding, cf.last_modified)
    )
    c.commit()
    # Get the id of the inserted/replaced row
    row = c.execute("SELECT id FROM code_files WHERE path = ?", (cf.path,)).fetchone()
    rid = row["id"] if row else None
    c.close()
    return rid

def get_code_file_by_path(path: str) -> Optional[CodeFile]:
    c = _conn("codebase.db")
    row = c.execute("SELECT * FROM code_files WHERE path = ?", (path,)).fetchone()
    c.close()
    return _row_to(CodeFile, row) if row else None

def get_all_code_files() -> list[CodeFile]:
    c = _conn("codebase.db")
    rows = c.execute("SELECT * FROM code_files ORDER BY path ASC").fetchall()
    c.close()
    return [CodeFile(**dict(r)) for r in rows]

def get_all_code_files_with_embeddings() -> list[CodeFile]:
    c = _conn("codebase.db")
    rows = c.execute("SELECT * FROM code_files WHERE embedding IS NOT NULL ORDER BY path ASC").fetchall()
    c.close()
    return [CodeFile(**dict(r)) for r in rows]