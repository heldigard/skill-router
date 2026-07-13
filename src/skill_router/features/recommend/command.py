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

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from ...shared.config import AUDIT_EMBED_TIMEOUT, DEPTH_EMBED_TIMEOUT
from ...shared.paths import state_dir
from ...shared.skill_io import Skill

# Catalog build embeds ~115 skills once (cold model ~2s each); this is a
# one-shot batch op like audit, NOT the per-prompt hook path. Use the generous
# audit timeout so a cold embeddinggemma doesn't silently starve every embed
# and produce an empty index. The per-prompt path keeps DEPTH_EMBED_TIMEOUT.
BUILD_EMBED_TIMEOUT = AUDIT_EMBED_TIMEOUT

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

_INDEX_DIR_NAME = "skill-router"


@dataclass(frozen=True)
class Recommendation:
    """One recommended skill with score + reason."""

    skill: str
    score: float
    reason: str
    mode: str  # "semantic" | "lexical"


def _index_dir() -> Path:
    d = state_dir() / _INDEX_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _index_paths() -> tuple[Path, Path, Path]:
    base = _index_dir()
    return (
        base / "catalog.npz",  # matrix + names array
        base / "catalog.meta.json",  # {skill_name: mtime_ns}
        base / "catalog.dim",  # single int: embedding dim (sanity check)
    )


def _catalog_text(skill: Skill) -> str:
    """Compact surrogate embedded per skill: name + description only.

    The system-prompt catalog uses exactly these two fields, so ranking on
    them matches what the model would see (and lets us resuscitate dropped
    entries by the same name).
    """
    desc = (skill.description or "").strip()
    return f"{skill.name}: {desc}" if desc else skill.name


def _skill_mtime(skill: Skill) -> int:
    try:
        return skill.skill_md.stat().st_mtime_ns
    except (OSError, AttributeError):
        return 0


def _load_meta(path: Path) -> dict[str, int]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_meta(path: Path, meta: dict[str, int]) -> None:
    try:
        _atomic_write_text(path, json.dumps(meta, sort_keys=True))
    except OSError:
        pass


