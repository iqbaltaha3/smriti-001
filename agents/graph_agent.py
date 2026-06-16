"""
Agent 7: Knowledge Graph Maintainer.
Uses Supabase PostgreSQL to store nodes and edges, and provides semantic search.
"""
import json
from tools.embedder import embed
from memory import (
    add_knowledge_node,
    add_knowledge_edge,
    vector_search_episodes,
    vector_search_facts,
)


def after_episode_added(episode_id: int, embedding_list: list, importance: int,
                        valence: float, tags: str, human_name: str):
    """Create an Episode node in the knowledge graph."""
    node_id = add_knowledge_node(
        "Episode", episode_id,
        {"importance": importance, "valence": valence, "tags": tags}
    )
    # For now we skip linking Human node; can be added later.


def after_fact_added(fact_id: int, embedding_list: list, confidence: int,
                     valence: float, source_episode_id: int = None):
    """Create a Fact node and optionally link it to its source Episode."""
    fact_node_id = add_knowledge_node(
        "Fact", fact_id,
        {"confidence": confidence, "valence": valence}
    )
    if source_episode_id is not None:
        # Find the Episode node by type + ref_id and create a CONTAINS edge
        from memory.backends.postgres import _get_conn, _put_conn
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM knowledge_nodes WHERE type='Episode' AND ref_id=%s",
                    (source_episode_id,)
                )
                row = cur.fetchone()
                if row:
                    add_knowledge_edge(row[0], fact_node_id, "CONTAINS")
        finally:
            _put_conn(conn)


def search_similar_episodes(query_text: str, top_k: int = 4) -> list[int]:
    """Semantic search over Episode embeddings using pgvector."""
    query_emb = json.loads(embed(query_text))
    return vector_search_episodes(query_emb, top_k)


def search_similar_facts(query_text: str, top_k: int = 4) -> list[int]:
    """Semantic search over Fact embeddings using pgvector."""
    query_emb = json.loads(embed(query_text))
    return vector_search_facts(query_emb, top_k)
