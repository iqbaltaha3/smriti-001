"""
scheduler/jobs.py – Idempotent background jobs for Smriti-001.
"""
import logging
from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler

from tools.web_search import search, DISCOVERY_QUERIES
from agents.semantic_agent import extract_and_store
from agents.reflection_agent import run_reflection
from agents.inspection_agent import run_inspection
from memory import add_milestone, get_recent_reflections, get_recent_inspections
from memory.models import Milestone

log = logging.getLogger("smriti.scheduler")


def discover():
    log.info("Starting discovery run...")
    total_facts = 0
    for query in DISCOVERY_QUERIES:
        results = search(query)
        for r in results[:2]:
            if r.get("text") and r["text"] != "" and "error" not in r["title"]:
                facts = extract_and_store(r["text"], source=f"web:{query}")
                total_facts += len(facts)
    log.info(f"Discovery run complete — {total_facts} facts stored")
    if total_facts > 0:
        m = Milestone(
            event_type="discovery",
            title="Internet observation run",
            description=f"Discovered {total_facts} new facts from web search",
        )
        add_milestone(m)


def nightly_reflect():
    """Run reflection only if no nightly reflection exists for today."""
    today = date.today().isoformat()
    recent = get_recent_reflections(5)
    # check if any reflection today with trigger='nightly'
    for r in recent:
        if r.trigger == "nightly" and r.timestamp[:10] == today:
            log.info("Nightly reflection already done today – skipping.")
            return
    log.info("Starting nightly reflection...")
    ref = run_reflection(trigger="nightly")
    log.info(f"Nightly reflection complete — id={ref.id}")


def morning_inspect():
    """Run inspection only if no inspection today."""
    today = date.today().isoformat()
    recent = get_recent_inspections(5)
    for ins in recent:
        if ins.timestamp[:10] == today:
            log.info("Morning inspection already done today – skipping.")
            return
    log.info("Starting morning inspection...")
    ins = run_inspection()
    log.info(f"Inspection complete — bottlenecks: {ins.bottlenecks}")


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(discover, "interval", hours=4, id="discover")
    scheduler.add_job(nightly_reflect, "cron", hour=23, minute=0, id="reflect")
    scheduler.add_job(morning_inspect, "cron", hour=8, minute=0, id="inspect")
    scheduler.start()
    log.info("Scheduler started — jobs: discover(4h), reflect(23:00), inspect(08:00)")
    return scheduler
