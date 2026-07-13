from __future__ import annotations

from skill_router.features.discover.command import CAPABILITIES, discover, render


def test_discover_exposes_one_stable_cross_cli_surface() -> None:
    payload = discover(include_examples=True)
    assert payload["schema_version"] == 1
    assert payload["mode"] == "deterministic"
    assert {item["name"] for item in payload["capabilities"]} == {
        "codeq",
        "codescan",
        "agent-memory",
        "skill-router",
        "prompt-improve",
        "smart-trim",
        "cli-orchestration",
    }
    assert len(payload["starter_intents"]) == 5


def test_discover_surfaces_precise_leaf_skill_without_embeddings() -> None:
    """A matched prompt still lexical-rescues a genuine orphan leaf skill.

    `subagent-cost-guard` has no Route regex; the worker route matches the
    prompt, but the skill is appended via the lexical recommender (no embeddings).
    """
    payload = discover("antes de delegar a codex-correr corre el guard de costos de workers")
    routing = payload["routing"]
    assert routing["status"] == "matched"
    names = {item["name"] for item in routing["skills"]}
    assert "subagent-cost-guard" in names
    card = next(item for item in routing["skills"] if item["name"] == "subagent-cost-guard")
    assert card["source"] == "lexical"
    assert card["path"].endswith("/subagent-cost-guard/SKILL.md")


def test_discover_routes_declared_family_skill_via_route_source() -> None:
    """Broadening: concurrency-review is now declared on the java route, so
    discover surfaces it as a first-class route skill (not a lexical rescue)."""
    payload = discover("review Java concurrency locks and thread safety")
    routing = payload["routing"]
    assert routing["status"] == "matched"
    card = next(item for item in routing["skills"] if item["name"] == "concurrency-review")
    assert card["source"] == "route"


def test_render_is_compact_and_actionable() -> None:
    text = render(discover("find references before editing a symbol"))
    assert "Cross-CLI capabilities" in text
    assert "codeq --json capabilities" in text
    assert len(text) < 2400


def test_capability_contract_declares_cost_and_side_effects() -> None:
    for card in CAPABILITIES:
        assert card["cost"]
        assert card["writes"]
        assert card["network"]
        assert card["start"]
