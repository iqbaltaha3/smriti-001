"""
tools/web_search.py — Passive internet observation for Smriti-001.

DESIGN PHILOSOPHY:
  Smriti does NOT browse the internet autonomously or contact strangers.
  She OBSERVES only — like a scientist watching through a window.
  Results are stored as semantic memory (Facts) for reflection.

USES:
  - Conversation agent: answer questions requiring current info
  - Scheduler: hourly/daily background discovery runs

API: DuckDuckGo Instant Answer — completely free, no key required.
     Returns structured JSON with abstract text and related topics.
"""

import json
import urllib.request
import urllib.parse

DDG_URL = "https://api.duckduckgo.com/"


def search(query: str) -> list[dict]:
    """
    Search DuckDuckGo. Returns list of {title, text, url} dicts.
    Never raises — returns [] on any error so callers don't crash.
    """
    try:
        params = urllib.parse.urlencode({
            "q":            query,
            "format":       "json",
            "no_html":      "1",
            "skip_disambig": "1",
        })
        with urllib.request.urlopen(f"{DDG_URL}?{params}", timeout=10) as r:
            data = json.loads(r.read())

        results = []

        # The main abstract (usually the best result)
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", query),
                "text":  data["AbstractText"],
                "url":   data.get("AbstractURL", ""),
            })

        # Related topics (up to 5 more)
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic["Text"][:60],
                    "text":  topic["Text"],
                    "url":   topic.get("FirstURL", ""),
                })

        return results

    except Exception as e:
        # Never crash the caller — just return empty
        return [{"title": "search_error", "text": str(e), "url": ""}]


# ── Discovery queries — what Smriti searches during background runs ────────────
DISCOVERY_QUERIES = [
    "new AI language models 2025",
    "new memory architectures AI agents",
    "new open source LLM tools",
    "agent memory systems research",
    "new Python AI frameworks",
    "vector database advances",
]
