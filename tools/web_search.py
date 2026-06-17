"""
tools/web_search.py – AI‑powered web search using Tavily.
Falls back to DuckDuckGo + Wikipedia if no API key is set.
"""
import os
import requests

import streamlit as st
st.write("TAVILY_KEY present:", bool(os.getenv("TAVILY_API_KEY")))

TAVILY_URL = "https://api.tavily.com/search"

DISCOVERY_QUERIES = [
    "latest breakthroughs in AI language models",
    "new memory architectures for AI agents",
    "open source LLM tools released recently",
    "latest agent memory systems research",
    "new Python AI frameworks",
    "latest vector database advances",
    "living like a digital organism"
]


def search(query: str) -> list[dict]:
    """
    Search the web using Tavily.
    Returns list of {title, text, url} dicts.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        # Fallback to DuckDuckGo + Wikipedia (existing logic)
        return _search_fallback(query)

    try:
        resp = requests.post(
            TAVILY_URL,
            headers={"Content-Type": "application/json"},
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",       # "basic" for speed, "advanced" for depth
                "include_answer": True,        # Tavily returns a direct answer if possible
                "max_results": 5,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []

        # Tavily's direct answer (if available)
        if data.get("answer"):
            results.append({
                "title": "Answer",
                "text": data["answer"],
                "url": "",
            })

        # Search results
        for r in data.get("results", [])[:4]:
            results.append({
                "title": r.get("title", ""),
                "text": r.get("content", ""),
                "url": r.get("url", ""),
            })

        return results

    except Exception:
        return _search_fallback(query)


def _search_fallback(query: str) -> list[dict]:
    """Original DuckDuckGo + Wikipedia fallback."""
    import json
    import urllib.request
    import urllib.parse

    DDG_URL = "https://api.duckduckgo.com/"

    # DuckDuckGo
    try:
        params = urllib.parse.urlencode({
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        })
        with urllib.request.urlopen(f"{DDG_URL}?{params}", timeout=10) as r:
            data = json.loads(r.read())
        results = []
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", query),
                "text": data["AbstractText"],
                "url": data.get("AbstractURL", ""),
            })
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic["Text"][:60],
                    "text": topic["Text"],
                    "url": topic.get("FirstURL", ""),
                })
        if results:
            return results
    except Exception:
        pass

    # Wikipedia fallback
    try:
        import wikipedia
        clean = query.lower()
        for w in ["who is", "what is", "where is", "when did", "current", "latest", "today"]:
            clean = clean.replace(w, "")
        clean = clean.strip().rstrip("?")
        summary = wikipedia.summary(clean, sentences=2, auto_suggest=True)
        return [{"title": f"Wikipedia: {clean}", "text": summary, "url": ""}]
    except Exception:
        return []
