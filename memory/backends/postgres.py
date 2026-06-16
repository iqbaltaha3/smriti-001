"""
memory/backends/postgres.py — PostgreSQL (Supabase) backend for Smriti-001.
Handles all structured memory tables, knowledge graph, and vector search.
Uses pgvector for embeddings.
"""
import os
import json
import datetime
from typing import Optional, List
import psycopg2
import psycopg2.pool
from memory.models import Episode, Fact, Reflection, Milestone, Inspection, Procedure, CodeFile

_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        # Read connection parameters individually (no DSN parsing issues)
        host = os.getenv("DB_HOST")
        port = int(os.getenv("DB_PORT", "6543"))
        dbname = os.getenv("DB_NAME", "postgres")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")

        if not all([host, user, password]):
            raise RuntimeError(
                "Missing database connection environment variables. "
                "Please set DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD in .env"
            )

        _pool = psycopg2.pool.SimpleConnectionPool(
            1, 10,
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            sslmode='require'
        )
    return _pool

def _get_conn():
    return _get_pool().getconn()

def _put_conn(conn):
    _get_pool().putconn(conn)

def init_all():
    """Create all tables and enable pgvector extension (idempotent)."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id SERIAL PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    human TEXT NOT NULL,
                    event TEXT NOT NULL,
                    summary TEXT DEFAULT '',
                    importance INTEGER DEFAULT 5,
                    tags TEXT DEFAULT '',
                    embedding vector(384),
                    valence REAL DEFAULT 0.0,
                    arousal REAL DEFAULT 0.0
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id SERIAL PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    fact TEXT NOT NULL,
                    source TEXT DEFAULT '',
                    confidence INTEGER DEFAULT 7,
                    category TEXT DEFAULT '',
                    embedding vector(384),
                    valence REAL DEFAULT 0.0,
                    arousal REAL DEFAULT 0.0
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reflections (
                    id SERIAL PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    trigger TEXT DEFAULT 'manual',
                    content TEXT DEFAULT '',
                    learned TEXT DEFAULT '',
                    weakness_found TEXT DEFAULT '',
                    cap_requested TEXT DEFAULT '',
                    principles_ok INTEGER DEFAULT 1
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS timeline (
                    id SERIAL PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    event_type TEXT DEFAULT '',
                    title TEXT DEFAULT '',
                    description TEXT DEFAULT ''
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS inspections (
                    id SERIAL PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    age_days INTEGER DEFAULT 0,
                    total_episodes INTEGER DEFAULT 0,
                    total_facts INTEGER DEFAULT 0,
                    total_reflections INTEGER DEFAULT 0,
                    capabilities_count INTEGER DEFAULT 0,
                    weaknesses_count INTEGER DEFAULT 0,
                    bottlenecks TEXT DEFAULT '',
                    recommendations TEXT DEFAULT '',
                    raw_report TEXT DEFAULT ''
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS procedures (
                    id SERIAL PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    name TEXT NOT NULL,
                    trigger TEXT DEFAULT '',
                    steps TEXT DEFAULT '',
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    last_used TEXT DEFAULT '',
                    embedding vector(384),
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS code_files (
                    id SERIAL PRIMARY KEY,
                    path TEXT NOT NULL UNIQUE,
                    content TEXT NOT NULL,
                    summary TEXT DEFAULT '',
                    embedding vector(384),
                    last_modified TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_nodes (
                    id SERIAL PRIMARY KEY,
                    type TEXT NOT NULL,
                    ref_id INTEGER NOT NULL,
                    properties JSONB DEFAULT '{}'
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_edges (
                    id SERIAL PRIMARY KEY,
                    source_node_id INTEGER REFERENCES knowledge_nodes(id),
                    target_node_id INTEGER REFERENCES knowledge_nodes(id),
                    relationship TEXT NOT NULL,
                    properties JSONB DEFAULT '{}'
                )
            """)
            # Create vector indexes (IVFFlat for approximate nearest neighbour)
            cur.execute("CREATE INDEX IF NOT EXISTS episodes_embedding_idx ON episodes USING ivfflat (embedding vector_cosine_ops)")
            cur.execute("CREATE INDEX IF NOT EXISTS facts_embedding_idx ON facts USING ivfflat (embedding vector_cosine_ops)")
            cur.execute("CREATE INDEX IF NOT EXISTS procedures_embedding_idx ON procedures USING ivfflat (embedding vector_cosine_ops)")
            cur.execute("CREATE INDEX IF NOT EXISTS code_files_embedding_idx ON code_files USING ivfflat (embedding vector_cosine_ops)")
        conn.commit()
    finally:
        _put_conn(conn)

