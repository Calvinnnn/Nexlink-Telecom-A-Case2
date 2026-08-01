import logging
from typing import Any, Dict, Optional, Set

logger = logging.getLogger("nextlink_auth")

# Session store mapping session_id -> set of verified account_ids
_verified_sessions: Dict[str, Set[int]] = {}


def get_session_id(ctx: Optional[Any] = None) -> str:
    """Derives a session identifier from FastMCP context if available."""
    if ctx is not None:
        if hasattr(ctx, "session") and ctx.session is not None:
            return str(id(ctx.session))
        if hasattr(ctx, "request_id") and ctx.request_id:
            return str(ctx.request_id)
    return "default_session"


def mark_account_verified(session_id: str, account_id: int) -> None:
    """Marks an account ID as verified for the given session."""
    if session_id not in _verified_sessions:
        _verified_sessions[session_id] = set()
    _verified_sessions[session_id].add(account_id)
    logger.info(f"Session '{session_id}' verified account #{account_id}")


def is_account_verified(session_id: str, account_id: int) -> bool:
    """Checks if a specific account is verified in this session."""
    return account_id in _verified_sessions.get(session_id, set())


def is_session_verified(session_id: str) -> bool:
    """Checks if any account has been verified in the session."""
    return bool(_verified_sessions.get(session_id, set()))


def clear_session(session_id: str) -> None:
    """Clears authentication state for a session."""
    _verified_sessions.pop(session_id, None)