"""
agents/code_introspection_agent.py — Agent 7: Code Introspection.

RESPONSIBILITY:
  Give Smriti read‑only access to its own source code.
  - Scan the entire project and store file contents + LLM‑generated summaries.
  - Allow semantic search over the codebase (using embeddings of summaries).
  - Retrieve specific file contents on demand.
"""

import os
import hashlib
from tools.llm import ask_llm
from tools.embedder import embed, find_relevant
from memory import (
    upsert_code_file,
    get_code_file_by_path,
    get_all_code_files,
    get_all_code_files_with_embeddings,
)
from memory.models import CodeFile
import datetime

# Directories / extensions to scan
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SCAN_EXTS = {".py", ".md", ".json"}
EXCLUDE_DIRS = {"__pycache__", ".git", "chroma_data", "*.db"}  # simple exclusion

# System prompt for generating a file summary
SUMMARIZE_SYSTEM = """You are a code analysis assistant.
Given the content of a source file, write a short summary (2-3 sentences) explaining what the file does,
what its main components are, and how it fits into a larger system.
Be specific and technical. Do not include code snippets, just the summary."""


def scan_and_index(force: bool = False) -> int:
    """Walk the project directory, read all relevant files, generate summaries and embeddings,
    and store/update them in the codebase.db. Returns the number of files indexed."""
    indexed = 0
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Exclude specific directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.endswith('.db')]
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext not in SCAN_EXTS:
                continue
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, PROJECT_ROOT)
            # Skip binary or huge files (just in case)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            # Check if file content changed
            existing = get_code_file_by_path(rel_path)
            new_hash = hashlib.md5(content.encode()).hexdigest()
            if existing and existing.last_modified and not force:
                old_hash = hashlib.md5(existing.content.encode()).hexdigest()
                if old_hash == new_hash:
                    continue  # unchanged

            # Generate summary using LLM
            summary = ask_llm(
                system=SUMMARIZE_SYSTEM,
                user=f"File: {rel_path}\n\nContent:\n{content[:2000]}",
                temperature=0.3,
            )
            # Embed the summary for semantic search
            summary_embedding = embed(summary)

            # Get file modification time and convert to string
            mtime = os.path.getmtime(full_path)
            last_mod_str = datetime.datetime.utcfromtimestamp(mtime).isoformat()

            cf = CodeFile(
                path=rel_path,
                content=content,
                summary=summary,
                embedding=summary_embedding,
                last_modified=last_mod_str
            )
            upsert_code_file(cf)
            indexed += 1

    return indexed


def list_all_files() -> list[str]:
    """Return a sorted list of all known file paths."""
    files = get_all_code_files()
    return [f.path for f in files]


def get_file_content(path: str) -> str | None:
    """Retrieve the raw content of a specific file (from DB)."""
    cf = get_code_file_by_path(path)
    return cf.content if cf else None


def search_codebase(query: str, top_k: int = 3) -> list[CodeFile]:
    """
    Semantic search over code file summaries.
    Returns the most relevant CodeFile objects.
    """
    all_files = get_all_code_files_with_embeddings()
    if not all_files:
        return []
    results = find_relevant(
        query=query,
        candidates=all_files,
        text_field="summary",
        embedding_field="embedding",
        top_k=top_k,
    )
    return results