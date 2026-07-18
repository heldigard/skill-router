"""Codex skill availability helpers for progressive-disclosure routing."""

from __future__ import annotations

import os
import shutil
import tomllib
from pathlib import Path

from .paths import codex_home
from .skill_io import find_skill


def _codex_home() -> Path:
    return codex_home()


def _config_paths(config_path: Path | None = None) -> tuple[Path, ...]:
    """Return Codex config layers from user base to nearest project override."""
    if config_path is not None:
        return (config_path,)
    base = _codex_home() / "config.toml"
    project_root = next(
        (
            parent
            for parent in (Path.cwd(), *Path.cwd().parents)
            if any((parent / marker).exists() for marker in (".git", "pyproject.toml", "AGENTS.md"))
        ),
        None,
    )
    project = project_root / ".codex" / "config.toml" if project_root is not None else None
    if project is not None and not project.is_file():
        project = None
    return (base,) if project is None or project.resolve() == base.resolve() else (base, project)


def _read_config(path: Path) -> dict:
    try:
        with path.open("rb") as handle:
            config = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return config if isinstance(config, dict) else {}


def disabled_skill_files(config_path: Path | None = None) -> set[Path]:
    """Return exact SKILL.md files disabled by effective user/project config."""
    states: dict[Path, bool] = {}
    for path in _config_paths(config_path):
        config = _read_config(path)
        for item in config.get("skills", {}).get("config", []):
            if not isinstance(item, dict):
                continue
            raw = item.get("path")
            if isinstance(raw, str) and raw:
                states[Path(raw).expanduser().resolve()] = item.get("enabled") is False
    return {path for path, disabled in states.items() if disabled}


def on_demand_skill_hints(names: list[str] | tuple[str, ...]) -> list[str]:
    """Render one priority hint for routed skills hidden from Codex's base list.

    Keeping the paths in one hint prevents a relevant specialist from falling
    past ``MAX_HINTS`` when several broad routes also match the prompt.
    """
    if os.environ.get("CLI_ORCHESTRATION_CALLER", "").lower() != "codex":
        return []
    disabled = disabled_skill_files()
    routed: list[tuple[str, Path]] = []
    for name in dict.fromkeys(names):
        skill = find_skill(name)
        source = skill.skill_md if skill is not None else _codex_skill_source(name)
        if source is None or source.resolve() not in disabled:
            continue
        routed.append((name, source))
    if not routed:
        return []
    entries = "; ".join(f"`{name}` -> `{source}`" for name, source in routed[:2])
    return [f"Codex hidden skills: {entries}. Read applicable SKILL.md before work."]


def configured_mcp_servers(config_path: Path | None = None) -> set[str]:
    """Return enabled MCP names from effective user/project Codex config."""
    states: dict[str, bool] = {}
    for path in _config_paths(config_path):
        servers = _read_config(path).get("mcp_servers", {})
        if not isinstance(servers, dict):
            continue
        for name, settings in servers.items():
            states[name] = not (isinstance(settings, dict) and settings.get("enabled") is False)
    return {name for name, enabled in states.items() if enabled}


def available_tool_names(names: list[str] | tuple[str, ...]) -> list[str]:
    """Filter route tools against Codex's active PATH and MCP configuration.

    Other callers keep their route metadata unchanged because their tool
    registries are injected by their own harnesses. Codex otherwise received
    imperative advice to call MCP servers that were not registered.
    """
    ordered = list(dict.fromkeys(names))
    if os.environ.get("CLI_ORCHESTRATION_CALLER", "").lower() != "codex":
        return ordered
    mcp_servers = configured_mcp_servers()
    return [name for name in ordered if shutil.which(name) is not None or name in mcp_servers]


def _codex_skill_source(name: str) -> Path | None:
    """Resolve a Codex-native/plugin skill that is outside Claude's catalog."""
    candidates = (
        _codex_home() / "skills" / name / "SKILL.md",
        _codex_home() / "skills" / name.removeprefix("azure:") / "SKILL.md",
    )
    return next((path.resolve() for path in candidates if path.is_file()), None)