def _atomic_write_text(path: Path, text: str) -> None:
    """Write text atomically (.tmp + os.replace). Crash-safe across processes."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _atomic_save_npz(npz_path: Path, matrix, names) -> None:
    """Save npz atomically so a concurrent reader never sees a partial file.

    numpy's savez appends '.npz' if the name lacks it, so the temp name MUST end
    in '.npz' or os.replace below would target a non-existent file.
    """
    import numpy as np  # type: ignore

    tmp = npz_path.with_name(npz_path.stem + ".tmp.npz")
    np.savez_compressed(tmp, matrix=matrix, names=np.asarray(names))
    os.replace(tmp, npz_path)


def _load_disk_vectors(npz_path: Path) -> tuple[dict[str, list[float]], list[str]]:
    """Read the on-disk npz into {name: vector}. Empty on missing/corrupt.

    Safe against a concurrent atomic write: os.replace presents either the old
    complete file or the new one, never a partial.
    """
    try:
        import numpy as np  # type: ignore
    except Exception:
        return {}, []
    if not npz_path.exists():
        return {}, []
    try:
        blob = np.load(npz_path, allow_pickle=False)
        names = [str(n) for n in blob["names"]]
        vecs = {name: list(row) for name, row in zip(names, blob["matrix"], strict=False)}
        return vecs, names
    except (OSError, ValueError, KeyError):
        return {}, []


def _acquire_build_lock():
    """Non-blocking cross-process lock. Returns an open file handle or None.

    The SessionStart warmup (nohup background) and a UserPromptSubmit hook can
    both decide to build at once. The lock lets one build while the other reads
    the existing on-disk index instead of duplicating ~115 embeds. fcntl is
    POSIX-only; this host is Linux/WSL2.
    """
    try:
        import fcntl
    except ImportError:
        return None  # non-POSIX: no dedup, atomic write still prevents corruption
    lock_path = _index_dir() / "catalog.lock"
    try:
        lf = open(lock_path, "w")  # noqa: SIM115 — held open until released
    except OSError:
        return None
    try:
        fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lf
    except OSError:
        lf.close()
        return None


def _release_build_lock(lf) -> None:
    try:
        lf.close()
    except Exception:  # noqa: BLE001 — lock release must never raise
        pass


def _needs_rebuild(
    skills: list[Skill], metas: dict[str, int], existing: dict[str, list[float]]
) -> bool:
    """True if any skill is missing, stale (mtime changed), or extra in the index."""
    live = {sk.name: _skill_mtime(sk) for sk in skills}
    if set(live) != set(metas) or set(live) != set(existing):
        return True
    return any(metas.get(name) != mtime for name, mtime in live.items())


def _build_index(
    skills: list[Skill], existing: dict[str, list[float]], metas: dict[str, int]
) -> tuple[list[list[float]], list[str], dict[str, int]] | None:
    """Embed any skill missing or stale in the cache. Returns None if Ollama down.

    Reuses cached vectors whose mtime is unchanged (incremental update); embeds
    the rest. Late-imports numpy/embed so a missing dep degrades to None rather
    than raising.
    """
    try:
        import numpy as np  # type: ignore

        from ...shared.embed import embed, is_alive
    except Exception:
        return None

    if not is_alive():
        return None

    vectors: list[list[float]] = []
    names: list[str] = []
    new_metas: dict[str, int] = {}
    changed = False
    for sk in skills:
        mtime = _skill_mtime(sk)
        cached = existing.get(sk.name)
        if cached is not None and metas.get(sk.name) == mtime:
            vectors.append(cached)
        else:
            vec = embed(_catalog_text(sk), timeout=BUILD_EMBED_TIMEOUT)
            if vec is None:
                # Ollama bailed mid-rebuild: skip this skill but keep the rest.
                continue
            vectors.append(vec)
            changed = True
        names.append(sk.name)
        new_metas[sk.name] = mtime

    if not vectors:
        return None

    # Persist only when something actually changed (amortizes disk writes).
    # Atomic (.tmp + os.replace) so a concurrent reader never sees a partial npz.
    if changed or len(new_metas) != len(metas):
        npz_path, meta_path, dim_path = _index_paths()
        try:
            matrix = np.asarray(vectors, dtype=np.float32)
            _atomic_save_npz(npz_path, matrix, names)
            _save_meta(meta_path, new_metas)
            _atomic_write_text(dim_path, str(matrix.shape[1]))
        except OSError:
            pass
    return vectors, names, new_metas


def _disk_matrix_or_none(
    names: list[str], existing: dict[str, list[float]]
) -> tuple[object, list[str]] | None:
    """Materialize a matrix from already-loaded vectors, or None if empty."""
    try:
        import numpy as np  # type: ignore
    except Exception:
        return None
    if not existing or not names:
        return None
    matrix = np.asarray([existing[n] for n in names], dtype=np.float32)
    return matrix, list(names)


def ensure_index(
    skills: list[Skill], force_rebuild: bool = False
) -> tuple[object, list[str]] | None:
    """Load or build the on-disk semantic index. Returns (matrix, names) or None.

    ``matrix`` is a numpy (N, dim) float32 array; ``names`` aligns rows to skill
    names. Returns None when Ollama or numpy is unavailable (caller falls back
    to lexical ranking). On ``force_rebuild`` the mtime cache is ignored.

    Race-safe: the build runs under a cross-process lock so the SessionStart
    warmup and a concurrent UserPromptSubmit hook never duplicate the ~115 embeds.
    A reader that loses the lock reuses whatever index is on disk rather than
    racing a writer; atomic writes (.tmp + os.replace) guarantee it never sees a
    partial npz.
    """
    try:
        import numpy as np  # type: ignore
    except Exception:
        return None

    npz_path, meta_path, _ = _index_paths()
    metas = {} if force_rebuild else _load_meta(meta_path)
    existing, names = _load_disk_vectors(npz_path)

    # Fast path: index on disk is fresh — return it without embedding anything.
    if not force_rebuild and existing and not _needs_rebuild(skills, metas, existing):
        return _disk_matrix_or_none(names, existing)

    # Build under lock; if another process holds it, reuse the on-disk index.
    lock = _acquire_build_lock()
    if lock is None:
        return _disk_matrix_or_none(names, existing)
    try:
        built = _build_index(skills, existing, metas)
    finally:
        _release_build_lock(lock)
    if built is None:
        return _disk_matrix_or_none(names, existing)
    vectors, built_names, _ = built
    return np.asarray(vectors, dtype=np.float32), built_names


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
