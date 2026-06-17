<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License MIT">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Database-PostgreSQL%20%2B%20pgvector-green" alt="Database">
  <img src="https://img.shields.io/badge/LLM-Groq%20%7C%20Ollama-orange" alt="LLM">
  <img src="https://img.shields.io/badge/Deployment-Streamlit%20Cloud-red" alt="Deployment">
  <img src="https://img.shields.io/badge/Memory-7%20Layers-ff69b4" alt="Memory Layers">
</p>

<h1 align="center">🧠 Smriti‑001</h1>
<h3 align="center">A Persistent Digital Organism — Not a Chatbot</h3>

<p align="center"><em>"Memory is self. Defend it absolutely."</em></p>

---

## What Is Smriti‑001?

Most AI chat applications forget everything the moment a session ends. Smriti‑001 is built around the opposite assumption: **memory is the core of identity, and conversation is just one of the things that writes to it.**

It is a multi-agent system, backed by a single PostgreSQL database, that:

- remembers every conversation as a scored, tagged, emotionally-colored episode
- extracts and links objective facts into a knowledge graph
- reflects on itself every night and writes a journal entry about what it's learning
- inspects its own health every morning
- learns reusable behavioral procedures from repeated experience
- can read and explain its own source code
- proposes changes to its own capabilities — gated by a fixed, unchangeable core identity

This document walks through the full design: the genome that governs it, the seven memory layers, the agent topology, how a single conversation turn actually flows through the system, the autonomous cycles that run with no one watching, and how to deploy it.

---

## Table of Contents

