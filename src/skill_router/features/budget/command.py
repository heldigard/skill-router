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


# Documented source-description rule (see ~/.claude/CLAUDE.md skill-router
# note): frontmatter descriptions <= HARD_CAP chars so trigger words survive
# Codex's model-visible listing. Codex additionally applies a DYNAMIC per-entry
# budget that collapses (~150ch) when the catalog overflows, so rule-compliant
# entries (<= HARD_CAP) can still be squeezed by Codex WITHOUT that being
# source debt. `shortened` reports the factual model-visible truncation;
# `over_hard_cap_names` is the actionable source debt (violates the rule).
HARD_CAP = 185


@dataclass(frozen=True)
class BudgetReport:
    listing_chars: int
    entries: int
    shortened: int  # model-visible truncation count (displayed != full); incl. dynamic squeeze
    missing_sources: int
    full_description_chars: int
    displayed_description_chars: int
    shortened_names: tuple[str, ...]
    effective_budget: int  # approximate Codex dynamic cap = max displayed length
    over_hard_cap_names: tuple[str, ...]  # all source > HARD_CAP (local + managed)
    over_hard_cap_local_names: tuple[str, ...]  # editable subset = actionable local debt
    over_hard_cap_managed_names: tuple[str, ...]  # Codex/plugin-owned, not locally editable

    @property
    def healthy(self) -> bool:
        """No locally-actionable source debt.

        ``shortened`` on rule-compliant entries is informational (Codex's dynamic
        budget squeeze, not a rule violation). ``over_hard_cap_managed_names``
        (Codex ``.system`` builtins / plugin skills) is reported but not a health
        failure — those descriptions are owned upstream and re-synced, not
        editable here. Health fails only on locally-editable over-cap sources.
        """
        return self.entries > 0 and self.missing_sources == 0 and not self.over_hard_cap_local_names


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


def _is_managed(path: Path) -> bool:
    """True for skills that are NOT first-party local debt.

    Over-cap descriptions on these paths are reported but do not fail health:
    they are owned upstream and re-synced, not hand-edited under a personal
    skill dir.

    Covered:
    - Codex ``.system`` builtins
    - Installed plugins / marketplaces (``/plugins/``)
    - Vendored skill packs under ``~/.claude/skills-sources/`` (Google Android,
      Chris Banes, etc.) — often linked into ``~/.claude/skills/``; both the
      symlink path and the resolved target are checked
    """
    markers = ("/.system/", "/plugins/", "/skills-sources/")
    candidates = [str(path)]
    try:
        candidates.append(str(path.resolve()))
    except OSError:
        pass
    for text in candidates:
        if text.endswith("/.system"):
            return True
        if any(marker in text for marker in markers):
            return True
    return False


def parse_prompt_input(payload: object) -> BudgetReport:
    """Build a loss report from ``codex debug prompt-input`` JSON."""
    listing = next(
        (text for text in _collect_strings(payload) if "<skills_instructions>" in text),
        "",
    )
    roots = {match.group(1): match.group(2) for match in _ROOT_RE.finditer(listing)}
    shortened: list[str] = []
    over_hard: list[str] = []
    over_hard_local: list[str] = []
    over_hard_managed: list[str] = []
    missing = full_chars = displayed_chars = entries = max_displayed = 0
    for line in listing.splitlines():
        match = _ENTRY_RE.fullmatch(line)
        if not match:
            continue
        name, displayed, raw_path = match.groups()
        entries += 1
        displayed_chars += len(displayed)
        if len(displayed) > max_displayed:
            max_displayed = len(displayed)
        resolved = _expand_source(raw_path, roots)
        full = _description(resolved)
        if full is None:
            missing += 1
            continue
        full_chars += len(full)
        if len(full) > HARD_CAP:
            over_hard.append(name)
            (over_hard_managed if _is_managed(resolved) else over_hard_local).append(name)
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
        effective_budget=max_displayed,
        over_hard_cap_names=tuple(over_hard),
        over_hard_cap_local_names=tuple(over_hard_local),
        over_hard_cap_managed_names=tuple(over_hard_managed),
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
