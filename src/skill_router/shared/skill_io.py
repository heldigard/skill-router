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
    keywords: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    doc_namespaces: tuple[str, ...] = ()


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


def _split_inline_list(value: str) -> tuple[str, ...]:
    """Parse `a, b` or `[a, b]` into a tuple of strings."""
    value = value.strip().strip("[]")
    if not value:
        return ()
    return tuple(part.strip().strip('"').strip("'") for part in value.split(",") if part.strip())


def _parse_sections_index(fm_block: str) -> list[dict[str, object]]:
    """Parse the `sections:` frontmatter list.

    Accepts the compact historical form:

      - lazy-loading: Lazy Loading

    and an enriched form:

      - lazy-loading: Lazy Loading
        keywords: lazy loading, proxy, EntityGraph
        doc_namespaces: spring, hibernate

    Tolerant by design: the router should keep working even if a skill's
    metadata is incomplete.
    """
    m = re.search(r"^sections:\s*\n((?:\s+.+\n?)+)", fm_block, re.M)
    if not m:
        return []
    out: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for raw in m.group(1).splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("-"):
            line = stripped.lstrip("-").strip()
            if not line:
                current = None
                continue
            if ":" in line:
                slug, _, title = line.partition(":")
                current = {"slug": slug.strip(), "title": title.strip() or slug.strip()}
            else:
                current = {"slug": line, "title": line}
            out.append(current)
            continue
        if current is None or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip().replace("-", "_")
        value = value.strip()
        if key in {"keywords", "aliases", "tools", "doc_namespaces"}:
            current[key] = _split_inline_list(value)
        elif key in {"docs", "namespaces"}:
            current["doc_namespaces"] = _split_inline_list(value)
        elif key == "title":
            current["title"] = value
        elif key == "slug":
            current["slug"] = value
    return out


def _as_str_tuple(value: object) -> tuple[str, ...]:
    """Coerce a parsed frontmatter value to a tuple of strings.

    ``_parse_sections_index`` stores either a plain string (legacy form) or a
    ``tuple[str, ...]`` (from ``_split_inline_list``) under each section key.
    This normalizes both — and ``None`` — to a flat ``tuple[str, ...]`` so the
    Section dataclass gets a typed value without ``cast``.
    """
    if isinstance(value, tuple):
        return tuple(str(v) for v in value if str(v))
    if isinstance(value, str):
        return (value,) if value.strip() else ()
    return ()


def _section_from_decl(decl: dict[str, object], sections_dir: Path) -> Section | None:
    """Build a Section from parsed frontmatter metadata."""
    slug = str(decl.get("slug", "")).strip()
    if not slug:
        return None
    title = str(decl.get("title", slug)).strip() or slug
    sec_path = sections_dir / f"{slug}.md"
    return Section(
        slug=slug,
        title=title,
        path=sec_path,
        keywords=_as_str_tuple(decl.get("keywords")),
        aliases=_as_str_tuple(decl.get("aliases")),
        tools=_as_str_tuple(decl.get("tools")),
        doc_namespaces=_as_str_tuple(decl.get("doc_namespaces")),
    )


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
        for decl in declared:
            sec = _section_from_decl(decl, sections_dir)
            if sec is not None:
                sections.append(sec)
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


# Process-local catalog cache. Keyed by skills_root() Path so distinct CLAUDE_HOME
# values (tests use per-test tmp_path) never collide. Value = (mtime_sig, skills).
# The signature is the max mtime across the root, every skill dir, and every
# SKILL.md — so add/remove/rename of a skill OR an in-place edit of its
# frontmatter/body invalidates the cache. stat() is ~10x cheaper than
# read_text()+parse, so recomputing the signature every call still beats a full
# rescan of 100+ skills on every UserPromptSubmit prompt.
_CATALOG_CACHE: dict[Path, tuple[float, list[Skill]]] = {}


def _safe_mtime(path: Path) -> float:
    """Return ``path.stat().st_mtime`` or 0.0 on OSError (missing/unreadable)."""
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _catalog_signature(root: Path) -> float:
    """Max mtime across root + skill dirs + SKILL.md + sections/ dirs.

    The sections/ dir mtime catches add/remove/rename of section files for
    skills whose sections are indexed from disk (undeclared in frontmatter).
    In-place edits to a section file's heading are NOT caught (would need an
    O(N-sections) stat sweep); declared-section skills are unaffected since
    their index lives in SKILL.md frontmatter.

    Returns 0.0 when nothing is stat-able (treated as always-miss for safety).
    """
    mtimes: list[float] = [_safe_mtime(root)]
    for d in root.iterdir():
        if not d.is_dir() or d.name.startswith("."):
            continue
        mtimes.append(_safe_mtime(d))
        mtimes.append(_safe_mtime(d / "SKILL.md"))
        mtimes.append(_safe_mtime(d / "sections"))
    return max(mtimes) if mtimes else 0.0


def clear_catalog_cache() -> None:
    """Drop the catalog cache. Tests that mutate SKILL.md after a first read
    can call this; mtime-signature invalidation normally makes it unnecessary."""
    _CATALOG_CACHE.clear()


def catalog(use_cache: bool = True) -> list[Skill]:
    """Read every valid skill in the canonical catalog.

    Cached by mtime-signature when ``use_cache`` is True (default). The hook
    path (UserPromptSubmit) calls this on every prompt, so the cache turns an
    O(N-skills) FS scan + frontmatter parse into O(N-skills) cheap ``stat()``
    calls on the steady state. CLI commands that must see fresh data
    (e.g. ``audit`` after edits) pass ``use_cache=False``.
    """
    root = skills_root()
    if not root.is_dir():
        return []
    sig: float = 0.0
    if use_cache:
        sig = _catalog_signature(root)
        cached = _CATALOG_CACHE.get(root)
        if cached is not None and cached[0] == sig:
            return cached[1]
    out: list[Skill] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        sk = read_skill(d)
        if sk is not None:
            out.append(sk)
    if use_cache:
        _CATALOG_CACHE[root] = (sig, out)
    return out


def find_skill(name: str) -> Skill | None:
    """Look up a single skill by directory name."""
    root = skills_root()
    d = root / name
    if not d.is_dir():
        return None
    return read_skill(d)
