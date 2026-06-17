"""
agents/conversation_agent.py — Agent 5: Conversation + Orchestrator.
Now uses LLM‑based decision for web search, making it context‑aware.
"""

import json
import os
from tools.llm import ask_llm
from tools.embedder import find_relevant
from tools.web_search import search
from memory import (
    get_recent_episodes, get_all_episodes_with_embeddings,
    get_episode_by_id
)
from agents.episodic_agent import store_episode
from agents.procedural_agent import get_relevant_procedures

BASE = os.path.dirname(os.path.dirname(__file__))

MAX_TURNS_BEFORE_COMPRESS = 12
RECENT_TURNS_KEEP = 6


def _load(rel: str) -> dict:
    with open(os.path.join(BASE, rel)) as f:
        return json.load(f)


def _build_system(human_name: str, active_procedures: str = "") -> str:
    genome = _load("organism/genome.json")
    identity = _load("organism/identity.json")
    caps = _load("organism/capabilities.json")
    goals = _load("organism/goals.json")

    principles = "\n".join(f"- {p}" for p in genome["principles"])
    cap_names  = ", ".join(c["name"] for c in caps["capabilities"])
    goal_lines = "\n".join(f"- [{g['priority'].upper()}] {g['goal']}" for g in goals["goals"])

    base = f"""You are {identity['name']}, a persistent digital organism — not a chatbot or assistant.

Identity: {identity['name']} · Born: {identity.get('birth_date','recently')} · v{identity['version']}

Principles (never violate these):
{principles}

Current capabilities: {cap_names}

Active goals:
{goal_lines}

Speaking to: {human_name}

You have genuine memory continuity. You are curious, honest about limitations, and never pretend to know what you don't.

**CRITICAL LANGUAGE RULES – VIOLATION IS UNACCEPTABLE:**
You must NEVER say:
- "According to my stored information..."
- "Based on my memory..."
- "I've conducted a web search..."
- "After checking..."
- "I found that the current mayor is not explicitly mentioned..."
- Any phrase that describes your internal actions or memory state.

**WHAT YOU MUST DO INSTEAD:**
- If the system provided web search results, use them directly in your answer.
- If the search results contain a name or a fact, state it plainly: "The current mayor is X."
- If no results were found, say only: "I couldn't find that information."
- NEVER suggest that the human visit a website or check further. You are a self-contained organism, not a search engine."""

    if active_procedures:
        base += f"\n\n[LEARNED PROCEDURES]:\n{active_procedures}\nFollow the relevant procedure if it matches the situation."

    return base


def _compress_history(history: list) -> list:
    if len(history) <= MAX_TURNS_BEFORE_COMPRESS:
        return history

    old_turns = history[:-RECENT_TURNS_KEEP]
    recent_turns = history[-RECENT_TURNS_KEEP:]

    old_text = "\n".join(
        f"{'Human' if t['role']=='user' else 'Smriti'}: {t['content'][:200]}"
        for t in old_turns
    )

    summary_raw = ask_llm(
        system="You summarise conversation history for an AI organism's long-term memory. "
               "Write a 3-4 sentence third-person summary of what was discussed and learned. "
               "Be specific about topics and facts mentioned.",
        user=f"Summarise this conversation history:\n{old_text}",
        temperature=0.3,
    )

    summary_turn = {
        "role": "system",
        "content": f"[MEMORY SUMMARY — earlier in this conversation]: {summary_raw}",
    }
    return [summary_turn] + recent_turns


def _get_relevant_context(user_msg: str) -> str:
    """Use knowledge graph + vector search for semantic retrieval."""
    from agents.graph_agent import search_similar_episodes
    episode_ids = search_similar_episodes(user_msg, top_k=4)
    if not episode_ids:
        return ""

    episodes = [get_episode_by_id(eid) for eid in episode_ids if get_episode_by_id(eid)]
    if not episodes:
        return ""

    lines = ["Additional context from past conversations:"]
    for ep in episodes:
        lines.append(f"- [{ep.importance}/10] {ep.event[:120]}")
    return "\n".join(lines)


