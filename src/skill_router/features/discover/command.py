"""One compact discovery surface for the graduated cross-CLI toolchain.

The command is intentionally deterministic: it inspects PATH, the route table,
and the parsed skill catalog, but never calls an LLM or an embedding service.
It answers the cheap question first: which primitive should handle this task?
"""

from __future__ import annotations

import shutil
from typing import Any

CAPABILITIES: tuple[dict[str, Any], ...] = (
    {
        "name": "codeq",
        "purpose": "Bounded symbol facts, references, dependencies, and edit context.",
        "cost": "cheap",
        "writes": "explicit tags/rename only",
        "network": "doctor only",
        "start": "codeq --json capabilities",
    },
    {
        "name": "codescan",
        "purpose": "Focused lint, type, secret, SAST, dead-code, and architecture sensors.",
        "cost": "cheap-moderate",
        "writes": "no",
        "network": "some sensors may update rules",
        "start": "codescan capabilities",
    },
    {
        "name": "agent-memory",
        "purpose": "Bounded project memory read, semantic recall, and durable handoff.",
        "cost": "cheap",
        "writes": "memory-bank commands only",
        "network": "no",
        "start": "agent-memory --help",
    },
    {
        "name": "skill-router",
        "purpose": "Route intent to exact skills, tools, docs, and bounded workers.",
        "cost": "cheap",
        "writes": "cache/audit index only",
        "network": "no",
        "start": "skill-router discover --help",
    },
    {
        "name": "prompt-improve",
        "purpose": "Turn vague prompts into compact execution constraints and acceptance hints.",
        "cost": "moderate",
        "writes": "cache only",
        "network": "optional model cascade",
        "start": "prompt-improve --help",
    },
    {
        "name": "smart-trim",
        "purpose": "Preserve a grounded handoff before context compaction.",
        "cost": "event-driven",
        "writes": ".memory-bank handoff/archive",
        "network": "optional cloud fallback",
        "start": "smart-trim --help",
    },
    {
        "name": "cli-orchestration",
        "purpose": "Coordinate leases, objectives, validation evidence, and bounded workers.",
        "cost": "variable",
        "writes": "coordination/control state",
        "network": "workers only",
        "start": "cli-orchestration --help",
    },
)

STARTER_INTENTS: tuple[dict[str, str], ...] = (
    {
        "intent": "map-code",
        "prompt": "Map this repository and identify the smallest files and symbols relevant to <goal>.",
    },
    {
        "intent": "edit-safely",
        "prompt": "Find references for <symbol>, make the smallest scoped change, and run focused validation.",
    },
    {
        "intent": "review",
        "prompt": "Review the current diff for correctness, regressions, security, and missing tests.",
    },
    {
        "intent": "resume",
        "prompt": "Read the project memory handoff and continue the next unfinished verified step.",
    },
    {
        "intent": "research",
        "prompt": "Verify <fact> against current primary documentation and cite the exact source.",
    },
)


def capability_cards() -> list[dict[str, Any]]:
    """Return stable tool cards with live PATH availability."""
    return [
        {**card, "available": shutil.which(str(card["name"])) is not None} for card in CAPABILITIES
    ]


def _routing(prompt: str) -> dict[str, Any]:
    from skill_router.command import discover_routing

    routing = discover_routing(prompt)

    next_actions: list[str] = []
    starts = {str(card["name"]): str(card["start"]) for card in CAPABILITIES}
    for tool in routing["tools"]:
        if tool in starts and starts[tool] not in next_actions:
            next_actions.append(starts[tool])
    # Precise lexical leaves are usually cheaper than broad route indexes.
    action_skills = sorted(routing["skills"], key=lambda item: item["source"] != "lexical")
    for skill_card in action_skills[:3]:
        if skill_card["path"]:
            next_actions.append(f"invoke skill {skill_card['name']} (source: {skill_card['path']})")
    if routing["status"] == "unmatched":
        next_actions.append("skill-router recommend --prompt <prompt>")
    return {**routing, "next_actions": next_actions}


def discover(prompt: str = "", *, include_examples: bool = False) -> dict[str, Any]:
    """Build the machine-readable discovery payload without model calls."""
    payload: dict[str, Any] = {
        "schema_version": 1,
        "mode": "deterministic",
        "capabilities": capability_cards(),
    }
    if prompt.strip():
        payload["routing"] = _routing(prompt.strip())
    if include_examples:
        payload["starter_intents"] = [dict(item) for item in STARTER_INTENTS]
    return payload


def render(payload: dict[str, Any]) -> str:
    """Render a compact human view; JSON remains the stable automation API."""
    lines = [
        "Cross-CLI capabilities (deterministic; no LLM)",
        "name               avail cost            writes                       purpose",
    ]
    for card in payload["capabilities"]:
        lines.append(
            f"{card['name']:<18} {'yes' if card['available'] else 'no':<5} "
            f"{card['cost']:<15} {card['writes']:<28} {card['purpose']}"
        )

    routing = payload.get("routing")
    if isinstance(routing, dict):
        lines.extend(["", f"route: {routing['status']} ({routing['route_count']} regex match(es))"])
        if routing["skills"]:
            lines.append("skills: " + ", ".join(item["name"] for item in routing["skills"]))
        if routing["tools"]:
            lines.append("tools: " + ", ".join(routing["tools"]))
        if routing["workers"]:
            lines.append("workers: " + ", ".join(routing["workers"]))
        for action in routing["next_actions"]:
            lines.append(f"next: {action}")

    examples = payload.get("starter_intents")
    if isinstance(examples, list):
        lines.extend(["", "Starter intents:"])
        lines.extend(f"- {item['intent']}: {item['prompt']}" for item in examples)
    return "\n".join(lines)


__all__ = ["CAPABILITIES", "STARTER_INTENTS", "capability_cards", "discover", "render"]
