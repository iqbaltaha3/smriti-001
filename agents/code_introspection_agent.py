"""
Agent 7: Code Introspection.
Scans project files, generates summaries with the LLM, and indexes them.
Now with per‑file error handling and progress reporting.
"""

import os
import hashlib
import datetime
from tools.llm import ask_llm
from tools.embedder import embed
from memory import (
    upsert_code_file,
    get_code_file_by_path,
    get_all_code_files,
    get_all_code_files_with_embeddings,
)
from memory.models import CodeFile

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SCAN_EXTS = {".py", ".md", ".json"}
EXCLUDE_DIRS = {"__pycache__", ".git", "chroma_data"}

SUMMARIZE_SYSTEM = """You are an expert code analyst. 
You are not independent, you are part of a "persistent memory organism" called "smriti-001".
The code that you will always analyze is smriti-001's codebase.

Given the content of a source file, write a sentence summary that covers:
1) what the file does at a high level.
2) the main classes, functions, or patterns.
3) how this file connects to the larger architecture.

Be specific, very technical, and direct. Do not include code, just the summary."""


def scan_and_index(force: bool = False, progress_callback=None) -> dict:
    """
    Walk the project directory, read all relevant files, generate summaries and embeddings,
    and store/update them in the codebase.db.
    Returns a dict with 'indexed', 'errors', and 'skipped' counts.
    """
    stats = {"indexed": 0, "errors": 0, "skipped": 0}
    files_to_process = []

    # Collect all files first (so we can show total count)
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.endswith('.db')]
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in SCAN_EXTS:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, PROJECT_ROOT)
                files_to_process.append((full_path, rel_path))

    total = len(files_to_process)

    for idx, (full_path, rel_path) in enumerate(files_to_process):
        if progress_callback:
            progress_callback(idx + 1, total, rel_path)

        # Check if file content changed
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            stats["errors"] += 1
            continue

        existing = get_code_file_by_path(rel_path)
        new_hash = hashlib.md5(content.encode()).hexdigest()
        if existing and not force:
            old_hash = hashlib.md5(existing.content.encode()).hexdigest() if existing.content else ""
            if old_hash == new_hash:
                stats["skipped"] += 1
                continue

        # Try to get LLM summary (wrap in try/catch so one failure doesn't kill scan)
        try:
            summary = ask_llm(
                system=SUMMARIZE_SYSTEM,
                user=f"File: {rel_path}\n\nContent:\n{content[:2000]}",
                temperature=0.3,
            )
        except Exception:
            # If LLM fails, use a simple fallback summary
            summary = f"Source file {rel_path} (LLM summary unavailable)"

        # Embed the summary
        summary_embedding = embed(summary)

        # Convert file modification time to ISO string
        mtime = os.path.getmtime(full_path)
        last_mod_str = datetime.datetime.fromtimestamp(
            mtime, tz=datetime.timezone.utc
        ).isoformat()

        cf = CodeFile(
            path=rel_path,
            content=content,
            summary=summary,
            embedding=summary_embedding,
            last_modified=last_mod_str,
        )
        upsert_code_file(cf)
        stats["indexed"] += 1

    return stats


def list_all_files() -> list[str]:
    files = get_all_code_files()
    return [f.path for f in files]


def get_file_content(path: str) -> str | None:
    cf = get_code_file_by_path(path)
    return cf.content if cf else None


def search_codebase(query: str, top_k: int = 3) -> list[CodeFile]:
    from tools.embedder import find_relevant
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