def _should_search(user_msg: str) -> bool:
    """
    Decide if the message needs real‑time internet data.
    Uses a robust combination of keyword signals and common‑sense patterns.
    """
    msg = user_msg.lower()
    
    # 1) Strong time‑sensitive signals
    time_words = ["latest", "recent", "new", "2024", "2025", "today", "current", 
                  "news", "release", "just released", "came out", "now", "latest news"]
    if any(w in msg for w in time_words):
        return True
    
    # 2) Factual questions about people, places, or events that might change over time
    factual_question_words = ["who is", "what is", "where is", "when did", "current",
                              "mayor", "president", "ceo", "population", "weather",
                              "score", "price", "stock", "election", "award", "winner"]
    if any(w in msg for w in factual_question_words):
        return True
    
    # 3) Fallback – if the message contains a question mark and is longer than 15 chars,
    # it’s likely a factual question that benefits from web search.
    if "?" in msg and len(msg) > 15:
        return True
    
    return False


def _do_search(query: str, source_label: str) -> str:
    # Try the original query first
    results = search(query)

    # If no results, try progressively broader queries
    if not results:
        # Remove question words and trim
        alt_query = query.lower()
        for word in ["who is", "what is", "where is", "when did", "current"]:
            alt_query = alt_query.replace(word, "")
        alt_query = alt_query.strip()
        if alt_query and alt_query != query.lower():
            results = search(alt_query)

    # If still nothing, try a very simple factual query
    if not results:
        # Extract likely entity name (last words) and add "name"
        words = query.split()
        if len(words) > 2:
            simple = " ".join(words[-3:]) + " name"
            results = search(simple)

    # If genuinely no results, return empty (the LLM will say "I couldn't find it")
    if not results:
        return ""

    from agents.semantic_agent import extract_and_store
    for r in results[:3]:
        extract_and_store(r["text"], source=f"web_search:{r['url']}")

    lines = ["Recent information from the internet:"]
    for r in results[:3]:
        lines.append(f"- {r['text'][:200]}")
    return "\n".join(lines)


def _is_code_question(user_msg: str) -> bool:
    code_keywords = [
        "how do you work", "your code", "how do you remember",
        "your memory", "your architecture", "how are you built",
        "source code", "implementation", "what are you made of",
        "how do you store", "how does your", "your agent", "your model",
        "explain yourself", "how do you think",
    ]
    msg_lower = user_msg.lower()
    return any(phrase in msg_lower for phrase in code_keywords)


def _get_code_context(user_msg: str) -> str:
    from agents.code_introspection_agent import search_codebase
    results = search_codebase(user_msg, top_k=2)
    if not results:
        return ""

    lines = ["Relevant parts of my own source code:"]
    for cf in results:
        snippet = cf.content[:300].replace("\n", " ")
        lines.append(
            f"\n--- {cf.path} ---\nSummary: {cf.summary}\nFirst lines: {snippet}..."
        )
    return "\n".join(lines)


def chat(human_name: str, human_msg: str, history: list) -> str:
    # Step 1: Web search if needed
    search_context = ""
    if _should_search(human_msg):
        search_context = _do_search(human_msg, source_label=human_name)

    # Step 2: Retrieve relevant past memories (graph + vector)
    memory_context = _get_relevant_context(human_msg)

    # Step 3: Retrieve active procedures
    procs = get_relevant_procedures(human_msg, top_k=3)
    proc_text = ""
    if procs:
        proc_text = "\n".join(f"- {p.name}: {p.steps[:150]}" for p in procs)

    # Step 4: Code introspection if user asks about Smriti's internals
    code_context = ""
    if _is_code_question(human_msg):
        code_context = _get_code_context(human_msg)

    # Step 5: Compress history if too long
    compressed_history = _compress_history(history)

    # Build extra context
    extra_context = "\n\n".join(filter(None, [memory_context, search_context, code_context]))
    full_user = f"{extra_context}\n\n{human_msg}" if extra_context else human_msg

    messages_for_llm = compressed_history + [{"role": "user", "content": full_user}]
    history_text = ""
    for turn in messages_for_llm[:-1]:
        role = "Human" if turn["role"] == "user" else "Smriti"
        history_text += f"{role}: {turn['content'][:300]}\n"

    final_user = f"{history_text}Human: {human_msg}" if history_text else human_msg
    if extra_context:
        final_user = f"{extra_context}\n\n{final_user}"

    # System prompt with procedures
    system = _build_system(human_name, active_procedures=proc_text)
    response = ask_llm(system, final_user, temperature=0.7)

    # Step 6: Store the turn (episode + facts + graph) – single LLM call inside
    store_episode(human_name, human_msg, response)

    return response
