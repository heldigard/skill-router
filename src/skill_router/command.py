"""UserPromptSubmit hook entry point.

Reads the hook payload from stdin, classifies the prompt, matches routing hints,
and (when a hint references a multi-level skill) appends a depth suggestion.
Emits the Claude Code / Codex UserPromptSubmit envelope:

    {"continue": true,
     "hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                            "additionalContext": "..."}}

Failures degrade OPEN: any internal error returns {"continue": true} so prompt
submission never blocks. Mirrors prompt-improve's robustness contract.

Wired via the hook entrypoint at ~/.claude/hooks/skill-router.py (settings.json).
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
    Returns "" if nothing matched.
    """
    return analyze(prompt, include_depth=False, lexical_only=True)["context"]


def _recommendation_hints(prompt: str, skills: list) -> list[str]:
    """Semantic skill recommendations as hook hints. Fail-open (empty on any error)."""
    try:
        from .features.recommend.command import recommend, recommendations_to_hints

        return recommendations_to_hints(recommend(prompt, skills, top_k=3))
    except Exception:
        return []


def _unmatched_decision(prompt: str, skills: list, render_context, empty: dict) -> dict:
    """When no regex route matches, fall back to the semantic recommender.

    Resuscitates the ~33% of skills with no Route regex (concurrency-review,
    logging-patterns, maven-dependency-audit, ...) and entries the system-prompt
    catalog dropped past skillListingBudgetFraction.
    """
    rec_hints = _recommendation_hints(prompt, skills)
    if rec_hints:
        return {
            **empty,
            "hints": rec_hints,
            "context": render_context(rec_hints, {}),
            "decision": {
                "status": "recommended",
                "reason": "no regex route matched; semantic recommender surfaced skills",
                "route_count": 0,
            },
        }
    return {
        **empty,
        "decision": {
            "status": "unmatched",
            "reason": "no route pattern matched the prompt",
            "route_count": 0,
        },
    }


def _depth_decisions(prompt: str, matches: list, lexical_only: bool, include_depth: bool) -> list:
    """Advisory multi-level section selection. Fail-open (empty list)."""
    if not (include_depth or lexical_only):
        return []
    try:
        from .features.depth.command import decide_for_skills
        from .features.routing.command import skills_for_routes
        from .shared.skill_io import catalog

        skills = skills_for_routes(matches, catalog())
        return list(decide_for_skills(prompt, skills, lexical_only=lexical_only))
    except Exception:
        return []


def analyze(
    prompt: str,
    include_depth: bool = False,
    lexical_only: bool = False,
) -> dict:
    """Full analysis: routing hints + depth decisions + rendered context.

    Depth decisions may call local Ollama embeddings and are intentionally
    opt-in. Prompt-submit hooks must stay deterministic and fast.
    """
    # Local imports so a single bad feature import never blocks submission.
    from .features.routing.command import (
        collect_metadata,
        match_routes,
        render_context,
        route_records,
        should_skip,
    )
    from .shared.skill_io import catalog

    empty = {"hints": [], "routes": [], "metadata": {}, "depth_decisions": [], "context": ""}
    if should_skip(prompt, dict(os.environ)):
        return {
            **empty,
            "decision": {
                "status": "skipped",
                "reason": "prompt marker or worker environment disables dynamic routing",
                "route_count": 0,
            },
        }

    matches = match_routes(prompt)
    if not matches:
        return _unmatched_decision(prompt, catalog(), render_context, empty)
    hints = [m.route.hint for m in matches]
    metadata = collect_metadata(matches)

    depth_decisions = _depth_decisions(prompt, matches, lexical_only, include_depth)
    for dec in depth_decisions:
        if dec.level in ("section", "summary"):
            hints.append(dec.as_hint())

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
        "decision": {
            "status": "matched",
            "reason": "one or more route patterns matched",
            "route_count": len(matches),
        },
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
