#!/usr/bin/env python3
"""Split a monolith SKILL.md into a multi-level skill with section metadata.

Backs up the original SKILL.md, extracts each H2 section listed in --map into
sections/<slug>.md, and rewrites SKILL.md as frontmatter + TOC pointing at the
new section files. Headings not in the map stay inline.

Reusable: was split_jpa_patterns.py (hardcoded). Now `split_skill.py <name>` +
`--map 'H2 Heading=slug,H2=slug,...'`. Auto-detects sections if --map omitted
(slug = kebab-case of the heading).

Idempotent by default: refuses if sections/ already exists. Use --force only
when intentionally regenerating a split skill.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path


def _kebab(heading: str) -> str:
    """'N+1 Problem' -> 'n-plus-1'; 'Lazy Loading' -> 'lazy-loading'."""
    s = re.sub(r"[^A-Za-z0-9 +]", "", heading).strip().lower()
    return re.sub(r"\s+", "-", s) if s else "section"


_STOPWORDS = {
    "and",
    "are",
    "but",
    "for",
    "from",
    "how",
    "into",
    "the",
    "this",
    "with",
    "your",
    "para",
    "por",
    "una",
    "uno",
    "los",
    "las",
    "del",
    "con",
    "que",
}


def _keywords(heading: str, body: str, limit: int = 12) -> tuple[str, ...]:
    """Small deterministic keyword extractor for frontmatter hints."""
    text = f"{heading}\n{body[:4000]}"
    tokens = [
        t.lower()
        for t in re.findall(r"[A-Za-z][A-Za-z0-9+._-]{2,}", text)
        if t.lower() not in _STOPWORDS
    ]
    counts = Counter(tokens)
    ordered: list[str] = []
    for token in re.findall(r"[A-Za-z][A-Za-z0-9+._-]{2,}", heading):
        low = token.lower()
        if low not in ordered and low not in _STOPWORDS:
            ordered.append(low)
    for token, _count in counts.most_common(limit * 2):
        if token not in ordered:
            ordered.append(token)
        if len(ordered) >= limit:
            break
    return tuple(ordered[:limit])


def split_h2(text: str) -> list[tuple[str, str]]:
    """Return [(heading, body), ...] splitting text on '## ' headings."""
    parts = re.split(r"^## ", text, flags=re.M)
    sections = []
    for part in parts[1:]:  # parts[0] is the preamble
        nl = part.find("\n")
        heading = part[:nl].strip() if nl > 0 else part.strip()
        body = part[nl + 1 :] if nl > 0 else ""
        sections.append((heading, body))
    return sections


def parse_map(spec: str | None, sections: list[tuple[str, str]] | None = None) -> dict[str, str]:
    """Return {heading: slug}. If spec is None, auto-kebab every H2 from `sections`."""
    if spec is None:
        secs = sections or []
        return {h: _kebab(h) for h, _ in secs}
    out: dict[str, str] = {}
    for entry in spec.split(","):
        if "=" in entry:
            h, slug = entry.split("=", 1)
            out[h.strip()] = slug.strip()
        else:
            out[entry.strip()] = _kebab(entry.strip())
    return out


def split_skill(
    skill_dir: Path,
    slug_map: dict[str, str] | None = None,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> int:
    """Perform the split. Returns 0 on success, 1 on error."""
    skill_md = skill_dir / "SKILL.md"
    sections_dir = skill_dir / "sections"
    backup = skill_dir / "SKILL.md.pre-multilevel.bak"

    if not skill_md.exists():
        print(f"ERROR: {skill_md} not found", file=sys.stderr)
        return 1
    if sections_dir.exists() and not force:
        print(
            f"ERROR: {sections_dir} already exists — refusing to overwrite. Use --force to regenerate.",
            file=sys.stderr,
        )
        return 1

    text = skill_md.read_text(errors="ignore")
    m = re.match(r"^(---\n.*?\n---\n)(.*)", text, re.S)
    if not m:
        print("ERROR: no frontmatter found", file=sys.stderr)
        return 1
    frontmatter = m.group(1)
    body = m.group(2)

    sections = split_h2(body)
    slug_lookup = slug_map or {h: _kebab(h) for h, _ in sections}

    extracted: list[tuple[str, str, str]] = []  # (heading, slug, body)
    inline: list[tuple[str, str]] = []
    for heading, sbody in sections:
        slug = slug_lookup.get(heading)
        if slug:
            extracted.append((heading, slug, sbody))
        else:
            inline.append((heading, sbody))

    if not extracted:
        print("ERROR: no mapped sections found; nothing to split", file=sys.stderr)
        return 1

    print(f"Skill: {skill_dir.name}")
    print(f"Extracted sections: {len(extracted)}")
    for heading, slug, sbody in extracted:
        print(f"  - {slug:28} {sbody.count(chr(10)) + 1:>4}L  {heading}")
    print(f"Inline sections kept: {len(inline)}")
    if dry_run:
        return 0

    shutil.copy2(skill_md, backup)
    if sections_dir.exists() and force:
        shutil.rmtree(sections_dir)
    sections_dir.mkdir(parents=True)
    for heading, slug, sbody in extracted:
        (sections_dir / f"{slug}.md").write_text(f"## {heading}\n{sbody}")

    # Rewrite SKILL.md: frontmatter (with sections index) + TOC + inline remainder.
    yaml_lines = ["sections:\n"]
    for heading, slug, sbody in extracted:
        yaml_lines.append(f"  - {slug}: {heading}\n")
        kws = ", ".join(_keywords(heading, sbody))
        if kws:
            yaml_lines.append(f"    keywords: {kws}\n")
    sections_yaml = "".join(yaml_lines)
    fm_text = frontmatter.replace("\n---\n", "\n" + sections_yaml + "\n---\n", 1)

    toc_lines = [
        f"# {skill_dir.name} (multi-level)\n",
        "This skill is split into focused sections. The router suggests the section",
        "most relevant to your prompt; load it directly instead of scanning the whole body.\n",
        "## Section index\n",
    ]
    for heading, slug, _ in extracted:
        toc_lines.append(f"- **{heading}** → `sections/{slug}.md`")
    toc_lines.append("")
    if inline:
        toc_lines.append("## General reference (inline)\n")
        for heading, sbody in inline:
            toc_lines.append(f"## {heading}\n{sbody}")

    skill_md.write_text(fm_text + "\n".join(toc_lines) + "\n")

    print(f"OK: split {len(extracted)} sections -> {sections_dir}")
    print(f"Backup: {backup}")
    print(f"Inline (kept in SKILL.md): {len(inline)} section(s)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Split a monolith SKILL.md into a multi-level skill (sections/)."
    )
    p.add_argument("skill", help="skill name (dir under ~/.claude/skills/)")
    p.add_argument(
        "--map",
        help="comma-list of 'H2 Heading=slug' entries. Omit to auto-kebab every H2 section.",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="show planned split without writing files"
    )
    p.add_argument(
        "--force", action="store_true", help="regenerate an existing sections/ directory"
    )
    p.add_argument(
        "--claude-home",
        default=os.environ.get("CLAUDE_HOME", str(Path.home() / ".claude")),
        help="Claude home containing skills/ (default: CLAUDE_HOME or ~/.claude)",
    )
    args = p.parse_args()

    skill_dir = Path(args.claude_home).expanduser() / "skills" / args.skill
    slug_map = parse_map(args.map, None) if args.map else None
    return split_skill(skill_dir, slug_map, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
