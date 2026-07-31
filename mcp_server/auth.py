from typing import Set, Dict, Optional
import logging

logger = logging.getLogger("nextlink_auth")

# In-memory store: session_id -> Set[account_id]
_verified_sessions: Dict[str, Set[int]] = {}

def get_session_id(ctx: Optional[Any] = None) -> str:
    """Extracts or derives a session identifier from FastMCP Context."""
    if ctx is not None:
        # Check session object or request_id
        if hasattr(ctx, "session") and ctx.session is not None:
            return str(id(ctx.session))
        if hasattr(ctx, "request_id") and ctx.request_id:
            return str(ctx.request_id)
    return "default_session"

def mark_account_verified(session_id: str, account_id: int) -> None:
    """Marks a specific account_id as identity-verified for a session."""
    if session_id not in _verified_sessions:
        _verified_sessions[session_id] = set()
    _verified_sessions[session_id].add(account_id)
    logger.info(f"Session {session_id} verified identity for account_id {account_id}")

def is_account_verified(session_id: str, account_id: int) -> bool:
    """Checks if a specific account_id is verified for the given session."""
    return account_id in _verified_sessions.get(session_id, set())

def is_session_verified(session_id: str) -> bool:
    """Checks if any account is verified in this session (useful for dynamic tool listing)."""
    return bool(_verified_sessions.get(session_id, set()))

def clear_session(session_id: str) -> None:
    """Clears session auth state."""
    _verified_sessions.pop(session_id, None)
