"""
scheduler/jobs.py — Background scheduled tasks for Smriti-001.

THREE JOBS:
  1. discover()     — Every 4 hours. Search for AI news, store as facts.
  2. reflect()      — Every night at 23:00. Run full reflection cycle.
  3. inspect()      — Every morning at 08:00. Run system health inspection.

HOW APSCHEDULER WORKS:
  - BackgroundScheduler runs jobs in separate threads (non-blocking).
  - The Streamlit app stays responsive while jobs run in the background.
  - Jobs run even if no one is actively using the dashboard.
  - APScheduler persists job schedules in memory (not across restarts —
    but jobs re-register every time app.py starts, so that's fine).

INSTALL: pip install apscheduler

DESIGN PRINCIPLE:
  All jobs are fire-and-forget. They log results to their respective DBs.
  The dashboard reads from those DBs — it doesn't need to know when jobs ran.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler

from tools.web_search import search, DISCOVERY_QUERIES
from agents.semantic_agent import extract_and_store
from agents.reflection_agent import run_reflection
from agents.inspection_agent import run_inspection
from memory import add_milestone
from memory.models import Milestone

log = logging.getLogger("smriti.scheduler")


# ── Job 1: Internet Discovery ─────────────────────────────────────────────────

def discover():
    """
    Passive internet observation — runs every 4 hours.
    Searches for AI news and stores discoveries as semantic facts.
    This is the 'observe_world' instinct in action.
    """
    log.info("Starting discovery run...")
    total_facts = 0

    for query in DISCOVERY_QUERIES:
        results = search(query)
        for r in results[:2]:   # top 2 results per query
            if r.get("text") and r["text"] != "" and "error" not in r["title"]:
                facts = extract_and_store(r["text"], source=f"web:{query}")
                total_facts += len(facts)

    log.info(f"Discovery run complete — {total_facts} facts stored")

    # Record in timeline if we found anything
    if total_facts > 0:
        m = Milestone(
            event_type  = "discovery",
            title       = "Internet observation run",
            description = f"Discovered {total_facts} new facts from web search",
        )
        add_milestone(m)


# ── Job 2: Nightly Reflection ─────────────────────────────────────────────────

def nightly_reflect():
    """Runs at 23:00 every night. Full self-analysis cycle."""
    log.info("Starting nightly reflection...")
    ref = run_reflection(trigger="nightly")
    log.info(f"Nightly reflection complete — id={ref.id}")


# ── Job 3: Morning Inspection ─────────────────────────────────────────────────

def morning_inspect():
    """Runs at 08:00 every morning. System health check."""
    log.info("Starting morning inspection...")
    ins = run_inspection()
    log.info(f"Inspection complete — bottlenecks: {ins.bottlenecks}")


# ── Scheduler setup ───────────────────────────────────────────────────────────

def start_scheduler() -> BackgroundScheduler:
    """
    Create and start the background scheduler.
    Returns the scheduler instance so app.py can stop it on shutdown.

    Call this ONCE from app.py at startup.
    """
    scheduler = BackgroundScheduler()

    scheduler.add_job(weekly_procedure_extraction, "cron", day_of_week="sun", hour=2, minute=0, id="proc_extract") 

    # Discovery: every 4 hours
    scheduler.add_job(discover, "interval", hours=4, id="discover")

    # Nightly reflection: 23:00 every day
    scheduler.add_job(nightly_reflect, "cron", hour=23, minute=0, id="reflect")

    # Morning inspection: 08:00 every day
    scheduler.add_job(morning_inspect, "cron", hour=8, minute=0, id="inspect")

    scheduler.add_job(daily_code_scan, "cron", hour=3, minute=0, id="code_scan")

    scheduler.start()
    log.info("Scheduler started — jobs: discover(4h), reflect(23:00), inspect(08:00)")
    return scheduler

def weekly_procedure_extraction():
    from agents.procedural_agent import extract_procedures_from_recent_episodes
    new = extract_procedures_from_recent_episodes()
    log.info(f"Procedure extraction complete — {len(new)} new procedures")

def daily_code_scan():
    from agents.code_introspection_agent import scan_and_index
    log.info("Running daily codebase scan...")
    count = scan_and_index(force=False)
    log.info(f"Codebase scan complete – {count} files updated.")