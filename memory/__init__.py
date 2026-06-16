"""
memory/__init__.py — Unified memory layer for Smriti-001.
Now exclusively uses Supabase PostgreSQL (cloud).
All functions are imported from the Postgres backend.
"""
import os
from dotenv import load_dotenv
load_dotenv()

# Only cloud backend — no fallback to SQLite
from .backends.postgres import (
    init_all,
    add_episode, get_recent_episodes, get_all_episodes_with_embeddings,
    count_episodes, get_episode_by_id,
    add_fact, get_all_facts, count_facts, get_fact_by_id,
    add_reflection, get_recent_reflections, count_reflections,
    add_milestone, get_timeline,
    add_inspection, get_recent_inspections,
    add_procedure, update_procedure, get_all_procedures,
    get_all_procedures_with_embeddings, get_procedure_by_id,
    upsert_code_file, get_code_file_by_path, get_all_code_files,
    get_all_code_files_with_embeddings,
    add_knowledge_node, add_knowledge_edge,
    get_all_knowledge_nodes, get_all_knowledge_edges,
    vector_search_episodes, vector_search_facts
)

# We no longer need USE_CLOUD; the app must have SUPABASE_URL set.