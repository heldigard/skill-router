from __future__ import annotations

import os
import pwd
from pathlib import Path

import pytest

from skill_router.features.discover.command import CAPABILITIES, discover, render

# The lexical-rescue assertions below are integration checks against the REAL
# skill catalog (web-scrape is a live leaf skill). ``claude_home()`` resolves
# via $HOME, so a redirected HOME (CI sandbox, hermetic-env sweep) leaves an
# empty catalog. Recover the real home via pwd, immune to $HOME overrides.
_REAL_SKILLS = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".claude" / "skills"
requires_real_catalog = pytest.mark.skipif(
    not (_REAL_SKILLS / "web-scrape" / "SKILL.md").is_file(),
    reason="real skill catalog unavailable (redirected HOME?)",
)


@pytest.fixture()
def real_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_HOME", str(_REAL_SKILLS.parent))


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
        "cheap-llm",
        "web-research",
        "fusion-local",
        "smart-trim",
        "cli-orchestration",
    }
    assert len(payload["starter_intents"]) == 5


@requires_real_catalog
def test_discover_surfaces_precise_leaf_skill_without_embeddings(
    real_catalog: None,
) -> None:
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


@requires_real_catalog
def test_discover_does_not_pollute_a_matched_route_with_weak_lexical_neighbors(
    real_catalog: None,
) -> None:
    payload = discover("review the PostgreSQL query and indexes")
    routing = payload["routing"]
    assert routing["status"] == "matched"
    names = {item["name"] for item in routing["skills"]}
    assert "postgres" in names
    assert "search-swarm" not in names


@requires_real_catalog
def test_discover_routes_declared_family_skill_via_route_source(
    real_catalog: None,
) -> None:
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


def test_discover_makes_graduated_route_tools_actionable() -> None:
    architecture = discover("review this architecture with a second opinion and reasoning")
    research = discover("research the latest current API documentation")

    assert "fusion-local --capabilities" in architecture["routing"]["next_actions"]
    assert "web-research capabilities" in research["routing"]["next_actions"]


def test_capability_contract_declares_cost_and_side_effects() -> None:
    for card in CAPABILITIES:
        assert card["cost"]
        assert card["writes"]
        assert card["network"]
        assert card["start"]
