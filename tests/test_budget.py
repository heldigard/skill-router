"""Tests for Codex model-visible skills budget diagnostics."""

from __future__ import annotations

from skill_router.features.budget.command import parse_prompt_input


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
    fake_claude_home, monkeypatch  # type: ignore[no-untyped-def]
) -> None:
    skill_file = fake_claude_home / "skills" / "alpha" / "SKILL.md"
    full = "Alpha widgets and gadgets."
    skill_file.write_text(
        f'---\nname: alpha\ndescription: "{full}"\n---\n', encoding="utf-8"
    )
    report = parse_prompt_input(_payload(str(skill_file), full))
    assert report.healthy
    assert report.entries == 1
    assert report.shortened == 0


def test_budget_report_detects_shortened_description(
    fake_claude_home, monkeypatch  # type: ignore[no-untyped-def]
) -> None:
    skill_file = fake_claude_home / "skills" / "alpha" / "SKILL.md"
    report = parse_prompt_input(_payload(str(skill_file), "Alpha widgets"))
    assert not report.healthy
    assert report.shortened_names == ("alpha",)
