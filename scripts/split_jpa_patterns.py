#!/usr/bin/env python3
"""One-shot pilot splitter: jpa-patterns (monolith) -> multi-level skill.

Backs up the original SKILL.md, extracts each H2 section into sections/<slug>.md,
and rewrites SKILL.md as frontmatter + TOC pointing at the new section files.

Idempotent: detects an existing sections/ dir and refuses (delete it first to
re-run). Run from anywhere; paths are absolute.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

SKILL_DIR = Path.home() / ".claude" / "skills" / "jpa-patterns"
SKILL_MD = SKILL_DIR / "SKILL.md"
SECTIONS_DIR = SKILL_DIR / "sections"
BACKUP = SKILL_DIR / "SKILL.md.pre-multilevel.bak"

# Slug map: H2 heading -> file slug. Headings not in this map stay inline.
SLUG_MAP = {
    "N+1 Problem": "n-plus-1",
    "Lazy Loading": "lazy-loading",
    "Transactions": "transactions",
    "Entity Relationships": "entity-relationships",
    "Query Optimization": "query-optimization",
    "Caching": "caching",
    "Performance Pitfalls": "performance-pitfalls",
}


def split_h2(text: str) -> list[tuple[str, str]]:
    """Return [(heading, body), ...] splitting text on '## ' headings."""
    parts = re.split(r"^## ", text, flags=re.M)
    # First part is the preamble (frontmatter + intro) before any ## — skip.
    sections = []
    for part in parts[1:]:
        nl = part.find("\n")
        heading = part[:nl].strip() if nl > 0 else part.strip()
        body = part[nl + 1 :] if nl > 0 else ""
        sections.append((heading, body))
    return sections


def main() -> int:
    if not SKILL_MD.exists():
        print(f"ERROR: {SKILL_MD} not found", file=sys.stderr)
        return 1
    if SECTIONS_DIR.exists():
        print(
            f"ERROR: {SECTIONS_DIR} already exists — refusing to overwrite. Delete it to re-run.",
            file=sys.stderr,
        )
        return 1

    text = SKILL_MD.read_text(errors="ignore")
    m = re.match(r"^(---\n.*?\n---\n)(.*)", text, re.S)
    if not m:
        print("ERROR: no frontmatter found", file=sys.stderr)
        return 1
    frontmatter = m.group(1)
    body = m.group(2)

    sections = split_h2(body)
    extracted: list[tuple[str, str, str]] = []  # (heading, slug, body)
    inline: list[tuple[str, str]] = []  # (heading, body) kept in SKILL.md
    for heading, sbody in sections:
        slug = SLUG_MAP.get(heading)
        if slug:
            extracted.append((heading, slug, sbody))
        else:
            inline.append((heading, sbody))

    if not extracted:
        print("ERROR: no mapped sections found; nothing to split", file=sys.stderr)
        return 1

    # Backup + write section files.
    shutil.copy2(SKILL_MD, BACKUP)
    SECTIONS_DIR.mkdir(parents=True)
    for heading, slug, sbody in extracted:
        (SECTIONS_DIR / f"{slug}.md").write_text(f"## {heading}\n{sbody}")

    # Rewrite SKILL.md: frontmatter (with sections index) + TOC + inline remainder.
    fm_text = frontmatter
    # Insert sections index into frontmatter (before closing ---).
    sections_yaml = "sections:\n" + "".join(
        f"  - {slug}: {heading}\n" for heading, slug, _ in extracted
    )
    fm_text = fm_text.replace("\n---\n", "\n" + sections_yaml + "\n---\n", 1)

    toc_lines = [
        "# JPA Patterns (multi-level)\n",
        "This skill is split into focused sections. The router suggests the section",
        "most relevant to your prompt; load it directly instead of scanning the whole body.\n",
        "## Section index\n",
    ]
    for heading, slug, _ in extracted:
        toc_lines.append(f"- **{heading}** → `sections/{slug}.md`")
    toc_lines.append("")

    # Keep unmapped inline sections as-is (Quick Reference, When to Use, etc.)
    if inline:
        toc_lines.append("## General reference (inline)\n")
        for heading, sbody in inline:
            toc_lines.append(f"## {heading}\n{sbody}")

    SKILL_MD.write_text(fm_text + "\n".join(toc_lines) + "\n")

    print(f"OK: split {len(extracted)} sections -> {SECTIONS_DIR}")
    print(f"Backup: {BACKUP}")
    print(f"Skills inline: {len(inline)} section(s) kept in SKILL.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
