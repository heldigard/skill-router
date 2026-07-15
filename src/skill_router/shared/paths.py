"""Path resolution for the cross-CLI skill ecosystem.

Canonical source of truth: ~/.claude/skills/. Other CLIs sync/symlink from it.
"""

from __future__ import annotations

import os
from pathlib import Path


def claude_home() -> Path:
    """~/.claude — the canonical harness root (env override: CLAUDE_HOME).

    CODEX_HOME is intentionally NOT a fallback here. Both CLAUDE_HOME and
    CODEX_HOME may be set simultaneously (Codex hooks inherit both); using
    CODEX_HOME as a claude_home fallback would redirect skills_root() to
    ~/.codex/skills — the wrong canonical tree.
    """
    override = os.environ.get("CLAUDE_HOME")
    if override:
        return Path(override).resolve()
    return Path(os.environ.get("HOME", str(Path.home()))).resolve() / ".claude"


def codex_home() -> Path:
    """~/.codex — Codex user-home. Falls back to ~/.codex when CODEX_HOME unset."""
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).resolve()


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
    "opencode": ["~/.config/opencode/skills"],
    "antigravity": ["~/.gemini/config/skills", "~/.gemini/antigravity-cli/skills"],
}
