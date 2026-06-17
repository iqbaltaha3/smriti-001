"""
tools/web_search.py – Tavily-powered web search with Wikipedia fallback.
"""
import os, requests, wikipedia

TAVILY_URL = "https://api.tavily.com/search"

DISCOVERY_QUERIES = [
    "latest breakthroughs in AI language models 2025",
    "new memory architectures for AI agents",
    "open source LLM tools released recently",
    "agent memory systems research 2025",
    "new Python AI frameworks",
    "vector database advances",
]

def search(query: str) -> list[dict]:
    """Search using Tavily if key is set, otherwise fall back to Wikipedia."""
    api_key = os.getenv("TAVILY_API_KEY")
    if api_key:
        try:
            resp = requests.post(
                TAVILY_URL,
                headers={"Content-Type": "application/json"},
                json={
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "basic",
                    "include_answer": True,
                    "max_results": 5,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            if data.get("answer"):
                results.append({"title": "Answer", "text": data["answer"], "url": ""})
            for r in data.get("results", []):
                results.append({"title": r.get("title",""), "text": r.get("content",""), "url": r.get("url","")})
            if results:
                return results
        except Exception:
            pass   # fall through to Wikipedia

    # Wikipedia fallback – works for factual questions without any API key
    try:
        clean = query.lower()
        for w in ["who is","what is","where is","when did","current","latest","today"]:
            clean = clean.replace(w,"")
        clean = clean.strip().rstrip("?")
        # Search Wikipedia for the best matching article
        titles = wikipedia.search(clean, results=3)
        for title in titles:
            try:
                summary = wikipedia.summary(title, sentences=2, auto_suggest=False)
                return [{"title": f"Wikipedia: {title}", "text": summary, "url": f"https://en.wikipedia.org/wiki/{title.replace(' ','_')}"}]
            except wikipedia.exceptions.DisambiguationError as e:
                if e.options:
                    try:
                        summary = wikipedia.summary(e.options[0], sentences=2, auto_suggest=False)
                        return [{"title": f"Wikipedia: {e.options[0]}", "text": summary, "url": ""}]
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass

    return []   # genuinely nothing found
