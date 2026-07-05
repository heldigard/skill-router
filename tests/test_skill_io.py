"""Tests for shared/skill_io.py: frontmatter parsing + multi-level detection."""

from __future__ import annotations

from skill_router.shared.skill_io import catalog, find_skill, parse_frontmatter


def test_parse_frontmatter_extracts_name_and_description() -> None:
    text = '---\nname: foo\ndescription: "Foo does bar."\n---\n\nbody'
    name, desc, _ = parse_frontmatter(text)
    assert name == "foo"
    assert desc == "Foo does bar."


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
