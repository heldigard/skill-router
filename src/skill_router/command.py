"""UserPromptSubmit hook entry point.

Reads the hook payload from stdin, classifies the prompt, matches routing hints,
and (when a hint references a multi-level skill) appends a depth suggestion.
Emits the Claude Code / Codex UserPromptSubmit envelope:

    {"continue": true,
     "hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                            "additionalContext": "..."}}

Failures degrade OPEN: any internal error returns {"continue": true} so prompt
submission never blocks. Mirrors prompt-improve's robustness contract.

Wired via the shim at ~/.claude/hooks/prompt-router.py (settings.json).
"""

from __future__ import annotations

import json
import os
import sys


def load_prompt() -> str:
    """Read the hook payload from stdin; return the prompt string (empty if none)."""
    try:
        data = json.load(sys.stdin)
        if isinstance(data, dict):
            return str(data.get("prompt", "")).strip()
    except Exception:
        pass
    return ""


def build_context(prompt: str) -> str:
    """Build the additionalContext string for the hook envelope.

    Composes (in order):
      1. routing hints (regex -> skill/MCP/worker advice)
      2. depth suggestions (when a hint references a multi-level skill)

    Returns "" if nothing matched.
    """
    # Local imports so a single bad feature import never blocks submission.
    from .features.depth.command import decide_for_skills
    from .features.routing.command import (
        match_hints,
        render_context,
        should_skip,
        skills_referenced_in_hints,
    )
    from .shared.skill_io import catalog

    if should_skip(prompt, dict(os.environ)):
        return ""

    hints = match_hints(prompt)
    if not hints:
        return ""

    # Depth layer: if any hint references a multi-level skill, suggest a section.
    try:
        skills = skills_referenced_in_hints(hints, catalog())
        decisions = decide_for_skills(prompt, skills)
        for dec in decisions:
            if dec.level in ("section", "summary"):
                hints.append(dec.as_hint())
    except Exception:
        pass  # depth is advisory; never fail the hook on it

    return render_context(hints)


def main() -> None:
    """Hook entry. Always emits valid JSON; never raises."""
    try:
        prompt = load_prompt()
        if not prompt:
            print(json.dumps({"continue": True}))
            return
        context = build_context(prompt)
        if not context:
            print(json.dumps({"continue": True}))
            return
        print(
            json.dumps(
                {
                    "continue": True,
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": context,
                    },
                },
                ensure_ascii=False,
            )
        )
    except Exception as exc:  # noqa: BLE001 — fail-open is the contract
        sys.stderr.write(f"[skill-router] hook error (fail-open): {exc}\n")
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
