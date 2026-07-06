"""Embedding helper around ollama_client (graceful degradation).

Used by:
  - audit/discrim  (pairwise description overlap)
  - audit/bench    (prompt -> skill hit@k)
  - depth          (prompt -> section relevance ranking)

Returns None vectors when Ollama is down — callers must handle None as
"feature unavailable, skip silently". This mirrors skills-audit's _ollama_ok.

Bootstrap is cached: the sys.path insert + `import ollama_client` happens at
most once per process. `is_alive()` still pings the server on every call (it
can go down mid-session); only the import resolution is memoized.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BOOTSTRAP_DONE = False
_BOOTSTRAP_OK = False


def _bootstrap() -> bool:
    """Ensure ollama_client is importable. Memoized per-process."""
    global _BOOTSTRAP_DONE, _BOOTSTRAP_OK
    if _BOOTSTRAP_DONE:
        return _BOOTSTRAP_OK
    # shared/compat already inserts ~/.claude/scripts on import; but this module
    # may be imported in isolation by tests — bootstrap defensively.
    scripts = Path.home() / ".claude" / "scripts"
    if scripts.is_dir() and str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        import ollama_client  # type: ignore  # noqa: F401

        _BOOTSTRAP_OK = True
    except Exception:
        _BOOTSTRAP_OK = False
    _BOOTSTRAP_DONE = True
    return _BOOTSTRAP_OK


def reset_bootstrap_cache() -> None:
    """Force re-bootstrap on next call (tests that swap ollama_client on the path)."""
    global _BOOTSTRAP_DONE, _BOOTSTRAP_OK
    _BOOTSTRAP_DONE = False
    _BOOTSTRAP_OK = False


def is_alive() -> bool:
    """True if Ollama is reachable and ollama_client loaded."""
    if not _bootstrap():
        return False
    try:
        import ollama_client as oc  # type: ignore

        return bool(oc.is_alive())
    except Exception:
        return False


def embed(text: str) -> list[float] | None:
    """Embed text via local Ollama. None if unavailable."""
    if not _bootstrap():
        return None
    try:
        import ollama_client as oc  # type: ignore

        v = oc.embed(text)
        return list(v) if v is not None else None
    except Exception:
        return None
