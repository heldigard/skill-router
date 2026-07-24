"""Routing match logic: prompt -> structured route matches."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TypeAlias

from ...shared.availability import available_tool_names
from ...shared.config import MAX_HINTS, SKIP_ENV_VARS, SKIP_PROMPT_MARKERS
from ...shared.skill_io import Skill
from .routes import ROUTES, Route

RouteRecord: TypeAlias = dict[str, int | str | list[str]]


@dataclass(frozen=True)
class MatchedRoute:
    """A route that matched a prompt, preserving source order for explainability."""

    index: int
    route: Route


_COMPILED: list[tuple[int, Route, tuple[re.Pattern[str], ...]]] = [
    (idx, route, tuple(re.compile(p, re.IGNORECASE) for p in route.patterns))
    for idx, route in enumerate(ROUTES)
]


def should_skip(prompt: str, env: dict[str, str] | None = None) -> bool:
    """True if any skip marker is in the prompt or env (NO_DELEGATE etc.)."""
    if any(m in prompt for m in SKIP_PROMPT_MARKERS):
        return True
    if env and any(env.get(v) for v in SKIP_ENV_VARS):
        return True
    return False


def match_routes(prompt: str, limit: int = MAX_HINTS) -> list[MatchedRoute]:
    """Return matched routes, ranked by priority then source order."""
    matches: list[MatchedRoute] = []
    for idx, route, compiled_patterns in _COMPILED:
        if any(cp.search(prompt) for cp in compiled_patterns):
            matches.append(MatchedRoute(index=idx, route=route))
    matches.sort(key=lambda m: (-m.route.priority, m.index))
    return matches[:limit]


def match_hints(prompt: str, limit: int = MAX_HINTS) -> list[str]:
    """Return compact hint strings for matched routes."""
    return [m.route.hint for m in match_routes(prompt, limit=limit)]


def skills_for_routes(matches: list[MatchedRoute], catalog: list[Skill]) -> list[Skill]:
    """Return catalog skills explicitly declared by matched routes."""
    names: list[str] = []
    seen_names: set[str] = set()
    for match in matches:
        for name in match.route.skills:
            if name not in seen_names:
                names.append(name)
                seen_names.add(name)

    out: list[Skill] = []
    wanted = set(names)
    for sk in catalog:
        if sk.name in wanted:
            out.append(sk)
    return out


def collect_metadata(matches: list[MatchedRoute]) -> dict[str, list[str]]:
    """Aggregate route metadata in first-seen order."""
    out: dict[str, list[str]] = {"skills": [], "tools": [], "workers": [], "doc_namespaces": []}
    seen: dict[str, set[str]] = {k: set() for k in out}
    for match in matches:
        route = match.route
        for key, values in (
            ("skills", route.skills),
            ("tools", route.tools),
            ("workers", route.workers),
            ("doc_namespaces", route.doc_namespaces),
        ):
            for value in values:
                if value not in seen[key]:
                    out[key].append(value)
                    seen[key].add(value)
    return out


def route_records(matches: list[MatchedRoute]) -> list[RouteRecord]:
    """JSON-ready route explain records."""
    records: list[RouteRecord] = []
    for match in matches:
        route = match.route
        records.append(
            {
                "index": match.index,
                "priority": route.priority,
                "hint": route.hint,
                "skills": list(route.skills),
                "tools": available_tool_names(route.tools),
                "workers": list(route.workers),
                "doc_namespaces": list(route.doc_namespaces),
            }
        )
    return records


def render_context(hints: list[str], metadata: dict[str, list[str]] | None = None) -> str:
    """Wrap hints in the [Dynamic routing] envelope used by the hook."""
    if not hints:
        return ""
    meta = metadata or {}
    doc_namespaces = meta.get("doc_namespaces") or []
    doc_hint = ""
    if doc_namespaces:
        doc_hint = "\n- Docs: official/Context7 namespaces: " + ", ".join(doc_namespaces[:8]) + "."
    return (
        "[Dynamic routing]\n- "
        + "\n- ".join(hints)
        + doc_hint
        + "\nAction: load applicable named skills before work; invoke suggested tools/workers."
    )
