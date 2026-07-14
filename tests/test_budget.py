"""Tests for Codex model-visible skills budget diagnostics."""

from __future__ import annotations

from skill_router.features.budget.command import HARD_CAP, parse_prompt_input


def _payload(skill_file: str, displayed: str) -> dict:
    listing = (
        "<skills_instructions>\n"
        "### Skill roots\n"
        "- `r0` = `/catalog`\n"
        "### Available skills\n"
        f"- alpha: {displayed} (file: {skill_file.removesuffix('/SKILL.md')}/SKILL.md)\n"
        "</skills_instructions>"
    )
    return {"items": [{"content": listing}]}


def test_budget_report_detects_complete_description(
    fake_claude_home,
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    skill_file = fake_claude_home / "skills" / "alpha" / "SKILL.md"
    full = "Alpha widgets and gadgets."
    skill_file.write_text(f'---\nname: alpha\ndescription: "{full}"\n---\n', encoding="utf-8")
    report = parse_prompt_input(_payload(str(skill_file), full))
    assert report.healthy
    assert report.entries == 1
    assert report.shortened == 0


def test_budget_report_detects_shortened_description(
    fake_claude_home,
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    # Rule-compliant source (<= HARD_CAP) but Codex shows a truncated string.
    # This is a factual shortening (model loses text), NOT source debt → the
    # report is still healthy; the squeeze is informational.
    skill_file = fake_claude_home / "skills" / "alpha" / "SKILL.md"
    report = parse_prompt_input(_payload(str(skill_file), "Alpha widgets"))
    assert report.shortened_names == ("alpha",)
    assert report.over_hard_cap_names == ()
    assert report.healthy  # squeeze on a compliant entry is not a health failure


def test_budget_report_flags_over_hard_cap_source(
    fake_claude_home,
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    # Source violates the <= HARD_CAP rule → actionable debt → not healthy,
    # independent of whether Codex also truncated the displayed string.
    skill_file = fake_claude_home / "skills" / "alpha" / "SKILL.md"
    full = (
        "Alpha skill covering widgets, gadgets, assembly lines, quality "
        "control, packaging, labeling, shipping logistics, inventory, and "
        "reporting dashboards with export and alerting integrations."
    )
    assert len(full) > HARD_CAP
    skill_file.write_text(f'---\nname: alpha\ndescription: "{full}"\n---\n', encoding="utf-8")
    report = parse_prompt_input(_payload(str(skill_file), full))
    assert "alpha" in report.over_hard_cap_names
    assert "alpha" in report.over_hard_cap_local_names  # absolute local path → editable
    assert report.over_hard_cap_managed_names == ()
    assert not report.healthy


def test_is_managed_classifies_system_and_plugin_paths() -> None:
    from pathlib import Path

    from skill_router.features.budget.command import _is_managed

    assert _is_managed(Path("/home/u/.codex/skills/.system/imagegen/SKILL.md"))
    assert _is_managed(Path("/home/u/.codex/skills/.system"))
    assert _is_managed(Path("/home/u/.claude/plugins/foo/SKILL.md"))
    assert not _is_managed(Path("/home/u/.claude/skills/git-commit/SKILL.md"))
    assert not _is_managed(Path("/home/u/.codex/skills/my-skill/SKILL.md"))
