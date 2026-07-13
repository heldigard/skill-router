"""Measure Codex's actual model-visible skills list and description loss."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ...shared.skill_io import parse_frontmatter

_ROOT_RE = re.compile(r"- `([^`]+)` = `([^`]+)`")
_ENTRY_RE = re.compile(r"- (.*?): (.*?) \(file: (.+)/SKILL\.md\)$")


@dataclass(frozen=True)
class BudgetReport:
    listing_chars: int
    entries: int
    shortened: int
    missing_sources: int
    full_description_chars: int
    displayed_description_chars: int
    shortened_names: tuple[str, ...]

    @property
    def healthy(self) -> bool:
        return self.entries > 0 and self.shortened == 0 and self.missing_sources == 0

def _collect_strings(value: object) -> list[str]:
    out: list[str] = []
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            out.extend(_collect_strings(item))
    elif isinstance(value, list):
        for item in value:
            out.extend(_collect_strings(item))
    return out


def _expand_source(raw: str, roots: dict[str, str]) -> Path:
    for alias, root in roots.items():
        if raw == alias or raw.startswith(f"{alias}/"):
            raw = root + raw[len(alias) :]
            break
    return Path(f"{raw}/SKILL.md").expanduser()


def _description(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    return parse_frontmatter(text)[1]


def parse_prompt_input(payload: object) -> BudgetReport:
    """Build a loss report from ``codex debug prompt-input`` JSON."""
    listing = next(
        (text for text in _collect_strings(payload) if "<skills_instructions>" in text),
        "",
    )
    roots = {match.group(1): match.group(2) for match in _ROOT_RE.finditer(listing)}
    shortened: list[str] = []
    missing = full_chars = displayed_chars = entries = 0
    for line in listing.splitlines():
        match = _ENTRY_RE.fullmatch(line)
        if not match:
            continue
        name, displayed, raw_path = match.groups()
        entries += 1
        displayed_chars += len(displayed)
        full = _description(_expand_source(raw_path, roots))
        if full is None:
            missing += 1
            continue
        full_chars += len(full)
        if displayed != full:
            shortened.append(name)
    return BudgetReport(
        listing_chars=len(listing),
        entries=entries,
        shortened=len(shortened),
        missing_sources=missing,
        full_description_chars=full_chars,
        displayed_description_chars=displayed_chars,
        shortened_names=tuple(shortened),
    )


def inspect_codex(profile: str | None = None) -> BudgetReport | None:
    command = ["codex"]
    if profile:
        command.extend(("--profile", profile))
    command.extend(("debug", "prompt-input"))
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    try:
        return parse_prompt_input(json.loads(result.stdout))
    except json.JSONDecodeError:
        return None
