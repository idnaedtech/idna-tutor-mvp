"""
IDNA EdTech - Cost Guard
=========================
Enforces LLM call limits to prevent runaway costs.

Limits:
    MAX_LLM_CALLS_PER_SESSION = 50
    MAX_LLM_CALLS_PER_MINUTE  = 10

When a limit is hit, the caller falls back to deterministic responses
(teacher_policy generates structured plans without LLM).

Integrated into llm_client.py via check_and_increment().
"""

import time
import threading
from typing import Tuple

# ---------------------------------------------------------------------------
# Limits (configurable via env vars in future, hard-coded for now)
# ---------------------------------------------------------------------------

MAX_LLM_CALLS_PER_SESSION = 50
MAX_LLM_CALLS_PER_MINUTE = 10

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

_lock = threading.Lock()

# Per-session counters: session_id -> call_count
_session_counts: dict[str, int] = {}

# Rolling window for per-minute rate limiting
_minute_timestamps: list[float] = []

# Global fallback counter (no session context — counts all calls)
_global_call_count: int = 0


def check_and_increment(session_id: str = "") -> Tuple[bool, str]:
    """
    Check if an LLM call is allowed and increment counters.

    Returns:
        (allowed: bool, reason: str)
        If allowed is False, reason explains why.
    """
    global _global_call_count

    now = time.time()

    with _lock:
        # 1. Per-minute rate limit (rolling window)
        # Remove timestamps older than 60 seconds
        cutoff = now - 60.0
        _minute_timestamps[:] = [t for t in _minute_timestamps if t > cutoff]

        if len(_minute_timestamps) >= MAX_LLM_CALLS_PER_MINUTE:
            return False, f"Rate limit: {MAX_LLM_CALLS_PER_MINUTE} calls/minute exceeded"

        # 2. Per-session limit
        if session_id:
            count = _session_counts.get(session_id, 0)
            if count >= MAX_LLM_CALLS_PER_SESSION:
                return False, f"Session limit: {MAX_LLM_CALLS_PER_SESSION} calls exceeded"

        # All checks passed — increment
        _minute_timestamps.append(now)
        _global_call_count += 1

        if session_id:
            _session_counts[session_id] = _session_counts.get(session_id, 0) + 1

        return True, "ok"


def get_session_usage(session_id: str) -> int:
    """Get current LLM call count for a session."""
    with _lock:
        return _session_counts.get(session_id, 0)


def get_minute_usage() -> int:
    """Get LLM calls in the last 60 seconds."""
    now = time.time()
    cutoff = now - 60.0
    with _lock:
        return sum(1 for t in _minute_timestamps if t > cutoff)


def reset_session(session_id: str):
    """Reset counters for a session (called on session end)."""
    with _lock:
        if session_id in _session_counts:
            del _session_counts[session_id]


def reset_all():
    """Reset all counters (for testing)."""
    global _global_call_count
    with _lock:
        _session_counts.clear()
        _minute_timestamps.clear()
        _global_call_count = 0