# Episodic CRUD
def add_episode(ep: Episode) -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO episodes (timestamp,human,event,summary,importance,tags,embedding,valence,arousal) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (ep.timestamp, ep.human, ep.event, ep.summary,
                 ep.importance, ep.tags, ep.embedding, ep.valence, ep.arousal)
            )
            rid = cur.fetchone()[0]
            conn.commit()
            return rid
    finally:
        _put_conn(conn)

def get_recent_episodes(limit: int = 50) -> List[Episode]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM episodes ORDER BY id DESC LIMIT %s", (limit,))
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [Episode(**dict(zip(cols, row))) for row in rows]
    finally:
        _put_conn(conn)

def get_all_episodes_with_embeddings() -> List[Episode]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM episodes WHERE embedding IS NOT NULL ORDER BY id DESC")
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [Episode(**dict(zip(cols, row))) for row in rows]
    finally:
        _put_conn(conn)

def count_episodes() -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM episodes")
            return cur.fetchone()[0]
    finally:
        _put_conn(conn)

def get_episode_by_id(eid: int) -> Optional[Episode]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM episodes WHERE id = %s", (eid,))
            row = cur.fetchone()
            if row:
                cols = [desc[0] for desc in cur.description]
                return Episode(**dict(zip(cols, row)))
            return None
    finally:
        _put_conn(conn)

# Semantic CRUD
def add_fact(fact: Fact) -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO facts (timestamp,fact,source,confidence,category,embedding,valence,arousal) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (fact.timestamp, fact.fact, fact.source, fact.confidence,
                 fact.category, fact.embedding, fact.valence, fact.arousal)
            )
            rid = cur.fetchone()[0]
            conn.commit()
            return rid
    finally:
        _put_conn(conn)

def get_all_facts(limit: int = 100) -> List[Fact]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM facts ORDER BY id DESC LIMIT %s", (limit,))
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [Fact(**dict(zip(cols, row))) for row in rows]
    finally:
        _put_conn(conn)

def count_facts() -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM facts")
            return cur.fetchone()[0]
    finally:
        _put_conn(conn)

def get_fact_by_id(fid: int) -> Optional[Fact]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM facts WHERE id = %s", (fid,))
            row = cur.fetchone()
            if row:
                cols = [desc[0] for desc in cur.description]
                return Fact(**dict(zip(cols, row)))
            return None
    finally:
        _put_conn(conn)

# Reflection CRUD
def add_reflection(ref: Reflection) -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO reflections (timestamp,trigger,content,learned,weakness_found,cap_requested,principles_ok) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (ref.timestamp, ref.trigger, ref.content, ref.learned,
                 ref.weakness_found, ref.cap_requested, ref.principles_ok)
            )
            rid = cur.fetchone()[0]
            conn.commit()
            return rid
    finally:
        _put_conn(conn)

def get_recent_reflections(limit: int = 10) -> List[Reflection]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM reflections ORDER BY id DESC LIMIT %s", (limit,))
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [Reflection(**dict(zip(cols, row))) for row in rows]
    finally:
        _put_conn(conn)

def count_reflections() -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM reflections")
            return cur.fetchone()[0]
    finally:
        _put_conn(conn)

# Timeline CRUD
def add_milestone(m: Milestone) -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO timeline (timestamp,event_type,title,description) VALUES (%s,%s,%s,%s) RETURNING id",
                (m.timestamp, m.event_type, m.title, m.description)
            )
            rid = cur.fetchone()[0]
            conn.commit()
            return rid
    finally:
        _put_conn(conn)

def get_timeline() -> List[Milestone]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM timeline ORDER BY id ASC")
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [Milestone(**dict(zip(cols, row))) for row in rows]
    finally:
        _put_conn(conn)

# Inspection CRUD
def add_inspection(ins: Inspection) -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO inspections (timestamp,age_days,total_episodes,total_facts,total_reflections,"
                "capabilities_count,weaknesses_count,bottlenecks,recommendations,raw_report) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (ins.timestamp, ins.age_days, ins.total_episodes, ins.total_facts,
                 ins.total_reflections, ins.capabilities_count, ins.weaknesses_count,
                 ins.bottlenecks, ins.recommendations, ins.raw_report)
            )
            rid = cur.fetchone()[0]
            conn.commit()
            return rid
    finally:
        _put_conn(conn)

def get_recent_inspections(limit: int = 5) -> List[Inspection]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM inspections ORDER BY id DESC LIMIT %s", (limit,))
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [Inspection(**dict(zip(cols, row))) for row in rows]
    finally:
        _put_conn(conn)

# Procedure CRUD
def add_procedure(proc: Procedure) -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO procedures (timestamp,name,trigger,steps,success_count,failure_count,last_used,embedding,is_active) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (proc.timestamp, proc.name, proc.trigger, proc.steps,
                 proc.success_count, proc.failure_count, proc.last_used,
                 proc.embedding, proc.is_active)
            )
            rid = cur.fetchone()[0]
            conn.commit()
            return rid
    finally:
        _put_conn(conn)

