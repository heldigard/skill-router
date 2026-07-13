"""Codex skill availability helpers for progressive-disclosure routing."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from .skill_io import find_skill


def _codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).resolve()


def disabled_skill_files(config_path: Path | None = None) -> set[Path]:
    """Return exact SKILL.md files disabled by the active base config."""
    path = config_path or (_codex_home() / "config.toml")
    try:
        with path.open("rb") as handle:
            config = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return set()
    disabled: set[Path] = set()
    for item in config.get("skills", {}).get("config", []):
        if not isinstance(item, dict) or item.get("enabled") is not False:
            continue
        raw = item.get("path")
        if isinstance(raw, str) and raw:
            disabled.add(Path(raw).expanduser().resolve())
    return disabled


def on_demand_skill_hints(names: list[str] | tuple[str, ...]) -> list[str]:
    """Render exact file hints for routed skills hidden from Codex's base list."""
    if os.environ.get("CLI_ORCHESTRATION_CALLER", "").lower() != "codex":
        return []
    disabled = disabled_skill_files()
    hints: list[str] = []
    for name in dict.fromkeys(names):
        skill = find_skill(name)
        source = skill.skill_md if skill is not None else _codex_skill_source(name)
        if source is None or source.resolve() not in disabled:
            continue
        hints.append(
            f"On-demand skill `{name}`: read `{source}` before acting "
            "(hidden from the initial catalog to save context)."
        )
    return hints


def _codex_skill_source(name: str) -> Path | None:
    """Resolve a Codex-native/plugin skill that is outside Claude's catalog."""
    candidates = (
        _codex_home() / "skills" / name / "SKILL.md",
        _codex_home() / "skills" / name.removeprefix("azure:") / "SKILL.md",
    )
    return next((path.resolve() for path in candidates if path.is_file()), None)
