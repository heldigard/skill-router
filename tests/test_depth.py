"""Tests for features/depth/command.py: legacy/summary/body decisions.

Embeddings (Ollama) are NOT exercised here — these tests stub out is_alive/embed
so the depth logic is deterministic and offline. The bench probe in audit covers
the live-embedding path (skipped when Ollama is down).
"""

from __future__ import annotations

import pytest

from skill_router.features.depth import command as depth_mod
from skill_router.shared.skill_io import find_skill


def test_legacy_skill_returns_body_level(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    alpha = find_skill("alpha")
    assert alpha is not None
    dec = depth_mod.decide("anything", alpha)
    assert dec.level == "body"
    assert dec.skill == "alpha"
    assert "legacy" in dec.reason


def test_multilevel_skill_degrades_to_summary_when_ollama_down(
    fake_claude_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    beta = find_skill("beta")
    assert beta is not None
    monkeypatch.setattr(depth_mod, "is_alive", lambda: False)
    dec = depth_mod.decide("lazy loading", beta)
    assert dec.level == "summary"


def test_section_match_when_top_score_above_threshold(
    fake_claude_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stub embeddings so 'lazy loading' prompt -> 'lazy-loading' section."""
    beta = find_skill("beta")
    assert beta is not None

    # Make the prompt vector identical to the lazy-loading section vector,
    # orthogonal to others.
    def fake_embed(text: str, **_kwargs: object) -> list[float]:
        if "lazy loading" in text.lower() or text.lower().startswith("lazy"):
            return [1.0, 0.0]
        return [0.0, 1.0]

    monkeypatch.setattr(depth_mod, "is_alive", lambda: True)
    monkeypatch.setattr(depth_mod, "embed", fake_embed)
    # Lower threshold so the stubbed identical-vector (cos=1.0) clearly wins.
    dec = depth_mod.decide("lazy loading proxies", beta, threshold=0.5)
    assert dec.level == "section"
    assert dec.section == "lazy-loading"
    assert dec.score == pytest.approx(1.0)


def test_section_match_uses_enriched_metadata(
    fake_claude_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill_md = fake_claude_home / "skills" / "beta" / "SKILL.md"
    skill_md.write_text(
        """---
name: beta
description: "Beta multi-level skill for spring boot jpa patterns."
sections:
  - lazy-loading: Lazy Loading
    keywords: entitygraph, hibernate proxy
    tools: context7
    doc_namespaces: spring, hibernate
  - transactions: Transaction Boundaries
---

# Beta
"""
    )
    beta = find_skill("beta")
    assert beta is not None

    def fake_embed(text: str, **_kwargs: object) -> list[float]:
        if "entitygraph" in text.lower():
            return [1.0, 0.0]
        return [0.0, 1.0]

    monkeypatch.setattr(depth_mod, "is_alive", lambda: True)
    monkeypatch.setattr(depth_mod, "embed", fake_embed)
    depth_mod.clear_section_cache()
    dec = depth_mod.decide("use entitygraph for this query", beta, threshold=0.5)
    assert dec.level == "section"
    assert dec.section == "lazy-loading"
    assert dec.doc_namespaces == ("spring", "hibernate")
    assert dec.tools == ("context7",)


def test_summary_when_top_score_below_threshold(
    fake_claude_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    beta = find_skill("beta")
    assert beta is not None

    def fake_embed(text: str, **_kwargs: object) -> list[float]:
        # 4 orthogonal axes; prompt vec distinct from every section vec.
        low = text.lower()
        if "lazy" in low:
            return [1.0, 0.0, 0.0, 0.0]
        if "n-plus-1" in low or "n + 1" in low:
            return [0.0, 1.0, 0.0, 0.0]
        if "transaction" in low:
            return [0.0, 0.0, 1.0, 0.0]
        return [0.0, 0.0, 0.0, 1.0]

    monkeypatch.setattr(depth_mod, "is_alive", lambda: True)
    monkeypatch.setattr(depth_mod, "embed", fake_embed)
    dec = depth_mod.decide("generic unrelated prompt", beta, threshold=0.9)
    assert dec.level == "summary"


def test_summary_without_lexical_section_match_skips_embeddings(
    fake_claude_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    beta = find_skill("beta")
    assert beta is not None
    calls = 0

    def fake_embed(_text: str, **_kwargs: object) -> list[float]:
        nonlocal calls
        calls += 1
        return [1.0, 0.0]

    monkeypatch.setattr(depth_mod, "is_alive", lambda: True)
    monkeypatch.setattr(depth_mod, "embed", fake_embed)
    dec = depth_mod.decide("generic unrelated prompt", beta)
    assert dec.level == "summary"
    assert calls == 0


def test_decide_for_skills_skips_legacy(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    from skill_router.shared.skill_io import catalog

    skills = catalog()
    decisions = depth_mod.decide_for_skills("anything", skills)
    # Only beta is multi-level among alpha/beta/gamma -> exactly 1 decision.
    assert len(decisions) == 1
    assert decisions[0].skill == "beta"


def test_decide_for_skills_caps_multilevel_evaluations(
    fake_claude_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # type: ignore[no-untyped-def]
    from skill_router.shared.skill_io import catalog

    beta_dir = fake_claude_home / "skills" / "delta"
    beta_dir.mkdir()
    (beta_dir / "SKILL.md").write_text(
        """---
name: delta
description: "Delta multi-level skill."
sections:
  - setup: Setup
---

# Delta
"""
    )
    (beta_dir / "sections").mkdir()
    (beta_dir / "sections" / "setup.md").write_text("# Setup\n")

    monkeypatch.setattr(depth_mod, "is_alive", lambda: False)
    decisions = depth_mod.decide_for_skills("setup", catalog(use_cache=False))

    assert len(decisions) == 2


def test_as_hint_section_mentions_path(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    from skill_router.features.depth.command import DepthDecision

    dec = DepthDecision(
        level="section",
        skill="beta",
        section="lazy-loading",
        section_path="/x/sections/lazy-loading.md",
        score=0.9,
    )
    hint = dec.as_hint()
    assert "multi-level" in hint
    assert "lazy-loading" in hint
    assert "sections/lazy-loading.md" in hint


def test_cosine_helper_handles_empty_vectors() -> None:
    assert depth_mod._cosine([], [1.0]) == 0.0
    assert depth_mod._cosine([0.0], [0.0]) == 0.0
    # orthogonal
    assert depth_mod._cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    # parallel
    assert depth_mod._cosine([1.0, 1.0], [1.0, 1.0]) == pytest.approx(1.0)
