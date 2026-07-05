"""Embedding helper around ollama_client (graceful degradation).

Used by:
  - audit/discrim  (pairwise description overlap)
  - audit/bench    (prompt -> skill hit@k)
  - depth          (prompt -> section relevance ranking)

Returns None vectors when Ollama is down — callers must handle None as
"feature unavailable, skip silently". This mirrors skills-audit's _ollama_ok.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap() -> bool:
    """Ensure ollama_client is importable. Returns True if available."""
    # shared/compat already inserts ~/.claude/scripts on import; but this module
    # may be imported in isolation by tests — bootstrap defensively.
    scripts = Path.home() / ".claude" / "scripts"
    if scripts.is_dir() and str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        import ollama_client  # type: ignore  # noqa: F401

        return True
    except Exception:
        return False


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


def embed_batch(texts: list[str]) -> list[list[float] | None]:
    """Embed multiple texts; per-item None on failure (preserves index alignment)."""
    return [embed(t) for t in texts]
