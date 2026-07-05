"""Routing match logic: prompt -> list of hint strings.

Pure functions over the ROUTES table. The hook entry (skill_router.command)
calls match_hints() and wraps the result in the UserPromptSubmit envelope.
"""

from __future__ import annotations

import re

from ...shared.config import MAX_HINTS, SKIP_ENV_VARS, SKIP_PROMPT_MARKERS
from ...shared.skill_io import Skill
from .routes import ROUTES

_COMPILED: list[tuple[list[re.Pattern[str]], str]] = [
    ([re.compile(p, re.IGNORECASE) for p in patterns], hint) for patterns, hint in ROUTES
]


def should_skip(prompt: str, env: dict[str, str] | None = None) -> bool:
    """True if any skip marker is in the prompt or env (NO_DELEGATE etc.)."""
    if any(m in prompt for m in SKIP_PROMPT_MARKERS):
        return True
    if env and any(env.get(v) for v in SKIP_ENV_VARS):
        return True
    return False


def match_hints(prompt: str, limit: int = MAX_HINTS) -> list[str]:
    """Return up to `limit` hint strings whose patterns match the prompt.

    Order matters: first matches win, preserving the declaration order of ROUTES.
    """
    hints: list[str] = []
    for compiled_patterns, hint in _COMPILED:
        if any(cp.search(prompt) for cp in compiled_patterns):
            hints.append(hint)
    return hints[:limit]


def skills_referenced_in_hints(hints: list[str], catalog: list[Skill]) -> list[Skill]:
    """Best-effort: skills whose name appears in any hint text.

    Used by the depth selector to know which skills the router is recommending,
    so it can suggest a section instead of the full body when one is multi-level.
    """
    out: list[Skill] = []
    seen: set[str] = set()
    for sk in catalog:
        if sk.name in seen:
            continue
        if any(sk.name in h for h in hints):
            out.append(sk)
            seen.add(sk.name)
    return out


def render_context(hints: list[str]) -> str:
    """Wrap hints in the [Dynamic routing] envelope used by the hook."""
    if not hints:
        return ""
    return (
        "[Dynamic routing]\n- "
        + "\n- ".join(hints)
        + "\nAcción: cuando una skill aplique a la tarea, invócala vía la herramienta Skill "
        "ANTES de responder; cuando sugieras un MCP o worker, úsalo en lugar de solo mencionarlo."
    )
