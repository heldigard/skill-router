"""Tests for features/routing/command.py: hint matching + skip guards."""

from __future__ import annotations

from skill_router.features.routing.command import (
    match_hints,
    render_context,
    should_skip,
    skills_referenced_in_hints,
)


def test_match_hints_returns_skill_hint_for_angular_prompt() -> None:
    hints = match_hints("how do I write an Angular standalone component with signals?")
    assert any("angular" in h.lower() for h in hints)


def test_match_hints_caps_at_limit() -> None:
    # A prompt that triggers many routes still respects the limit.
    hints = match_hints("azure functions python spring boot angular", limit=2)
    assert len(hints) <= 2


def test_match_hints_no_match_returns_empty() -> None:
    assert match_hints("totally unrelated prompt about cooking pasta") == []


def test_should_skip_on_marker() -> None:
    assert should_skip("do thing [NO_DELEGATE]") is True


def test_should_skip_on_env() -> None:
    assert should_skip("anything", {"CODEX_WORKER": "1"}) is True


def test_should_skip_clean_prompt() -> None:
    assert should_skip("normal prompt", {}) is False


def test_render_context_wraps_hints() -> None:
    out = render_context(["hint A", "hint B"])
    assert out.startswith("[Dynamic routing]")
    assert "- hint A" in out
    assert "- hint B" in out


def test_render_context_empty_returns_empty() -> None:
    assert render_context([]) == ""


def test_skills_referenced_in_hints_finds_named_skill() -> None:
    class FakeSkill:  # minimal stand-in
        def __init__(self, name: str) -> None:
            self.name = name

    catalog = [FakeSkill("angular"), FakeSkill("vue")]
    found = skills_referenced_in_hints(["load `angular` for components"], catalog)  # type: ignore[arg-type]
    assert len(found) == 1
    assert found[0].name == "angular"