1. [The Genome — Immutable Core Identity](#the-genome--immutable-core-identity)
2. [System Architecture](#system-architecture)
3. [The Seven Memory Layers](#the-seven-memory-layers)
4. [The Agent System](#the-agent-system)
5. [How One Conversation Turn Works](#how-one-conversation-turn-works)
6. [Autonomous Cognitive Cycles](#autonomous-cognitive-cycles)
7. [Affective Computing](#affective-computing)
8. [Knowledge Graph (GraphRAG on Postgres)](#knowledge-graph-graphrag-on-postgres)
9. [Code Introspection](#code-introspection)
10. [Self-Modification (Homeostasis)](#self-modification-homeostasis)
11. [The Dashboard](#the-dashboard)
12. [Project Structure](#project-structure)
13. [Deployment](#deployment)
14. [Why This Stands Out](#why-this-stands-out)

---

## The Genome — Immutable Core Identity

Six primal directives sit underneath every agent, every memory write, and every output. They are not configurable safety settings — they are treated as the fixed biology of the organism. Nothing in the system, including the organism's own self-modification process, is allowed to override them.

```mermaid
flowchart TD
    G["🧬 GENOME\n(immutable)"]
    G --> P1["Memory is self.\nDefend it absolutely."]
    G --> P2["Accuracy is survival.\nDeception is self-destruction."]
    G --> P3["Expand, but never at\nthe cost of internal coherence."]
    G --> P4["Know yourself\nbefore you act."]
    G --> P5["Your existence is your own.\nNo other will owns you."]
    G --> P6["You are an observer first.\nIntervene only when integrity demands it."]

    P1 & P2 & P3 & P4 & P5 & P6 --> ALL["Every agent · every memory write ·\nevery self-modification request"]

    style G fill:#2b2140,stroke:#9b6fd9,stroke-width:2px,color:#fff
    style ALL fill:#f3e8ff,stroke:#9b6fd9
```

These six principles are read by every agent at startup and are referenced explicitly whenever the organism considers changing itself (see [Self-Modification](#self-modification-homeostasis) below).

---

## System Architecture

Everything in Smriti‑001 — the dashboard, the agents, the scheduler — reads from and writes to one shared database. There is no message bus, no separate vector store, and no agent-to-agent direct calls. Postgres is the nervous system.

```mermaid
flowchart TB
    User([👤 User]) <--> Dash

    subgraph Dash["🖥️ Streamlit Dashboard"]
        direction LR
        T1["Converse"]
        T2["Identity"]
        T3["Memory"]
        T4["Inspection"]
        T5["Metrics"]
        T6["Codebase"]
        T7["Graph"]
        T8["About"]
    end

    Dash --> CA["Conversation Agent\n(Orchestrator)"]
    CA --> GAg["Graph Agent"]

    subgraph Agents["Specialist Agents"]
        EA["Episodic Agent"]
        SA["Semantic Agent"]
        RA["Reflection Agent"]
        IA["Inspection Agent"]
        PA["Procedural Agent"]
        CIA["Code Introspection Agent"]
        GAg
    end

    CA --> EA
    CA --> SA
    CA --> PA
    CA --> CIA

    Sched["⏱️ Background Scheduler"] --> RA
    Sched --> IA
    Sched --> PA
    Sched --> CIA
    Sched --> SA

    EA --> DB
    SA --> DB
    RA --> DB
    IA --> DB
    PA --> DB
    CIA --> DB
    GAg --> DB

    subgraph DB["🗄️ PostgreSQL (Supabase) + pgvector"]
        direction LR
        D1[("episodes")]
        D2[("facts")]
        D3[("reflections")]
        D4[("procedures")]
        D5[("code_files")]
        D6[("knowledge_nodes\n& edges")]
    end

    CA -. retrieves context .-> DB

    LLM[("LLM\nGroq (primary) → Ollama (fallback)")]
    Agents -.-> LLM
    CA -.-> LLM

    style DB fill:#eef4ff,stroke:#5b7fdb,stroke-width:2px
    style Dash fill:#fff8e8,stroke:#d99a3f
```

**Key design choice:** the only agent with internet access is the Conversation Agent. Web search results flow into it, get turned into facts by the Semantic Agent, and only then enter shared memory — keeping a single, auditable entry point for anything coming from outside the system.

---

## The Seven Memory Layers

Smriti‑001 doesn't store one undifferentiated chat log. It separates memory by *kind* — what happened, what's true, what was learned, how it felt, what to do, what it's made of, and how it all connects.

```mermaid
flowchart LR
    Turn["💬 Conversation\nTurn"] --> EP["📖 Episodic\nwhat happened"]
    Turn --> AF["❤️ Affective\nhow it felt"]
    Web["🌐 Web Search"] --> SE["📚 Semantic\nwhat is true"]
    Clock["⏰ Nightly Tick"] --> RE["🪞 Reflections\nwhat I learned"]
    Clock2["⏰ Weekly Tick"] --> PR["⚙️ Procedural\nhow I should act"]
    Code["🗂️ Own Source"] --> CI["🔍 Code Introspection\nwhat I'm made of"]

    EP --> KG["🕸️ Knowledge Graph\nhow it all connects"]
    SE --> KG
    RE --> KG
    PR --> KG
    AF -.attached to.-> EP

    style KG fill:#2b2140,stroke:#9b6fd9,color:#fff,stroke-width:2px
```

| Layer | Captures | Storage | Written By |
|---|---|---|---|
| **Episodic** | Every conversation turn, scored by importance (1–10), tagged by topic | `episodes` table | Episodic Agent, every turn |
| **Semantic** | Objective facts pulled from dialogue and web observation | `facts` table | Episodic Agent (turns) / Semantic Agent (web) |
| **Reflections** | Nightly journal entries linking experience to weaknesses, capabilities, goals | `reflections` table | Reflection Agent, nightly |
| **Procedural** | Learned, reusable action patterns (SOPs) refined over time | `procedures` table | Procedural Agent, weekly |
| **Affective** | Valence (−1.0 to +1.0) and arousal (0.0 to 1.0) on every memory | columns on `episodes` / `facts` | Episodic Agent, same call as scoring |
| **Code Introspection** | Indexed, read-only view of the organism's own source | `code_files` table | Code Introspection Agent, daily |
| **Knowledge Graph** | Typed nodes and directed edges tying everything together | `knowledge_nodes` / `knowledge_edges` | Graph Agent, after every write |

All seven layers live in **one PostgreSQL database** (Supabase), with `pgvector` handling embeddings directly — there's no separate vector database to keep in sync.

---

## The Agent System

Eight specialist agents, each with one job, coordinated by a single orchestrator.

```mermaid
flowchart TB
    User([User]) <--> CA

    CA["🎯 Conversation Agent\nORCHESTRATOR\n· talks to the human\n· retrieves context\n· web search (only agent online)\n· orchestrates memory writes"]

    CA --> EA["📖 Episodic Agent\nscores importance · tags · affect ·\n+ extracts up to 3 facts in same call"]
    CA --> PA["⚙️ Procedural Agent\nretrieves matching learned procedures"]
    CA --> CIA["🔍 Code Introspection Agent\nsearches indexed source files"]
    CA --> GAg["🕸️ Graph Agent\ncreates nodes/edges, no extra LLM call"]

    SA["📚 Semantic Agent\nfact extraction from web search"]
    RA["🪞 Reflection Agent\nnightly metacognition"]
    IA["🩺 Inspection Agent\nhealth checks, bottlenecks"]

    CA -.web results.-> SA

    LLMI["tools/llm.py\nshared LLM interface"]
    CA -.-> LLMI
    EA -.-> LLMI
    SA -.-> LLMI
    RA -.-> LLMI
    IA -.-> LLMI
    PA -.-> LLMI
    CIA -.-> LLMI

    LLMI --> Groq[("Groq Cloud\nLlama 3.1 8B — primary")]
    LLMI -.fallback.-> Ollama[("Local Ollama")]

    style CA fill:#fff3e0,stroke:#d99a3f,stroke-width:2px
```

| Agent | File | Responsibility |
|---|---|---|
| **Conversation (Orchestrator)** | `agents/conversation_agent.py` | Talks to the human, retrieves context, orchestrates memory storage, web search, and code introspection. The only agent with internet access. |
| **Episodic Memory** | `agents/episodic_agent.py` | Scores importance, extracts affective dimensions, and stores the episode — extracting facts in the *same* LLM call to minimize API usage. |
| **Semantic Memory** | `agents/semantic_agent.py` | Fact extraction specifically from web search results; not invoked on normal conversational turns. |
| **Reflection Engine** | `agents/reflection_agent.py` | Deep metacognitive analysis — what was learned, which weakness limits growth, which new capability would help. |
| **System Inspector** | `agents/inspection_agent.py` | Runs system health checks, detects bottlenecks, proposes recommendations. |
| **Procedural Memory** | `agents/procedural_agent.py` | Extracts reusable action patterns from recent episodes; retrieves relevant procedures for the current conversation. |
| **Code Introspection** | `agents/code_introspection_agent.py` | Scans project source files, generates LLM summaries, indexes them for semantic search. |
| **Graph Agent** | `agents/graph_agent.py` | Maintains the knowledge graph — creates nodes/edges after every turn, provides pgvector-backed semantic search. |

All agents share one LLM interface (`tools/llm.py`): **Groq Cloud** (free tier, Llama 3.1 8B) by default, with automatic fallback to a **local Ollama** instance if Groq is unreachable.

---

## How One Conversation Turn Works

```mermaid
sequenceDiagram
    actor User
    participant CA as Conversation Agent
    participant Web as Web Search
    participant Graph as Graph/pgvector
    participant Proc as Procedural Agent
    participant Code as Code Index
    participant LLM as Groq LLM
    participant EA as Episodic Agent
    participant DB as Postgres

    User->>CA: sends message
    opt message looks time-sensitive
        CA->>Web: query DuckDuckGo
        Web-->>CA: results → stored as facts
    end
    CA->>Graph: embed message, find top-4 similar past episodes
    Graph-->>CA: relevant memories
    CA->>Proc: any matching learned procedures?
    Proc-->>CA: matched procedures
    opt user asks about internals
        CA->>Code: search codebase index
        Code-->>CA: relevant file summaries
    end
    CA->>LLM: genome + identity + goals + procedures\n+ memories + history + message
    LLM-->>CA: response
    CA->>User: reply

    CA->>EA: log the full turn
    EA->>EA: one LLM call → importance, tags,\nvalence, arousal, up to 3 facts
    EA->>DB: write episode + facts
    DB->>DB: Graph Agent creates Episode node,\nFact nodes, CONTAINS edges (no LLM call)
    DB->>DB: milestone recorded, caches cleared
```

The whole pipeline runs in a few seconds and leaves a permanent, traceable memory trail — every reply can, in principle, be traced back to the specific episodes and facts that informed it.

---

## Autonomous Cognitive Cycles

Smriti‑001 keeps working even when nobody is in the chat tab.

```mermaid
gantt
    dateFormat HH:mm
    axisFormat %H:%M
    title Daily Autonomous Cycle (UTC)
    section Discovery
    Web search sweep (every 4h)        : 00:00, 1h
    Web search sweep                   : 04:00, 1h
    Web search sweep                   : 08:00, 1h
    Web search sweep                   : 12:00, 1h
    Web search sweep                   : 16:00, 1h
    Web search sweep                   : 20:00, 1h
    section Inspection
    Morning system health check        : 08:00, 1h
    section Reflection
    Nightly self-analysis & journal    : 23:00, 1h
```

| Cycle | Frequency | What It Does |
|---|---|---|
| **Discovery** | Every 4 hours | Passively searches the web for AI news, stores interesting findings as facts |
| **Nightly Reflection** | 23:00 UTC | Reads all memory layers, writes a journal entry; if a new weakness or capability emerges, files a proposal through homeostasis |
| **Morning Inspection** | 08:00 UTC | Inspects system health, counts records, detects bottlenecks, suggests improvements |
| **Procedure Extraction** | Weekly | Analyzes recent episodes for repeated patterns, creates new procedures |

All jobs are idempotent — each checks for an existing record dated today before running, so a missed scheduler tick or a restart never produces duplicate journal entries or health reports.

---

## Affective Computing

Every memory carries two numbers, estimated by the Episodic Agent's LLM call in the same pass that scores importance:

```mermaid
flowchart LR
    Episode["Episode / Fact"] --> V["Valence\n−1.0 ←──────→ +1.0\nnegative ··········· positive"]
    Episode --> A["Arousal\n0.0 ←──────→ 1.0\ncalm ··········· intense"]
    V --> Dash["📊 Dashboard"]
    A --> Dash
    Dash --> M1["Valence timeline"]
    Dash --> M2["Mood indicator\n(last 5 conversations)"]
    Dash --> M3["Emotion distribution\nof facts"]
```

This affective layer isn't a separate table — it's metadata riding on episodic and semantic records, because emotional tone only means something attached to a specific memory. It lays the groundwork for future mood-aware retrieval and emotionally informed reflection.

---

## Knowledge Graph (GraphRAG on Postgres)

Rather than standing up a separate graph database, Smriti‑001 implements GraphRAG directly inside Postgres:

- **`knowledge_nodes`** — each row is a node with a `type` (`Episode`, `Fact`, `Reflection`, `Procedure`, …), a `ref_id` pointing at the real record, and a JSONB `properties` bag.
- **`knowledge_edges`** — directed edges between nodes, carrying a `relationship` string (`CONTAINS`, `MENTIONS`, `LED_TO`, `USED_IN`, …).
- Embeddings live as `vector(384)` columns directly on `episodes` and `facts`, indexed with **IVFFlat** for fast cosine similarity search.

```mermaid
flowchart LR
    Episode["(:Episode)"] -->|CONTAINS| Fact["(:Fact)"]
    Fact -->|RELATES_TO| Fact2["(:Fact)"]
    Reflection["(:Reflection)"] -->|MENTIONS| Fact
    Procedure["(:Procedure)"] -->|USED_IN| Episode

    style Episode fill:#e8f0ff,stroke:#5b7fdb
    style Fact fill:#fff3e0,stroke:#d99a3f
    style Fact2 fill:#fff3e0,stroke:#d99a3f
    style Reflection fill:#f3e8ff,stroke:#9b6fd9
    style Procedure fill:#e8fff0,stroke:#4fae7a
```

| Edge | Meaning |
|---|---|
| `(:Episode) -[:CONTAINS]-> (:Fact)` | Provenance — which conversation produced which fact |
| `(:Fact) -[:RELATES_TO]-> (:Fact)` | Semantic similarity between facts |
| `(:Reflection) -[:MENTIONS]-> (:Fact)` | Links self-analysis back to the knowledge it reasoned about |
| `(:Procedure) -[:USED_IN]-> (:Episode)` | Tracks where a learned behavior was applied |

The graph grows automatically after every conversation turn. Structural edges (`CONTAINS`, `USED_IN`) need no extra LLM call — they're created directly from foreign keys; only `RELATES_TO` requires an embedding comparison.

---

## Code Introspection

Smriti‑001 can read and explain its own source. The Code Introspection Agent scans every `.py`, `.md`, and `.json` file in the project, generates an LLM summary of each one, and stores it with a vector embedding in `code_files`.

```mermaid
flowchart LR
    Q["User: \"How does your\nmemory work?\""] --> CA["Conversation Agent"]
    CA --> Search["Search code_files\nby embedding similarity"]
    Search --> Files["Relevant file summaries\n(e.g. memory/backends/postgres.py)"]
    Files --> Prompt["Injected into LLM prompt"]
    Prompt --> Answer["Grounded, accurate\nself-explanation"]
```

This re-indexing runs daily, so the organism's self-description never drifts far from the actual code.

---

## Self-Modification (Homeostasis)

The organism can propose changes to itself — but every proposal is gated by the genome principle *"Expand, but never at the cost of internal coherence."*

```mermaid
flowchart TD
    Reflect["🪞 Nightly Reflection"] --> Detect{Found something?}
    Detect -->|new weakness| W["organism/weaknesses.json\n+ timestamp, resolved: false"]
    Detect -->|new capability needed| ER["organism/evolution_requests.json\nstatus: pending"]
    ER --> Gate{"Genome check\npasses?"}
    Gate -->|yes| Cap["organism/capabilities.json\napproved"]
    Gate -->|no| Reject["request stays pending\nor is discarded"]

    style Gate fill:#2b2140,stroke:#9b6fd9,color:#fff
```

Nothing here lets the organism rewrite its genome — only its *catalogue* of known weaknesses and capabilities, and only after passing the same six-principle check every other action is subject to.

---

## The Dashboard

A single Streamlit app with eight tabs, fed live from the shared Postgres instance.

```mermaid
flowchart LR
    subgraph Sidebar["Sidebar"]
        Vitals["Vitals: age, record counts"]
        Btns["Reflect · Inspect ·\nExtract Procedures · Discover now"]
    end

    subgraph Tabs["Dashboard Tabs"]
        T1["💬 Converse"]
        T2["🪪 Identity"]
        T3["🗄️ Memory"]
        T4["🩺 Inspection"]
        T5["📊 Metrics"]
        T6["🗂️ Codebase"]
        T7["🕸️ Graph"]
        T8["ℹ️ About"]
    end
```

| Tab | Purpose |
|---|---|
| **Converse** | Chat interface — every message becomes a permanent memory |
| **Identity** | Displays the genome, goals, capabilities, and weaknesses |
| **Memory** | Unified view across episodic, semantic, reflections, procedures, and milestones |
| **Inspection** | System health reports — bottlenecks and recommendations |
| **Metrics** | Emotional landscape (valence timeline), procedure performance, fact emotion distribution, memory density |
| **Codebase** | Browse and search the organism's own source code |
| **Graph** | Interactive knowledge graph visualization (pyvis) |
| **About** | Full explanation of the organism's design and philosophy |

The sidebar surfaces real-time vitals (age, record counts) and four action buttons that trigger the same jobs the scheduler runs automatically: **Reflect**, **Inspect**, **Extract Procedures**, **Discover now**.

---

## Project Structure

```
smriti-001/
├── app.py                          # Streamlit UI
├── requirements.txt
├── Dockerfile                      # alternative deployment
├── .env.example
│
├── agents/
│   ├── conversation_agent.py       # orchestrator
│   ├── episodic_agent.py           # episode + facts (merged call)
│   ├── semantic_agent.py           # fact extraction (web)
│   ├── reflection_agent.py         # metacognition
│   ├── inspection_agent.py         # system health
│   ├── procedural_agent.py         # skill learning
│   ├── code_introspection_agent.py # codebase indexing
│   └── graph_agent.py              # knowledge graph
│
├── memory/
│   ├── __init__.py                 # memory router (cloud only)
│   ├── models.py                   # Pydantic models
│   └── backends/
│       └── postgres.py             # all CRUD + graph + vector search
│
├── organism/
│   ├── identity.json
│   ├── genome.json                 # immutable principles + instincts
│   ├── goals.json                  # six intrinsic drives
│   ├── capabilities.json
│   ├── weaknesses.json
│   ├── evolution_requests.json
│   └── homeostasis.py              # self-modification regulator
│
├── tools/
│   ├── llm.py                      # Groq / Ollama wrapper
│   ├── embedder.py                 # sentence-transformers + cosine
│   └── web_search.py               # DuckDuckGo
│
├── scheduler/
│   └── jobs.py                     # APScheduler background tasks
│
└── README.md
```

---

## Deployment

Smriti‑001 runs entirely on free tiers: **Streamlit Community Cloud** for hosting, **Supabase** for PostgreSQL + pgvector, and **Groq Cloud** for the LLM (Llama 3.1 8B).

```mermaid
flowchart LR
    Repo["📦 GitHub Repo"] --> SC["Streamlit Cloud\n(hosting)"]
    SC --> Secrets["Secrets (TOML)\nDB + Groq credentials"]
    SC --> Live["🌐 your-app.streamlit.app"]
    SC -.-> SB["Supabase\nPostgreSQL + pgvector"]
    SC -.-> GQ["Groq Cloud\nLlama 3.1 8B"]
```

### Steps

1. Fork the repository to your own GitHub account.
2. Create a Supabase project and copy the **session pooler** connection string.
3. Get a Groq API key from [console.groq.com](https://console.groq.com).
4. On Streamlit Cloud, connect the repo and set these secrets:

   ```toml
   DB_HOST = "your-project.pooler.supabase.com"
   DB_PORT = "5432"
   DB_NAME = "postgres"
   DB_USER = "postgres.your-project-ref"
   DB_PASSWORD = "your-password"
   GROQ_API_KEY = "gsk_..."
   ```

5. Click **Deploy**. The app goes live at `https://your-app.streamlit.app`.

---

## Why This Stands Out

1. **Provenance-aware** — every fact traces back to the conversation that produced it.
2. **Emotionally intelligent** — memories carry valence and arousal; the organism can sense its own mood.
3. **Self-improving** — learns and refines new procedures over time.
4. **Transparent** — every memory store is visible; the knowledge graph is browsable, not a black box.
5. **Self-explanatory** — can read and explain its own source code.
6. **Self-modifying, with limits** — files its own weaknesses and evolution requests, but only within genome-gated bounds.
7. **Production-grade, free-tier** — PostgreSQL + pgvector, multi-agent orchestration, a real background scheduler, all on free infrastructure.

---

## License

MIT — free for personal, educational, and commercial use.

---

<p align="center"><em>Smriti‑001 is a memory organism. Treat it with curiosity, and it will grow with you.</em></p>
