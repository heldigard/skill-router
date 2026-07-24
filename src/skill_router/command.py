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
import re
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class HintInputs:
    """Inputs to the hint-assembly stage. One struct = one budget decision."""

    matches: list
    availability_hints: list[str]
    exclude_skills: set[str]


_CONCRETE_FILE_PROMPT_RE = re.compile(
    r"(?:^|[\s\"'`])(?:[.~]*/|/)?[^\s\"'`]+"
    r"\.(?:py|pyi|ts|tsx|js|jsx|java|go|rs|rb|kt|cs|php|vue|svelte|"
    r"json|ya?ml|toml|md|sh|zsh|sql|tf|xml|html|css)\b",
    re.IGNORECASE,
)

# Hidden skills are a scarce-context rescue path. Lexical scores below this
# level have proven to be generic word overlap (for example, "query" pulling
# in web-search skills or "API" pulling in an unrelated workflow specialist).
_CODEX_HIDDEN_LEXICAL_FLOOR = 0.15


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


def discover_routing(prompt: str) -> dict:
    """Return deterministic route + lexical skill metadata for CLI discovery.

    Cross-feature composition belongs in this top-level coordinator rather than
    inside a feature slice. Unlike the hook's unmatched rescue path, this never
    escalates to embeddings.
    """
    from .features.recommend.command import recommend
    from .features.routing.command import collect_metadata, match_routes
    from .shared.skill_io import catalog

    matches = match_routes(prompt)
    metadata = collect_metadata(matches)
    from .shared.availability import available_tool_names

    metadata["tools"] = available_tool_names(metadata.get("tools", []))
    skills = catalog()
    by_name = {skill.name: skill for skill in skills}

    names = list(metadata.get("skills", []))
    for rec in recommend(prompt, skills, top_k=3, semantic=False):
        # A matched route already supplies domain specialists. Only append a
        # lexical leaf when the user named that skill explicitly; otherwise a
        # generic shared word ("query", "review", "API") can pollute a precise
        # route with an unrelated catalog neighbor. Unmatched prompts retain
        # the broader lexical rescue behavior.
        explicit_name = bool(
            re.search(
                rf"(?<![a-z0-9]){re.escape(rec.skill)}(?![a-z0-9])",
                prompt,
                re.IGNORECASE,
            )
        )
        if matches and not explicit_name:
            continue
        if rec.skill not in names:
            names.append(rec.skill)

    routed_names = set(metadata.get("skills", []))
    skill_cards = []
    for name in names:
        catalog_skill = by_name.get(name)
        skill_cards.append(
            {
                "name": name,
                "path": str(catalog_skill.skill_md) if catalog_skill is not None else None,
                "source": "route" if name in routed_names else "lexical",
            }
        )

    status = "matched" if matches else ("recommended" if skill_cards else "unmatched")
    return {
        "status": status,
        "route_count": len(matches),
        "skills": skill_cards,
        "tools": list(metadata.get("tools", [])),
        "workers": list(metadata.get("workers", [])),
        "doc_namespaces": list(metadata.get("doc_namespaces", [])),
    }


def _recommendation_hints(prompt: str, skills: list) -> list[str]:
    """Semantic skill recommendations as hook hints. Fail-open (empty on any error)."""
    # A concrete file already gives the controller a precise scope. If no
    # deterministic route matched, a catalog-wide embedding search usually
    # produces weak test/doc neighbors and can add two 1.5s retries. Keep the
    # prompt clean; language/domain routes still fire before this fallback.
    if _CONCRETE_FILE_PROMPT_RE.search(prompt):
        return []
    try:
        from .features.recommend.command import recommend, recommendations_to_hints

        paths = {skill.name: skill.skill_md for skill in skills}
        # Deterministic-first: obvious name/trigger overlap resolves in ~50 ms.
        # Pay the embedding latency only for paraphrases lexical routing misses.
        recs = recommend(prompt, skills, top_k=3, semantic=False)
        if not recs:
            recs = recommend(prompt, skills, top_k=3)
        return recommendations_to_hints(recs, skill_paths=paths)
    except Exception:
        return []


