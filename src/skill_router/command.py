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
    return analyze(prompt)["context"]


def analyze(prompt: str) -> dict:
    """Full analysis: routing hints + depth decisions + rendered context.

    Used by `skill-router route --json` for observability. The hook uses
    build_context() (the rendered string only).
    """
    # Local imports so a single bad feature import never blocks submission.
    from .features.depth.command import decide_for_skills
    from .features.routing.command import (
        collect_metadata,
        match_routes,
        render_context,
        route_records,
        should_skip,
        skills_for_routes,
    )
    from .shared.skill_io import catalog

    empty = {"hints": [], "routes": [], "metadata": {}, "depth_decisions": [], "context": ""}
    if should_skip(prompt, dict(os.environ)):
        return empty

    matches = match_routes(prompt)
    if not matches:
        return empty
    hints = [m.route.hint for m in matches]
    metadata = collect_metadata(matches)

    depth_decisions = []
    try:
        skills = skills_for_routes(matches, catalog())
        depth_decisions = decide_for_skills(prompt, skills)
        for dec in depth_decisions:
            if dec.level in ("section", "summary"):
                hints.append(dec.as_hint())
    except Exception:
        pass  # depth is advisory; never fail the hook on it

    return {
        "hints": hints,
        "routes": route_records(matches),
        "metadata": metadata,
        "depth_decisions": [
            {
                "skill": d.skill,
                "level": d.level,
                "section": d.section,
                "score": round(d.score, 3),
                "reason": d.reason,
                "doc_namespaces": list(d.doc_namespaces),
                "tools": list(d.tools),
            }
            for d in depth_decisions
        ],
        "context": render_context(hints, metadata),
    }


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
