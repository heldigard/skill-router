"""Tests for features/audit/command.py: structural + drift + gate.

discrim/bench need Ollama and are skipped here (advisory probes anyway).
Drift/check tests monkeypatch HOME so cross-CLI sync targets (~/.codex etc.)
resolve inside the temp tree and don't see the live user config.
"""

from __future__ import annotations

import pytest

from skill_router.features.audit import command as audit_mod
from skill_router.features.audit.command import bench, check, discrim, drift, structural


def test_structural_clean_on_well_formed_catalog(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    s = structural()
    assert s["missing_fm"] == []
    assert s["missing_desc"] == []
    assert s["missing_name"] == []
    assert s["orphans"] == []
    assert s["name_mismatch"] == []


def test_drift_marks_all_targets_absent_when_isolated(
    fake_claude_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HOME isolated -> no ~/.codex, ~/.gemini, etc. exist -> all targets absent."""
    monkeypatch.setenv("HOME", str(fake_claude_home))
    d = drift()
    assert all(info.get("absent_target") for info in d.values())


def test_check_passes_on_clean_catalog(
    fake_claude_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(fake_claude_home))
    assert check() == 0


def test_check_fails_on_missing_frontmatter(
    isolated_claude_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("HOME", str(isolated_claude_home))
    sk = isolated_claude_home / "skills" / "broken"
    sk.mkdir(parents=True)
    (sk / "SKILL.md").write_text("no frontmatter here")
    assert check() == 1


def test_discrim_handles_mixed_embedding_dimensions(
    fake_claude_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(audit_mod, "is_alive", lambda: True)

    def fake_embed(text: str) -> list[float]:
        if "spring" in text.lower():
            return [0.0, 1.0, 0.0]
        return [1.0, 0.0]

    monkeypatch.setattr(audit_mod, "embed", fake_embed)
    result = discrim()

    assert result is not None
    assert "near_dups" in result


def test_bench_handles_mixed_embedding_dimensions(
    fake_claude_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(audit_mod, "is_alive", lambda: True)

    def fake_embed(text: str) -> list[float]:
        if "spring" in text.lower():
            return [0.0, 1.0, 0.0]
        return [1.0, 0.0]

    monkeypatch.setattr(audit_mod, "embed", fake_embed)
    result = bench([("alpha prompt", "alpha")])

    assert result is not None
    assert result["n"] == 1
