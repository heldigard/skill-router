"""Tests for features/routing/command.py: hint matching + skip guards."""

from __future__ import annotations

from skill_router.features.routing.command import (
    collect_metadata,
    match_hints,
    match_routes,
    render_context,
    should_skip,
    skills_for_routes,
)


def test_match_hints_returns_skill_hint_for_angular_prompt() -> None:
    hints = match_hints("how do I write an Angular standalone component with signals?")
    assert any("angular" in h.lower() for h in hints)


def test_match_routes_caps_at_limit() -> None:
    # A prompt that triggers many routes still respects the limit.
    matches = match_routes("azure functions python spring boot angular", limit=2)
    assert len(matches) <= 2


def test_match_hints_no_match_returns_empty() -> None:
    assert match_hints("totally unrelated prompt about cooking pasta") == []


def test_should_skip_on_marker() -> None:
    assert should_skip("do thing [NO_DELEGATE]") is True


def test_should_skip_on_env() -> None:
    assert should_skip("anything", {"CODEX_WORKER": "1"}) is True


def test_should_skip_clean_prompt() -> None:
    assert should_skip("normal prompt", {}) is False


def test_render_context_wraps_hints() -> None:
    out = render_context(["hint A", "hint B"], {"doc_namespaces": ["angular", "spring"]})
    assert out.startswith("[Dynamic routing]")
    assert "- hint A" in out
    assert "- hint B" in out
    assert "angular, spring" in out


def test_render_context_empty_returns_empty() -> None:
    assert render_context([]) == ""


def test_skills_for_routes_uses_structured_metadata() -> None:
    class FakeSkill:  # minimal stand-in
        def __init__(self, name: str) -> None:
            self.name = name

    catalog = [FakeSkill("angular"), FakeSkill("vue")]
    matches = match_routes("Angular signals standalone component")
    found = skills_for_routes(matches, catalog)  # type: ignore[arg-type]
    assert len(found) == 1
    assert found[0].name == "angular"


def test_collect_metadata_includes_docs_and_tools() -> None:
    matches = match_routes("Angular signals standalone component")
    meta = collect_metadata(matches)
    assert "angular" in meta["skills"]
    assert "context7" in meta["tools"]
    assert "angular" in meta["doc_namespaces"]