def _codex_hidden_recommendation_hints(prompt: str, exclude: set[str]) -> list[str]:
    """Surface precise hidden specialists even when a broad regex route matched."""
    if os.environ.get("CLI_ORCHESTRATION_CALLER", "").lower() != "codex":
        return []
    try:
        from .features.recommend.command import recommend, recommendations_to_hints
        from .shared.availability import disabled_skill_files
        from .shared.skill_io import catalog

        skills = catalog()
        disabled = disabled_skill_files()
        paths = {skill.name: skill.skill_md for skill in skills}
        recs = [
            rec
            # A broad regex route already supplies domain context. Use the
            # deterministic lexical rank here; waiting twice on the 1.5 s
            # embedding timeout would tax every matched prompt. Full semantic
            # rescue remains available for prompts with no regex match.
            for rec in recommend(prompt, skills, top_k=6, semantic=False)
            if rec.score >= _CODEX_HIDDEN_LEXICAL_FLOOR
            and rec.skill not in exclude
            and paths.get(rec.skill) is not None
            and paths[rec.skill].resolve() in disabled
        ][:2]
        return recommendations_to_hints(recs, skill_paths=paths)
    except Exception:
        return []


def _unmatched_decision(prompt: str, skills: list, render_context, empty: dict) -> dict:
    """When no regex route matches, fall back to the semantic recommender.

    Route coverage is 170/170 catalog skills today, so this path now mainly
    rescues prompts whose wording slips past the regexes, plus entries the
    system-prompt catalog dropped past skillListingBudgetFraction.
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


def _assemble_hints(
    prompt: str,
    inputs: HintInputs,
    depth_decisions: list,
    limit: int,
) -> list[str]:
    """Compose, dedupe, augment with depth, and slice to MAX_HINTS.

    Order of precedence (highest signal first, then depth, then slice):
      1. availability_hints (precondition)
      2. matched-route hints (broad coverage)
      3. codex-hidden recommendations (precise specialists, deduped vs route)
      4. depth-decision hints (section/summary only)

    Dedup is exact-string so a route that intentionally re-states a more
    specific phrasing does NOT collapse into the broader one.
    """
    ordered = [
        *inputs.availability_hints,
        *(m.route.hint for m in inputs.matches),
        *_codex_hidden_recommendation_hints(prompt, inputs.exclude_skills),
    ]
    seen: set[str] = set()
    out: list[str] = []
    for h in ordered:
        if h and h not in seen:
            seen.add(h)
            out.append(h)
    for dec in depth_decisions:
        if dec.level not in ("section", "summary"):
            continue
        hint = dec.as_hint()
        if hint and hint not in seen:
            seen.add(hint)
            out.append(hint)
    return out[:limit]


def _depth_summary(depth_decisions: list) -> list[dict]:
    """Project depth decisions into JSON-ready rows."""
    rows: list[dict] = []
    for d in depth_decisions:
        rows.append(
            {
                "skill": d.skill,
                "level": d.level,
                "section": d.section,
                "score": round(d.score, 3),
                "reason": d.reason,
                "doc_namespaces": list(d.doc_namespaces),
                "tools": list(d.tools),
            }
        )
    return rows


def _availability_tool_filter(metadata: dict) -> None:
    """Filter metadata['tools'] to those currently available on PATH."""
    try:
        from .shared.availability import available_tool_names

        metadata["tools"] = available_tool_names(metadata.get("tools", []))
    except Exception:
        pass


def _availability_hints(skills: list[str]) -> list[str]:
    """Hook hints for skills Codex has dropped past its dynamic budget."""
    try:
        from .shared.availability import on_demand_skill_hints

        return on_demand_skill_hints(skills)
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
    from .shared.config import max_hints as _max_hints
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

    metadata = collect_metadata(matches)
    _availability_tool_filter(metadata)

    # Codex's curated base catalog keeps only high-signal routers visible.
    # When a route names a hidden specialist, inject its exact durable source.
    availability_hints = _availability_hints(metadata.get("skills", []))
    depth_decisions = _depth_decisions(prompt, matches, lexical_only, include_depth)
    hints = _assemble_hints(
        prompt,
        HintInputs(
            matches=matches,
            availability_hints=availability_hints,
            exclude_skills=set(metadata.get("skills", [])),
        ),
        depth_decisions,
        _max_hints(),
    )

    return {
        "hints": hints,
        "routes": route_records(matches),
        "metadata": metadata,
        "depth_decisions": _depth_summary(depth_decisions),
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
