"""Path resolution for the cross-CLI skill ecosystem.

Canonical source of truth: ~/.claude/skills/. Other CLIs sync/symlink from it.
"""

from __future__ import annotations

import os
from pathlib import Path


def claude_home() -> Path:
    """~/.claude — the canonical harness root (env override: CLAUDE_HOME)."""
    return Path(os.environ.get("CLAUDE_HOME", str(Path.home() / ".claude"))).resolve()


def skills_root() -> Path:
    """Canonical skills directory: ~/.claude/skills."""
    return claude_home() / "skills"


def state_dir() -> Path:
    """~/.claude/state — runtime state (logs, intent telemetry)."""
    return claude_home() / "state"


# Cross-CLI sync targets (label -> list of dirs whose UNION = "present in this CLI").
# Codex is hybrid: Claude skills symlink into claude-personal/ AND codex keeps
# native skills at top level. A canonical skill is "present in codex" if it
# lives in EITHER dir, so the codex target is the UNION of both.
SYNC_TARGETS: dict[str, list[str]] = {
    "codex": ["~/.codex/skills", "~/.codex/skills/claude-personal"],
    "gemini": ["~/.gemini/skills"],
    "kimi": ["~/.kimi/skills"],
    "qwen": ["~/.qwen/skills"],
    "opencode": ["~/.opencode/skills"],
    "antigravity": ["~/.gemini/config/skills", "~/.gemini/antigravity-cli/skills"],
}
