"""Semantic skill recommender: prompt -> top-k relevant skills via embeddings.

Purpose
-------
The skill-router's regex routes cover ~60 hand-written patterns, but the live
catalog is ~115 local skills (+ plugin skills). Skills without a matching route
are invisible to the router unless the model happens to read their description
in the system-prompt catalog — and ``skillListingBudgetFraction`` silently
DROPS catalog entries past the budget. This recommender closes that gap:

  1. Embed ``name: description`` of every catalog skill ONCE, cache to disk.
  2. Per prompt: embed the prompt (~0.1s warm), cosine-rank vs the cached
     matrix, return the top-k skills above a floor threshold.
  3. Lexical fallback (token overlap) when Ollama or numpy is unavailable.

The UserPromptSubmit hook can then hint those skill NAMES directly in
``additionalContext`` — resuscitating budget-dropped skills and matching
synonyms/paraphrases the regex routes miss (e.g. "slow query" -> postgres).

Why a disk index (not process cache)
------------------------------------
Every hook invocation is a fresh subprocess, so a module-level cache does not
survive between prompts. Embedding ~115 skills per prompt (cold model ~2s each)
is infeasible inside the prompt-submit budget. A disk index built once (and
updated incrementally by mtime when a SKILL.md changes) makes the per-prompt
cost just one prompt embedding + a cosine over a prebuilt matrix.

Design mirrors ``features/depth/command.py``: late imports, graceful lexical
degradation, bounded timeout, fail-open (never raises).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from ...shared.config import DEPTH_EMBED_TIMEOUT
from ...shared.skill_io import Skill

# Catalog build embeds ~115 skills once (cold model ~2s each); this is a
# one-shot batch op like audit, NOT the per-prompt hook path. Use the generous
# audit timeout so a cold embeddinggemma doesn't silently starve every embed
# and produce an empty index. The per-prompt path keeps DEPTH_EMBED_TIMEOUT.

# Floor cosine for a skill to be "relevant" at catalog granularity. Section
# matching (depth) uses 0.60 because section titles are narrow; catalog
# descriptions are broad paragraphs, so cross-lingual prompts (ES vs EN desc)
# land lower. Empirically calibrated: good matches score 0.48-0.78, off-domain
# prompts (incl. meta/prompts about the harness itself) top out at ~0.36. The
# 0.40 floor cuts all observed noise while preserving every true-positive
# top-1 (verified on the live 115-skill catalog, 2026-07-12).
RECOMMEND_COSINE_FLOOR = 0.40
RECOMMEND_LEXICAL_FLOOR = 0.12  # Jaccard floor for the lexical fallback
RECOMMEND_DEFAULT_TOP_K = 3
RECOMMEND_MAX_TOP_K = 6



@dataclass(frozen=True)
class Recommendation:
    """One recommended skill with score + reason."""

    skill: str
    score: float
    reason: str
    mode: str  # "semantic" | "lexical"

from .index import (  # noqa: E402
    _index_dir,
    _index_paths,
    ensure_index,
)


def _cosine_topk(
    prompt_vec: list[float], matrix: object, names: list[str], top_k: int, floor: float
) -> list[tuple[str, float]]:
    """Return [(name, cosine)] above floor, sorted desc, capped at top_k."""
    try:
        import numpy as np  # type: ignore
    except Exception:
        return []
    pv = np.asarray(prompt_vec, dtype=np.float32)
    mat = np.asarray(matrix, dtype=np.float32)  # (N, dim); cast from opaque type
    # Cosine via row-wise L2 normalization (stable; avoids per-row Python loops).
    pn = pv / (np.linalg.norm(pv) + 1e-9)
    mn = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9)
    sims = mn @ pn  # (N,)
    order = np.argsort(-sims)
    out: list[tuple[str, float]] = []
    for idx in order[:top_k]:
        s = float(sims[idx])
        if s >= floor:
            out.append((names[int(idx)], s))
        else:
            break
    return out


def _tokens(text: str) -> set[str]:
    return {tok for tok in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", text.lower()) if len(tok) >= 3}


def _lexical_overlap(prompt_tokens: set[str], skill_tokens: set[str]) -> set[str]:
    matched = set()
    for p in prompt_tokens:
        stem = p[:4]
        if any(stem == s[:4] or p in s or s in p for s in skill_tokens):
            matched.add(p)
    return matched


def _lexical_rank(prompt: str, skills: list[Skill], top_k: int) -> list[tuple[str, float]]:
    """Token-overlap ranking (Jaccard). Used when embeddings are unavailable."""
    prompt_tokens = _tokens(prompt)
    if not prompt_tokens:
        return []
    scored: list[tuple[float, str]] = []
    for sk in skills:
        sk_tokens = _tokens(f"{sk.name} {sk.description}")
        if not sk_tokens:
            continue
        inter = _lexical_overlap(prompt_tokens, sk_tokens)
        if not inter:
            continue
        jaccard = len(inter) / len(prompt_tokens | sk_tokens)
        if jaccard > 0:
            scored.append((jaccard, sk.name))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [(name, score) for score, name in scored[:top_k]]


def _semantic_recommend(
    prompt: str, skills: list[Skill], top_k: int, floor: float, force_rebuild: bool
) -> list[Recommendation] | None:
    """Semantic path: Ollama embeddings + disk index. None = unavailable."""
    try:
        from ...shared.embed import embed, is_alive
    except Exception:
        return None
    if not is_alive():
        return None
    index = ensure_index(skills, force_rebuild=force_rebuild)
    if index is None:
        return None
    matrix, names = index
    prompt_vec = embed(prompt, timeout=DEPTH_EMBED_TIMEOUT)
    if prompt_vec is None:
        # The SessionStart warmup may still be loading embeddinggemma on the
        # first prompt of a session; one retry usually catches it before the
        # caller falls back to (weaker ES->EN) lexical ranking.
        prompt_vec = embed(prompt, timeout=DEPTH_EMBED_TIMEOUT)
    if prompt_vec is None:
        return None
    ranked = _cosine_topk(prompt_vec, matrix, names, top_k, floor)
    return [
        Recommendation(
            skill=name,
            score=round(score, 3),
            reason=f"semantic match cos={score:.2f}",
            mode="semantic",
        )
        for name, score in ranked
    ]


def recommend(
    prompt: str,
    skills: list[Skill] | None = None,
    top_k: int = RECOMMEND_DEFAULT_TOP_K,
    floor: float = RECOMMEND_COSINE_FLOOR,
    force_rebuild: bool = False,
    semantic: bool = True,
) -> list[Recommendation]:
    """Return up to ``top_k`` relevant skills for ``prompt``. Never raises.

    Tries semantic (Ollama embeddings + disk index) first; falls back to
    lexical token-overlap if Ollama/numpy are unavailable or the index build
    fails. ``skills`` defaults to the live catalog.
    """
    if skills is None:
        from ...shared.skill_io import catalog

        skills = catalog()
    if not skills or not prompt.strip():
        return []
    # Cap prompt length before embedding: a pasted log/stacktrace can be tens of
    # KB and would either blow past embeddinggemma's 8K context or time out the
    # 1.5s prompt budget. 2K chars (~500 tokens) is plenty for semantic matching.
    prompt = prompt[:2000]
    top_k = max(1, min(top_k, RECOMMEND_MAX_TOP_K))

    if semantic:
        semantic_recs = _semantic_recommend(prompt, skills, top_k, floor, force_rebuild)
        if semantic_recs:
            return semantic_recs

    # --- lexical fallback ---
    ranked = _lexical_rank(prompt, skills, top_k)
    return [
        Recommendation(
            skill=name,
            score=round(score, 3),
            reason=f"lexical match jaccard={score:.2f}",
            mode="lexical",
        )
        for name, score in ranked
        if score >= RECOMMEND_LEXICAL_FLOOR
    ]


def index_status() -> dict:
    """Report on-disk index health for the CLI/audit. Read-only."""
    npz_path, meta_path, dim_path = _index_paths()
    status: dict = {
        "index_dir": str(_index_dir()),
        "has_index": npz_path.exists(),
        "indexed_skills": 0,
        "dim": None,
        "meta_present": meta_path.exists(),
    }
    if npz_path.exists():
        try:
            import numpy as np  # type: ignore

            blob = np.load(npz_path, allow_pickle=False)
            status["indexed_skills"] = int(blob["matrix"].shape[0])
            status["dim"] = int(blob["matrix"].shape[1])
        except Exception:
            pass
    if dim_path.exists():
        try:
            status["dim"] = int(dim_path.read_text(encoding="utf-8").strip())
        except ValueError:
            pass
    return status


def recommendations_to_hints(
    recs: list[Recommendation],
    exclude: set[str] | None = None,
    skill_paths: dict[str, Path] | None = None,
) -> list[str]:
    """Render recommendations as compact routing hints for the hook envelope.

    ``exclude`` drops skills already surfaced by the regex routes (avoids
    double-hinting). Keeps the hint short — the model loads the skill body
    on demand; we only need to name it.
    """
    exclude = exclude or set()
    hints: list[str] = []
    for rec in recs:
        if rec.skill in exclude:
            continue
        fallback = ""
        if skill_paths and rec.skill in skill_paths:
            fallback = f" If unavailable in the catalog, read `{skill_paths[rec.skill]}`."
        hints.append(
            f"Relevant skill for this task: `{rec.skill}` ({rec.reason}). "
            f"Invoke it via the Skill tool if the task needs it.{fallback}"
        )
    return hints


def as_payload(recs: list[Recommendation]) -> list[dict]:
    """JSON-ready list of recommendation dicts (for --json CLI output)."""
    return [asdict(r) for r in recs]
