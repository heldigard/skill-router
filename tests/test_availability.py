"""Tests for Codex routed-on-demand skill availability hints."""

from __future__ import annotations

from skill_router.shared.availability import (
    available_tool_names,
    configured_mcp_servers,
    disabled_skill_files,
    on_demand_skill_hints,
)


def test_disabled_skill_files_and_codex_hint(
    fake_claude_home,
    monkeypatch,
    tmp_path,  # type: ignore[no-untyped-def]
) -> None:
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    skill_file = fake_claude_home / "skills" / "alpha" / "SKILL.md"
    (codex_home / "config.toml").write_text(
        f'[[skills.config]]\npath = "{skill_file}"\nenabled = false\n',
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
    fake_claude_home,
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    monkeypatch.setenv("CLI_ORCHESTRATION_CALLER", "claude")
    assert on_demand_skill_hints(["alpha"]) == []


def test_on_demand_hints_compact_multiple_hidden_skills_into_one(
    fake_claude_home,
    monkeypatch,
    tmp_path,  # type: ignore[no-untyped-def]
) -> None:
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    alpha = fake_claude_home / "skills" / "alpha" / "SKILL.md"
    beta = fake_claude_home / "skills" / "beta" / "SKILL.md"
    (codex_home / "config.toml").write_text(
        f'[[skills.config]]\npath = "{alpha}"\nenabled = false\n'
        f'[[skills.config]]\npath = "{beta}"\nenabled = false\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CLI_ORCHESTRATION_CALLER", "codex")

    hints = on_demand_skill_hints(["alpha", "beta"])
    assert len(hints) == 1
    assert str(alpha) in hints[0]
    assert str(beta) in hints[0]


def test_codex_tools_are_filtered_against_path_and_mcp_config(
    monkeypatch,
    tmp_path,  # type: ignore[no-untyped-def]
) -> None:
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    (codex_home / "config.toml").write_text(
        "[mcp_servers.context7]\nurl = 'https://example.invalid'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CLI_ORCHESTRATION_CALLER", "codex")
    monkeypatch.setattr("skill_router.shared.availability.shutil.which", lambda _name: None)

    assert configured_mcp_servers() == {"context7"}
    assert available_tool_names(["azure-mcp", "context7"]) == ["context7"]


def test_project_config_overrides_user_skill_and_mcp_state(
    fake_claude_home,
    monkeypatch,
    tmp_path,  # type: ignore[no-untyped-def]
) -> None:
    codex_home = tmp_path / "home" / ".codex"
    project = tmp_path / "project"
    project_config = project / ".codex"
    codex_home.mkdir(parents=True)
    project_config.mkdir(parents=True)
    (project / ".git").mkdir()
    skill_file = fake_claude_home / "skills" / "alpha" / "SKILL.md"
    (codex_home / "config.toml").write_text(
        f'[[skills.config]]\npath = "{skill_file}"\nenabled = false\n'
        "[mcp_servers.context7]\nurl = 'https://example.invalid'\n",
        encoding="utf-8",
    )
    (project_config / "config.toml").write_text(
        f'[[skills.config]]\npath = "{skill_file}"\nenabled = true\n'
        "[mcp_servers.context7]\nenabled = false\n"
        "[mcp_servers.project-docs]\nurl = 'https://example.invalid'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.chdir(project)

    assert disabled_skill_files() == set()
    assert configured_mcp_servers() == {"project-docs"}
