# Smriti-001 — Persistent Memory Organism

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install and start Ollama
# Download from https://ollama.com
ollama pull gemma3:12b
ollama serve

# 3. Copy env file
cp .env.example .env

# 4. Run
streamlit run app.py
```

## File structure

```
smriti001/
├── app.py                        # Streamlit UI — entry point
├── requirements.txt
├── organism/                     # Identity files (JSON)
│   ├── genome.json               # Immutable principles
│   ├── identity.json             # Name, birth_date, version
│   ├── capabilities.json         # What Smriti can do
│   ├── weaknesses.json           # Known limitations
│   ├── goals.json                # Active objectives
│   └── evolution_requests.json   # Pending capability requests
├── memory/                       # 5 SQLite databases
│   ├── __init__.py               # All DB functions (CRUD)
│   ├── models.py                 # Pydantic models for every record
│   ├── episodic.db               # What happened
│   ├── semantic.db               # What I know
│   ├── reflections.db            # Self-analysis
│   ├── history.db                # Life milestones
│   └── inspections.db            # System health snapshots
├── agents/                       # 5 specialised agents
│   ├── semantic_agent.py         # Agent 1: maintains semantic memory
│   ├── episodic_agent.py         # Agent 2: maintains episodic memory
│   ├── reflection_agent.py       # Agent 3: reflection cycle
│   ├── inspection_agent.py       # Agent 4: system health
│   └── conversation_agent.py     # Agent 5: talks to human + orchestrates
├── tools/
│   ├── llm.py                    # Single LLM call (Ollama)
│   ├── embedder.py               # Sentence-transformer embeddings
│   └── web_search.py             # DuckDuckGo passive search
└── scheduler/
    └── jobs.py                   # Background scheduled tasks
```

## Agents

| Agent | File | Job |
|-------|------|-----|
| Semantic | agents/semantic_agent.py | Extract & store facts from any text |
| Episodic | agents/episodic_agent.py | Score, tag, embed each conversation turn |
| Reflection | agents/reflection_agent.py | Nightly self-analysis |
| Inspection | agents/inspection_agent.py | System health, bottleneck detection |
| Conversation | agents/conversation_agent.py | Talk to human, orchestrate others |

## Scheduled jobs

| Job | Schedule |
|-----|----------|
| Web discovery (AI news) | Every 4 hours |
| Nightly reflection | 23:00 daily |
| Morning inspection | 08:00 daily |
