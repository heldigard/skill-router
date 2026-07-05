"""Bootstrap sys.path for sibling ecosystem modules.

skill-router reuses two veteran scripts that still live in ~/.claude/scripts/:
  - cheap_llm.py    (shim -> ~/cheap-llm/, the local->cloud LLM cascade)
  - ollama_client.py (local Ollama HTTP client + embeddings)

Both are resolved at runtime via absolute path insertion so the package works
whether or not it was pip-installed. This mirrors prompt-improve's compat layer.

Symlink note: when this module is loaded via a symlinked shim, __file__ is the
symlink path. Path(__file__).resolve() unwraps it so sibling imports land in
the real ~/.claude/scripts/ — without this the import silently fails and the
hook degrades to its rule-based fallback.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ecosystem_scripts() -> Path:
    """Locate ~/.claude/scripts robustly (CLAUDE_HOME override honored)."""
    import os

    claude_home = Path(os.environ.get("CLAUDE_HOME", str(Path.home() / ".claude")))
    return claude_home / "scripts"


def ensure_ecosystem_imports() -> None:
    """Make `cheap_llm` and `ollama_client` importable from ~/.claude/scripts/."""
    scripts = _ecosystem_scripts()
    if scripts.is_dir():
        s = str(scripts)
        if s not in sys.path:
            sys.path.insert(0, s)


# Eager bootstrap on import so `from skill_router.shared.compat import ...`
# is enough to make sibling modules work.
ensure_ecosystem_imports()
