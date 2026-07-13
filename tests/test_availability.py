"""Tests for Codex routed-on-demand skill availability hints."""

from __future__ import annotations

from skill_router.shared.availability import (
    disabled_skill_files,
    on_demand_skill_hints,
)


def test_disabled_skill_files_and_codex_hint(
    fake_claude_home, monkeypatch, tmp_path  # type: ignore[no-untyped-def]
) -> None:
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    skill_file = fake_claude_home / "skills" / "alpha" / "SKILL.md"
    (codex_home / "config.toml").write_text(
        "[[skills.config]]\n"
        f'path = "{skill_file}"\n'
        "enabled = false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CLI_ORCHESTRATION_CALLER", "codex")

    assert skill_file.resolve() in disabled_skill_files()
    hints = on_demand_skill_hints(["alpha", "beta"])
    assert len(hints) == 1
    assert "alpha" in hints[0]
    assert str(skill_file) in hints[0]


def test_on_demand_hints_are_codex_only(
    fake_claude_home, monkeypatch  # type: ignore[no-untyped-def]
) -> None:
    monkeypatch.setenv("CLI_ORCHESTRATION_CALLER", "claude")
    assert on_demand_skill_hints(["alpha"]) == []
