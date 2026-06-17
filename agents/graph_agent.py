"""
agents/graph_agent.py — Agent 7: Knowledge Graph Maintainer.
Fixed: reuses database connections to avoid pool exhaustion on cloud.
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
    add_knowledge_node(
        "Episode", episode_id,
        {"importance": importance, "valence": valence, "tags": tags}
    )


def after_fact_added(fact_id: int, embedding_list: list, confidence: int,
                     valence: float, source_episode_id: int = None):
    """Create a Fact node and optionally link it to its source Episode."""
    fact_node_id = add_knowledge_node(
        "Fact", fact_id,
        {"confidence": confidence, "valence": valence}
    )
    if source_episode_id is not None:
        # Find the Episode node by type + ref_id and create a CONTAINS edge
        # Use a direct SQL query with the same connection pattern as the rest of the app
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
                    # Now add the edge within the same connection session
                    cur.execute(
                        "INSERT INTO knowledge_edges (source_node_id, target_node_id, relationship) "
                        "VALUES (%s, %s, %s)",
                        (row[0], fact_node_id, "CONTAINS")
                    )
                    conn.commit()
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