def update_procedure(proc: Procedure) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE procedures SET name=%s, trigger=%s, steps=%s, success_count=%s, "
                "failure_count=%s, last_used=%s, embedding=%s, is_active=%s WHERE id=%s",
                (proc.name, proc.trigger, proc.steps, proc.success_count,
                 proc.failure_count, proc.last_used, proc.embedding, proc.is_active, proc.id)
            )
            conn.commit()
    finally:
        _put_conn(conn)

def get_all_procedures(active_only: bool = True) -> List[Procedure]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            if active_only:
                cur.execute("SELECT * FROM procedures WHERE is_active=TRUE ORDER BY id DESC")
            else:
                cur.execute("SELECT * FROM procedures ORDER BY id DESC")
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [Procedure(**dict(zip(cols, row))) for row in rows]
    finally:
        _put_conn(conn)

def get_all_procedures_with_embeddings() -> List[Procedure]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM procedures WHERE embedding IS NOT NULL AND is_active=TRUE ORDER BY id DESC")
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [Procedure(**dict(zip(cols, row))) for row in rows]
    finally:
        _put_conn(conn)

def get_procedure_by_id(pid: int) -> Optional[Procedure]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM procedures WHERE id = %s", (pid,))
            row = cur.fetchone()
            if row:
                cols = [desc[0] for desc in cur.description]
                return Procedure(**dict(zip(cols, row)))
            return None
    finally:
        _put_conn(conn)

# Codebase CRUD
def upsert_code_file(cf: CodeFile) -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO code_files (path, content, summary, embedding, last_modified) "
                "VALUES (%s,%s,%s,%s,%s) "
                "ON CONFLICT (path) DO UPDATE SET content=EXCLUDED.content, summary=EXCLUDED.summary, "
                "embedding=EXCLUDED.embedding, last_modified=EXCLUDED.last_modified "
                "RETURNING id",
                (cf.path, cf.content, cf.summary, cf.embedding, cf.last_modified)
            )
            rid = cur.fetchone()[0]
            conn.commit()
            return rid
    finally:
        _put_conn(conn)

def get_code_file_by_path(path: str) -> Optional[CodeFile]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM code_files WHERE path = %s", (path,))
            row = cur.fetchone()
            if row:
                cols = [desc[0] for desc in cur.description]
                return CodeFile(**dict(zip(cols, row)))
            return None
    finally:
        _put_conn(conn)

def get_all_code_files() -> List[CodeFile]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM code_files ORDER BY path ASC")
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [CodeFile(**dict(zip(cols, row))) for row in rows]
    finally:
        _put_conn(conn)

def get_all_code_files_with_embeddings() -> List[CodeFile]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM code_files WHERE embedding IS NOT NULL ORDER BY path ASC")
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [CodeFile(**dict(zip(cols, row))) for row in rows]
    finally:
        _put_conn(conn)

# Knowledge Graph CRUD
def add_knowledge_node(node_type: str, ref_id: int, properties: dict = None) -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO knowledge_nodes (type, ref_id, properties) VALUES (%s,%s,%s) RETURNING id",
                (node_type, ref_id, json.dumps(properties or {}))
            )
            rid = cur.fetchone()[0]
            conn.commit()
            return rid
    finally:
        _put_conn(conn)

def add_knowledge_edge(source_id: int, target_id: int, relationship: str, properties: dict = None) -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO knowledge_edges (source_node_id, target_node_id, relationship, properties) "
                "VALUES (%s,%s,%s,%s) RETURNING id",
                (source_id, target_id, relationship, json.dumps(properties or {}))
            )
            rid = cur.fetchone()[0]
            conn.commit()
            return rid
    finally:
        _put_conn(conn)

def get_all_knowledge_nodes() -> list:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM knowledge_nodes")
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [dict(zip(cols, row)) for row in rows]
    finally:
        _put_conn(conn)

def get_all_knowledge_edges() -> list:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM knowledge_edges")
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [dict(zip(cols, row)) for row in rows]
    finally:
        _put_conn(conn)

def vector_search_episodes(query_embedding: list, top_k: int = 4) -> List[int]:
    """Return episode IDs most similar to the query embedding using pgvector."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM episodes ORDER BY embedding <=> %s::vector LIMIT %s",
                (json.dumps(query_embedding), top_k)
            )
            return [row[0] for row in cur.fetchall()]
    finally:
        _put_conn(conn)

def vector_search_facts(query_embedding: list, top_k: int = 4) -> List[int]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM facts ORDER BY embedding <=> %s::vector LIMIT %s",
                (json.dumps(query_embedding), top_k)
            )
            return [row[0] for row in cur.fetchall()]
    finally:
        _put_conn(conn)