"""Skill IO: read/parse SKILL.md frontmatter, detect multi-level layout.

A skill is a directory under ~/.claude/skills/<name>/ containing SKILL.md.
Multi-level skills additionally have a sections/ subdir with one .md per topic.

SKILL.md frontmatter fields used here:
  name        — must equal the directory name
  description — used by Claude Code's skill selector + by our depth/embedding
  sections    — (optional, multi-level) list of "slug: One-line topic" entries

The sections/ layout enables the depth selector to recommend a single section
file instead of loading the whole SKILL.md body — progressive disclosure L2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .paths import skills_root


@dataclass
class Section:
    """One sub-topic file of a multi-level skill."""

    slug: str  # filename stem, e.g. "lazy-loading"
    title: str  # human label, e.g. "Lazy Loading & Proxy Detection"
    path: Path  # absolute path to the section .md


@dataclass
class Skill:
    """One skill catalog entry."""

    name: str  # directory name (== frontmatter `name`)
    description: str  # frontmatter description (for routing/embedding)
    path: Path  # skill directory
    skill_md: Path  # SKILL.md path
    body_lines: int  # SKILL.md line count
    is_multilevel: bool = False  # has sections/ subdir declared
    sections: list[Section] = field(default_factory=list)

    @property
    def legacy(self) -> bool:
        """True if this skill is monolithic (no sections/, loads body whole)."""
        return not self.is_multilevel


_FM_RE = re.compile(r"^---\s*\n(.*?)\n---", re.S)
_NAME_RE = re.compile(r"^name:\s*(\S+)", re.M)
_DESC_RE = re.compile(r"description:\s*(.*?)(?:\n[a-zA-Z_-]+:|\Z)", re.S | re.I)


def parse_frontmatter(text: str) -> tuple[str, str, str]:
    """Return (name, description, fm_block) from SKILL.md text. Empty strings if absent."""
    fm = _FM_RE.search(text)
    if not fm:
        return "", "", ""
    block = fm.group(1)
    nm = _NAME_RE.search(block)
    ds = _DESC_RE.search(block)
    name = nm.group(1).strip() if nm else ""
    desc = ds.group(1).strip().strip('"').strip("'") if ds else ""
    return name, desc, block


def _parse_sections_index(fm_block: str) -> list[tuple[str, str]]:
    """Parse the `sections:` frontmatter list into [(slug, title), ...].

    Accepts YAML-list or one-per-line `slug: Title` blocks. Tolerant — used for
    routing hints, not enforcement.
    """
    m = re.search(r"^sections:\s*\n((?:\s+.+\n?)+)", fm_block, re.M)
    if not m:
        return []
    out: list[tuple[str, str]] = []
    for raw in m.group(1).splitlines():
        line = raw.strip().lstrip("-").strip()
        if not line:
            continue
        # support both `- slug: Title` and `- slug` (title = slug)
        if ":" in line:
            slug, _, title = line.partition(":")
            out.append((slug.strip(), title.strip()))
        else:
            out.append((line, line))
    return out


def read_skill(skill_dir: Path) -> Skill | None:
    """Build a Skill from a directory. Returns None if not a valid skill."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None
    try:
        text = skill_md.read_text(errors="ignore")
    except OSError:
        return None
    name, desc, fm_block = parse_frontmatter(text)
    body_lines = text.count("\n") + 1
    sections_dir = skill_dir / "sections"
    sections: list[Section] = []
    declared = _parse_sections_index(fm_block)
    if declared:
        for slug, title in declared:
            sec_path = sections_dir / f"{slug}.md"
            sections.append(Section(slug=slug, title=title, path=sec_path))
    elif sections_dir.is_dir():
        # Undeclared sections/: index whatever .md files exist.
        for md in sorted(sections_dir.glob("*.md")):
            slug = md.stem
            title = _first_heading(md) or slug
            sections.append(Section(slug=slug, title=title, path=md))
    return Skill(
        name=name or skill_dir.name,
        description=desc,
        path=skill_dir,
        skill_md=skill_md,
        body_lines=body_lines,
        is_multilevel=bool(sections),
        sections=sections,
    )


def _first_heading(md_path: Path) -> str:
    """Return the first '# heading' in a section file, else empty string."""
    try:
        text = md_path.read_text(errors="ignore")
    except OSError:
        return ""
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def catalog() -> list[Skill]:
    """Read every valid skill in the canonical catalog."""
    root = skills_root()
    if not root.is_dir():
        return []
    out: list[Skill] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        sk = read_skill(d)
        if sk is not None:
            out.append(sk)
    return out


def find_skill(name: str) -> Skill | None:
    """Look up a single skill by directory name."""
    root = skills_root()
    d = root / name
    if not d.is_dir():
        return None
    return read_skill(d)
