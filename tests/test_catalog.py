"""Tests for features/catalog/command.py: rendering + oversized detection."""

from __future__ import annotations

from skill_router.features.catalog.command import list_all, oversized, show


def test_list_all_renders_multilevel_flag(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    out = list_all()
    assert "Catalog: 3 skill(s)" in out
    # beta is multi-level -> [ML] marker
    beta_line = [ln for ln in out.splitlines() if "beta" in ln][0]
    assert "[ML]" in beta_line
    assert "sections=3" in beta_line


def test_list_all_only_multilevel_filter(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    out = list_all(only_multilevel=True)
    assert "Catalog: 1 skill" in out
    assert "beta" in out
    assert "alpha" not in out


def test_show_skill_renders_sections(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    out = show("beta")
    assert "# beta" in out
    assert "multi-level: True" in out
    assert "lazy-loading" in out


def test_show_skill_missing_returns_message(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    assert "not found" in show("nope")


def test_oversized_filters_by_threshold(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    # gamma body is ~41 lines; alpha is ~16. Threshold 30 separates them.
    big = oversized(threshold=30)
    names = {s.name for s in big}
    assert "gamma" in names
    assert "alpha" not in names
    assert "beta" not in names  # beta is ~7 lines
