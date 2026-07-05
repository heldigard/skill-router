"""Catalog rendering: list skills, flag multi-level, surface oversized bodies.

Reads via shared.skill_io.catalog(). Output is plain-text for CLI consumption.
"""

from __future__ import annotations

from ...shared.skill_io import Skill, catalog


def list_all(only_multilevel: bool = False, min_lines: int = 0) -> str:
    """Render the catalog. Optional filters: multi-level only, min body lines."""
    skills = catalog()
    rows: list[str] = []
    for sk in skills:
        if only_multilevel and not sk.is_multilevel:
            continue
        if min_lines and sk.body_lines < min_lines:
            continue
        flag = "ML" if sk.is_multilevel else "  "
        secs = f"  sections={len(sk.sections)}" if sk.is_multilevel else ""
        rows.append(f"[{flag}] {sk.name:32} {sk.body_lines:>4}L{secs}")
    header = f"Catalog: {len(rows)} skill(s)"
    if only_multilevel:
        header += " (multi-level only)"
    if min_lines:
        header += f" (>= {min_lines}L)"
    return header + "\n" + "\n".join(rows)


def show(name: str) -> str:
    """Render one skill in detail: frontmatter + sections."""
    from ...shared.skill_io import find_skill

    sk = find_skill(name)
    if sk is None:
        return f"(skill not found: {name})"
    lines = [
        f"# {sk.name}",
        f"path: {sk.path}",
        f"body: {sk.body_lines}L",
        f"multi-level: {sk.is_multilevel}",
        "",
        "## description",
        sk.description or "(none)",
    ]
    if sk.is_multilevel:
        lines.append("")
        lines.append("## sections")
        for sec in sk.sections:
            exists = "✓" if sec.path.exists() else "✗"
            lines.append(f"  {exists} {sec.slug:24} {sec.title}")
    return "\n".join(lines)


def oversized(threshold: int = 400) -> list[Skill]:
    """Skills whose body exceeds the threshold (split candidates)."""
    return [sk for sk in catalog() if sk.body_lines > threshold]
