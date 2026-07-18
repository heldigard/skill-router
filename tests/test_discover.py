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

    `web-scrape` has no Route regex (it is a leaf skill); the playwright route
    matches the prompt, but the skill is appended via the lexical recommender (no
    embeddings). Stable orphan: not slated for routing.
    """
    payload = discover("scrape web content using web-scrape via curl or wget")
    routing = payload["routing"]
    assert routing["status"] == "matched"
    names = {item["name"] for item in routing["skills"]}
    assert "web-scrape" in names
    card = next(item for item in routing["skills"] if item["name"] == "web-scrape")
    assert card["source"] == "lexical"
    assert card["path"].endswith("/web-scrape/SKILL.md")


def test_discover_does_not_pollute_a_matched_route_with_weak_lexical_neighbors() -> None:
    payload = discover("review the PostgreSQL query and indexes")
    routing = payload["routing"]
    assert routing["status"] == "matched"
    names = {item["name"] for item in routing["skills"]}
    assert "postgres" in names
    assert "search-swarm" not in names


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
