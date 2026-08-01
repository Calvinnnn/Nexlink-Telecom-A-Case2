"""
The search_knowledge_base MCP tool.

This is additive to the existing server: it does not touch db.py, and it
does not replace any of the structured tools in tools_read.py /
tools_write.py. It answers a different kind of question -- "what does the
engineering troubleshooting guide say about X" -- that no amount of
querying the accounts/tickets/equipment tables could ever answer, because
that knowledge only exists as prose written by NOC engineers.
"""

from pydantic import BaseModel, Field, ConfigDict

from knowledge_base import knowledge_store


class SearchKnowledgeBaseInput(BaseModel):
    query: str = Field(..., description="Keywords describing the issue or topic to look up")
    top_k: int = Field(default=3, ge=1, le=10, description="Max number of KB sections to return")

    model_config = ConfigDict(extra="forbid")  # additionalProperties: false


def handle_search_knowledge_base(query: str, top_k: int = 3, session_role: str = "any") -> str:
    """
    Handler registered as the `search_knowledge_base` MCP tool.

    `session_role` mirrors the pattern used by verify_account_identity /
    auth.py elsewhere in the server: it comes from the authenticated
    session, never from the tool's `args`, so a caller can't just pass
    role="vet" (or here, role="engineering") to unlock restricted
    sections of the KB.
    """
    parsed = SearchKnowledgeBaseInput.model_validate({"query": query, "top_k": top_k})

    matches = knowledge_store.query(query_text=parsed.query, top_k=parsed.top_k)

    visible = [
        m for m in matches
        if m["metadata"]["role_required"] in ("any", session_role)
    ]

    if not visible:
        return "No relevant troubleshooting KB sections found for that query."

    lines = [f"Found {len(visible)} relevant KB section(s):\n"]
    for m in visible:
        lines.append(f"[{m['metadata']['section']}] (relevance score: {m['score']:.2f})\n{m['payload']}")
    return "\n\n---\n\n".join(lines) if len(lines) > 1 else lines[0]
