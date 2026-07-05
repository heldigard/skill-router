"""Shared pytest fixtures for skill-router tests.

The package reads from ~/.claude/skills (canonical catalog). Tests build an
in-memory temp CLAUDE_HOME so they never touch the live harness state.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _write_skill(
    root: Path, name: str, description: str, body: str = "", sections: dict[str, str] | None = None
) -> Path:
    """Create a minimal skill dir under root/skills/<name>/."""
    sk_dir = root / "skills" / name
    sk_dir.mkdir(parents=True, exist_ok=True)
    fm = "---\n"
    fm += f"name: {name}\n"
    fm += f'description: "{description}"\n'
    if sections:
        fm += "sections:\n"
        for slug, title in sections.items():
            fm += f"  - {slug}: {title}\n"
    fm += "---\n\n"
    fm += body
    (sk_dir / "SKILL.md").write_text(fm)
    if sections:
        secs = sk_dir / "sections"
        secs.mkdir(exist_ok=True)
        for slug in sections:
            (secs / f"{slug}.md").write_text(f"# {slug}\n\nSection body for {slug}.\n")
    return sk_dir


@pytest.fixture()
def fake_claude_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temp CLAUDE_HOME with a couple of test skills; cd into it."""
    root = tmp_path / "claude"
    (root / "skills").mkdir(parents=True)
    _write_skill(
        root,
        "alpha",
        "Alpha skill for acme widgets and gadget assembly.",
        body="# Alpha\n\nMonolith body.\n" * 5,
    )
    _write_skill(
        root,
        "beta",
        "Beta multi-level skill for spring boot jpa patterns.",
        body="# Beta\n\nIndex.\n",
        sections={
            "lazy-loading": "Lazy Loading & Proxy Detection",
            "n-plus-1": "N+1 Query Problem",
            "transactions": "Transaction Boundaries",
        },
    )
    _write_skill(
        root,
        "gamma",
        "Gamma skill for angular standalone components and signals.",
        body="# Gamma\n\n" * 20,
    )
    monkeypatch.setenv("CLAUDE_HOME", str(root))
    return root


@pytest.fixture()
def isolated_claude_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Empty CLAUDE_HOME (no skills) — for catalog-empty edge cases."""
    root = tmp_path / "claude_empty"
    (root / "skills").mkdir(parents=True)
    monkeypatch.setenv("CLAUDE_HOME", str(root))
    return root
