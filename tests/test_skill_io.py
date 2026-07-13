"""Tests for shared/skill_io.py: frontmatter parsing + multi-level detection."""

from __future__ import annotations

import json
import os
import time

from skill_router.shared.skill_io import (
    catalog,
    clear_catalog_cache,
    find_skill,
    parse_frontmatter,
)


def test_parse_frontmatter_extracts_name_and_description() -> None:
    text = '---\nname: foo\ndescription: "Foo does bar."\n---\n\nbody'
    name, desc, _ = parse_frontmatter(text)
    assert name == "foo"
    assert desc == "Foo does bar."


def test_parse_frontmatter_decodes_double_quoted_yaml_escapes() -> None:
    text = '---\nname: foo\ndescription: "Use \\"quoted\\" triggers."\n---\n'
    _, desc, _ = parse_frontmatter(text)
    assert desc == 'Use "quoted" triggers.'


def test_parse_frontmatter_missing_returns_empty() -> None:
    name, desc, _ = parse_frontmatter("no frontmatter here")
    assert name == ""
    assert desc == ""


def test_catalog_lists_all_skills(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    skills = catalog()
    names = {s.name for s in skills}
    assert names == {"alpha", "beta", "gamma"}


def test_multilevel_detection(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    beta = find_skill("beta")
    assert beta is not None
    assert beta.is_multilevel is True
    assert len(beta.sections) == 3
    slugs = {s.slug for s in beta.sections}
    assert slugs == {"lazy-loading", "n-plus-1", "transactions"}


def test_legacy_skill_has_no_sections(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    alpha = find_skill("alpha")
    assert alpha is not None
    assert alpha.legacy is True
    assert alpha.sections == []


def test_find_skill_missing_returns_none(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    assert find_skill("does-not-exist") is None


def test_catalog_empty_when_no_skills(isolated_claude_home) -> None:  # type: ignore[no-untyped-def]
    assert catalog() == []


def test_enriched_section_metadata_parses(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    skill_md = fake_claude_home / "skills" / "beta" / "SKILL.md"
    skill_md.write_text(
        """---
name: beta
description: "Beta multi-level skill for spring boot jpa patterns."
sections:
  - lazy-loading: Lazy Loading & Proxy Detection
    keywords: lazy loading, proxy, entitygraph
    aliases: proxies, hibernate proxy
    tools: context7
    doc_namespaces: spring, hibernate
---

# Beta
"""
    )
    beta = find_skill("beta")
    assert beta is not None
    section = beta.sections[0]
    assert section.slug == "lazy-loading"
    assert section.keywords == ("lazy loading", "proxy", "entitygraph")
    assert section.aliases == ("proxies", "hibernate proxy")
    assert section.tools == ("context7",)
    assert section.doc_namespaces == ("spring", "hibernate")


# --- catalog cache (mtime-signature invalidation) -------------------------
def test_catalog_cache_returns_same_object_on_unchanged_fs(
    fake_claude_home,
) -> None:  # type: ignore[no-untyped-def]
    clear_catalog_cache()
    first = catalog()
    second = catalog()
    # Steady state: identical list object (cache hit), not a rebuild.
    assert first is second


def test_catalog_disk_cache_is_safe_json(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    from skill_router.shared import skill_io

    clear_catalog_cache()
    catalog()
    snapshot, _ = skill_io._disk_cache_paths()
    assert snapshot.name == "catalog.json"
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert {item["name"] for item in payload} == {"alpha", "beta", "gamma"}


def test_catalog_cache_invalidates_on_skill_md_edit(
    fake_claude_home,
) -> None:  # type: ignore[no-untyped-def]
    clear_catalog_cache()
    first = catalog()
    # Rewrite one SKILL.md and bump its mtime into the future.
    skill_md = fake_claude_home / "skills" / "alpha" / "SKILL.md"
    skill_md.write_text('---\nname: alpha\ndescription: "Changed description."\n---\n\n# Alpha\n')
    future = time.time() + 5
    os.utime(skill_md, (future, future))
    second = catalog()
    assert second is not first  # rebuilt
    alpha = next((s for s in second if s.name == "alpha"), None)
    assert alpha is not None
    assert alpha.description == "Changed description."


def test_catalog_cache_invalidates_on_undeclared_section_add(
    fake_claude_home,
) -> None:  # type: ignore[no-untyped-def]
    # Skill with an UNDECLARED sections/ dir (indexed from disk, not frontmatter):
    # adding a section file must invalidate the cache via the sections/ dir mtime.
    sk_dir = fake_claude_home / "skills" / "delta"
    (sk_dir / "sections").mkdir(parents=True)
    (sk_dir / "SKILL.md").write_text(
        '---\nname: delta\ndescription: "Delta undeclared-sections skill."\n---\n\n# Delta\n'
    )
    (sk_dir / "sections" / "first.md").write_text("# First Topic\n")
    clear_catalog_cache()
    first = catalog()
    delta = next(s for s in first if s.name == "delta")
    assert [s.slug for s in delta.sections] == ["first"]

    new_md = sk_dir / "sections" / "second.md"
    new_md.write_text("# Second Topic\n")
    future = time.time() + 5
    os.utime(sk_dir / "sections", (future, future))
    second = catalog()
    assert second is not first  # rebuilt
    delta = next(s for s in second if s.name == "delta")
    assert {s.slug for s in delta.sections} == {"first", "second"}


def test_catalog_bypass_with_use_cache_false(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    clear_catalog_cache()
    cached = catalog()  # populates cache
    fresh = catalog(use_cache=False)
    # Bypass returns a freshly built list, distinct from the cached one.
    assert fresh is not cached
    assert [s.name for s in fresh] == [s.name for s in cached]
