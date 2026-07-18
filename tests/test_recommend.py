"""Offline tests for the semantic skill recommender.

Embeddings (Ollama) are stubbed — these tests exercise the ranking plumbing
(lexical fallback, disk index build/persist, cosine top-k) deterministically
without a live model. The live-embedding smoke path is covered by the CLI
`skill-router recommend` against the real catalog.
"""

from __future__ import annotations

import json

import pytest

from skill_router.features.recommend import command as rec_mod
from skill_router.features.recommend.command import (
    RECOMMEND_LEXICAL_FLOOR,
    Recommendation,
    _lexical_overlap,
    _tokens,
    index_status,
    recommend,
)
from skill_router.shared import embed as embed_mod
from skill_router.shared.skill_io import catalog

_DIM = 512


def _bow_embed(text: str, **_kwargs: object) -> list[float]:
    """Deterministic bag-of-words embedding: cosine == token Jaccard.

    Lets tests assert which skill SHOULD win by controlling shared tokens,
    without any model.
    """

    def tok(t: str) -> set[str]:
        return {w for w in __import__("re").findall(r"[a-z0-9]{3,}", t.lower())}

    vec = [0.0] * _DIM

    def h(w: str) -> int:
        return sum(ord(c) for c in w) % _DIM

    for w in tok(text):
        vec[h(w)] = 1.0
    return vec


# --------------------------------------------------------------------------------
# Lexical fallback (Ollama down)
# --------------------------------------------------------------------------------


def test_recommend_never_raises_on_empty(fake_claude_home) -> None:  # type: ignore[no-untyped-def]
    assert recommend("", catalog()) == []
    assert recommend("anything", []) == []
    assert recommend("   ") == []


def test_lexical_fallback_when_ollama_down(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(embed_mod, "is_alive", lambda: False)
    recs = recommend("acme widgets gadget", catalog())
    assert recs, "lexical fallback should still match on token overlap"
    assert recs[0].mode == "lexical"
    assert recs[0].skill == "alpha"
    assert all(r.score >= RECOMMEND_LEXICAL_FLOOR for r in recs)


def test_lexical_fallback_no_match_returns_empty(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(embed_mod, "is_alive", lambda: False)
    # "zzz qqq" shares no 3+ char token with any fake skill description.
    assert recommend("zzz qqq xyzzy", catalog()) == []


def test_explicit_lexical_mode_skips_semantic_backend(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        rec_mod,
        "_semantic_recommend",
        lambda *_args, **_kwargs: pytest.fail("semantic backend must stay cold"),
    )
    recs = recommend("acme widgets gadget", catalog(), semantic=False)
    assert recs and recs[0].mode == "lexical"


def test_lexical_overlap_rejects_short_substring_false_positives() -> None:
    """Short generic fragments are not evidence for a specialist skill."""
    prompt = _tokens("fix API bug for users; create_user returns 500")
    web = _tokens(
        "web-scrape Web scraping and page reading via curl. "
        "Use when search tools are unavailable."
    )

    overlap = _lexical_overlap(prompt, web)

    assert "api" not in overlap  # ``api`` is a substring of ``scraping``
    assert "users" not in overlap  # ``use`` used to match ``users``
    assert not overlap


# --------------------------------------------------------------------------------
# Semantic path (stubbed embeddings)
# --------------------------------------------------------------------------------


def test_semantic_recommend_ranks_relevant_skill_first(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(embed_mod, "is_alive", lambda: True)
    monkeypatch.setattr(embed_mod, "embed", _bow_embed)
    recs = recommend("angular standalone components signals", catalog(), top_k=2)
    assert recs, "semantic path must return matches"
    assert recs[0].mode == "semantic"
    assert recs[0].skill == "gamma"  # gamma description mentions all three


def test_semantic_index_persists_to_disk(fake_claude_home, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embed_mod, "is_alive", lambda: True)
    monkeypatch.setattr(embed_mod, "embed", _bow_embed)
    recommend("spring boot jpa", catalog())  # triggers index build
    status = index_status()
    assert status["has_index"], "on-disk index must be written after first build"
    assert status["indexed_skills"] == len(catalog())
    assert status["dim"] == _DIM


def test_semantic_respects_floor_threshold(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A prompt sharing no tokens with any skill should return nothing."""
    monkeypatch.setattr(embed_mod, "is_alive", lambda: True)
    monkeypatch.setattr(embed_mod, "embed", _bow_embed)
    assert recommend("zzz qqq xyzzy", catalog(), floor=0.99) == []


def test_semantic_drops_weak_and_far_from_best_matches(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The hook should inject specialists, not fill context with adjacent noise."""
    monkeypatch.setattr(embed_mod, "is_alive", lambda: True)
    monkeypatch.setattr(embed_mod, "embed", _bow_embed)
    recs = recommend("angular standalone components signals", catalog(), top_k=3)
    assert recs
    assert recs[0].skill == "gamma"
    assert all(rec.score >= recs[0].score - rec_mod.RECOMMEND_RELATIVE_BAND for rec in recs)


def test_index_meta_records_mtime(fake_claude_home, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embed_mod, "is_alive", lambda: True)
    monkeypatch.setattr(embed_mod, "embed", _bow_embed)
    recommend("alpha", catalog())
    _, meta_path, _ = rec_mod._index_paths()
    meta = json.loads(meta_path.read_text())
    skills = catalog()
    assert set(meta) == {sk.name for sk in skills}
    assert all(isinstance(v, int) for v in meta.values())


def test_top_k_is_bounded(fake_claude_home, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embed_mod, "is_alive", lambda: True)
    monkeypatch.setattr(embed_mod, "embed", _bow_embed)
    recs = recommend("skill", catalog(), top_k=99)
    assert len(recs) <= rec_mod.RECOMMEND_MAX_TOP_K


def test_recommendation_to_hints_excludes_already_surfaced(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(embed_mod, "is_alive", lambda: True)
    monkeypatch.setattr(embed_mod, "embed", _bow_embed)
    recs = [
        Recommendation(skill="alpha", score=0.9, reason="x", mode="semantic"),
        Recommendation(skill="gamma", score=0.5, reason="y", mode="semantic"),
    ]
    hints = rec_mod.recommendations_to_hints(recs, exclude={"alpha"})
    assert len(hints) == 1
    assert "gamma" in hints[0]


def test_isolated_home_yields_no_recommendations(
    isolated_claude_home, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty catalog -> empty recommendations, no crash."""
    monkeypatch.setattr(embed_mod, "is_alive", lambda: True)
    monkeypatch.setattr(embed_mod, "embed", _bow_embed)
    assert recommend("anything", catalog()) == []


def test_prompt_truncation_guards_giant_input(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pasted log/stacktrace (tens of KB) is truncated to 2K before embedding."""
    monkeypatch.setattr(embed_mod, "is_alive", lambda: True)
    monkeypatch.setattr(embed_mod, "embed", _bow_embed)
    big = "acme widgets gadget " * 500  # ~10K chars
    full = recommend(big, catalog(), top_k=2)
    truncated = recommend(big[:2000], catalog(), top_k=2)
    assert full == truncated, "giant prompt must be truncated to its first 2K chars"


def test_unicode_and_emoji_prompt_does_not_crash(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-ASCII / emoji prompts must flow through embedding without error."""
    monkeypatch.setattr(embed_mod, "is_alive", lambda: True)
    monkeypatch.setattr(embed_mod, "embed", _bow_embed)
    recs = recommend("café résumé naïve 🚀 über", catalog())
    assert isinstance(recs, list)
