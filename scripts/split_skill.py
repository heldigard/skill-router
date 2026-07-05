#!/usr/bin/env python3
"""Generalized one-shot splitter: monolith SKILL.md -> multi-level skill.

Backs up the original SKILL.md, extracts each H2 section listed in --map into
sections/<slug>.md, and rewrites SKILL.md as frontmatter + TOC pointing at the
new section files. Headings not in the map stay inline.

Reusable: was split_jpa_patterns.py (hardcoded). Now `split_skill.py <name>` +
`--map 'H2 Heading=slug,H2=slug,...'`. Auto-detects sections if --map omitted
(slug = kebab-case of the heading).

Idempotent: refuses if sections/ already exists (delete it first to re-run).
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path


def _kebab(heading: str) -> str:
    """'N+1 Problem' -> 'n-plus-1'; 'Lazy Loading' -> 'lazy-loading'."""
    s = re.sub(r"[^A-Za-z0-9 +]", "", heading).strip().lower()
    return re.sub(r"\s+", "-", s) if s else "section"


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


def split_skill(skill_dir: Path, slug_map: dict[str, str] | None = None) -> int:
    """Perform the split. Returns 0 on success, 1 on error."""
    skill_md = skill_dir / "SKILL.md"
    sections_dir = skill_dir / "sections"
    backup = skill_dir / "SKILL.md.pre-multilevel.bak"

    if not skill_md.exists():
        print(f"ERROR: {skill_md} not found", file=sys.stderr)
        return 1
    if sections_dir.exists():
        print(
            f"ERROR: {sections_dir} already exists — refusing to overwrite. Delete it to re-run.",
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

    shutil.copy2(skill_md, backup)
    sections_dir.mkdir(parents=True)
    for heading, slug, sbody in extracted:
        (sections_dir / f"{slug}.md").write_text(f"## {heading}\n{sbody}")

    # Rewrite SKILL.md: frontmatter (with sections index) + TOC + inline remainder.
    sections_yaml = "sections:\n" + "".join(
        f"  - {slug}: {heading}\n" for heading, slug, _ in extracted
    )
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
    args = p.parse_args()

    skill_dir = Path.home() / ".claude" / "skills" / args.skill
    slug_map = parse_map(args.map, None) if args.map else None
    return split_skill(skill_dir, slug_map)


if __name__ == "__main__":
    sys.exit(main())
