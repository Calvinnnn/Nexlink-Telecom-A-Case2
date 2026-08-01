"""
Chunking + indexing for the Nextlink troubleshooting knowledge base.

Source: rag/data/troubleshooting_kb.md -- an unstructured NOC reference
document. This is NOT the same thing as the structured `db.py` tables
(accounts, tickets, equipment). It's prose written by engineers, meant to
be read by a human, that our existing tools have no way to query.

Chunking strategy: split on markdown "## " section headers. Each section
is a self-contained topic (one error code, one policy note), which makes
it a natural retrieval unit -- we don't want to return half of an error
code's explanation and cut off the actionable part.
"""

import os
from keyword_search import KeywordStore

_KB_PATH = os.path.join(os.path.dirname(__file__), "data", "troubleshooting_kb.md")

knowledge_store = KeywordStore()


def _chunk_markdown_by_section(text: str) -> list[dict]:
    chunks = []
    current_title = None
    current_lines: list[str] = []

    def flush():
        if current_title is not None and current_lines:
            body = "\n".join(current_lines).strip()
            if body:
                chunks.append({"title": current_title, "text": f"## {current_title}\n\n{body}"})

    for line in text.splitlines():
        if line.startswith("## "):
            flush()
            current_title = line[3:].strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)
    flush()
    return chunks


def index_knowledge_base(path: str = _KB_PATH) -> int:
    """Loads the KB doc, chunks it by section, and indexes each chunk.

    Returns the number of chunks indexed. Safe to call more than once
    (e.g. on server startup) -- callers that want a clean re-index should
    construct a fresh KeywordStore first.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    sections = _chunk_markdown_by_section(raw)
    for section in sections:
        knowledge_store.upsert(
            payload=section["text"],
            metadata={
                "source": "troubleshooting_kb.md",
                "section": section["title"],
                # All internal agents can read this doc today; the field
                # exists so a future restricted section (e.g. vendor
                # pricing) can be locked to a role without changing the
                # tool's interface.
                "role_required": "any",
            },
        )
    return len(sections)


# Index once at import time, same as the module-level store pattern used
# by keyword_search.KeywordStore elsewhere in this add-on.
_CHUNK_COUNT = index_knowledge_base()
