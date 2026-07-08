"""Catalog health gate. Four probes (migrated verbatim from skills-audit.py):

  structural — frontmatter validity, name==dir, orphans, description bounds.
  drift      — canonical skills missing from cross-CLI sync targets.
  discrim    — embedding pairwise overlap; flags near-duplicate descriptions.
  bench      — prompt -> skill embed-rank hit@1/hit@3 (lower bound on router).

Pure stdlib for structural/drift; ollama via shared.embed for discrim/bench.
"""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path
from typing import Any, NamedTuple

from ...shared.config import DESC_CAP, DESC_WARN_VERBOSE
from ...shared.embed import embed, is_alive
from ...shared.paths import SYNC_TARGETS, skills_root
from ...shared.skill_io import catalog, parse_frontmatter


class SkillFrontmatter(NamedTuple):
    """Parsed skill frontmatter plus read-state for audit probes."""

    text: str
    name: str
    description: str
    block: str


def canonical_skill_dirs() -> list[Path]:
    """Valid skill directories in the canonical catalog."""
    root = skills_root()
    if not root.is_dir():
        return []
    return sorted(d for d in root.iterdir() if d.is_dir() and not d.name.startswith("."))


def _read_frontmatter(skill_dir: Path) -> SkillFrontmatter:
    sf = skill_dir / "SKILL.md"
    if not sf.exists():
        return SkillFrontmatter("", "", "", "")
    try:
        text = sf.read_text(errors="ignore")
    except OSError:
        return SkillFrontmatter("", "", "", "")
    name, desc, block = parse_frontmatter(text)
    return SkillFrontmatter(text, name, desc, block)


def _desc(skill_dir: Path) -> str:
    return _read_frontmatter(skill_dir).description


def _dominant_dimension_vectors(
    names: list[str],
    vectors: list[list[float]],
) -> tuple[list[str], list[list[float]]]:
    """Keep vectors that share the most common non-zero dimension.

    Ollama model swaps or partial failures can occasionally produce mixed vector
    dimensions in one process. Audit probes are advisory, so dropping the odd
    vector is better than crashing the whole health check.
    """
    dims = Counter(len(v) for v in vectors if v)
    if not dims:
        return [], []
    target_dim = dims.most_common(1)[0][0]
    kept_names: list[str] = []
    kept_vectors: list[list[float]] = []
    for name, vector in zip(names, vectors, strict=False):
        if len(vector) == target_dim:
            kept_names.append(name)
            kept_vectors.append(vector)
    return kept_names, kept_vectors


# ---------------------------------------------------------------- structural
def structural() -> dict:
    """Return {missing_fm, missing_desc, missing_name, name_mismatch, orphans, verbose}."""
    out: dict[str, list[Any]] = {
        "missing_fm": [],
        "missing_desc": [],
        "missing_name": [],
        "name_mismatch": [],
        "orphans": [],
        "verbose": [],
    }
    for d in canonical_skill_dirs():
        sf = d / "SKILL.md"
        if not sf.exists():
            out["orphans"].append(d.name)
            continue
        frontmatter = _read_frontmatter(d)
        if not frontmatter.block:
            out["missing_fm"].append(d.name)
            continue
        name = frontmatter.name
        desc = frontmatter.description
        if not name:
            out["missing_name"].append(d.name)
        elif name != d.name:
            out["name_mismatch"].append((d.name, name))
        if not desc:
            out["missing_desc"].append(d.name)
        elif len(desc) >= DESC_WARN_VERBOSE and not desc.upper().startswith("DEPRECATED"):
            out["verbose"].append((d.name, len(desc)))
    return out


# ---------------------------------------------------------------- drift
def drift() -> dict:
    """Per-target: canonical skills missing from the target's UNION of dirs."""
    canonical = {d.name for d in canonical_skill_dirs()}
    out: dict[str, dict] = {}
    for label, dirs in SYNC_TARGETS.items():
        present: set[str] = set()
        any_exists = False
        for tp in dirs:
            p = Path(os.path.expanduser(tp))
            if not p.exists():
                continue
            any_exists = True
            present |= {d.name for d in p.iterdir() if d.is_dir() and not d.name.startswith(".")}
        if not any_exists:
            out[label] = {"missing": [], "absent_target": True}
            continue
        out[label] = {"missing": sorted(canonical - present), "count": len(present)}
    return out


# ---------------------------------------------------------------- discrim
def discrim(top_pairs: int = 15, threshold: float = 0.80) -> dict | None:
    """Embedding pairwise overlap. Returns {pairs, near_dups} or None if ollama down."""
    if not is_alive():
        return None
    try:
        import numpy as np  # local import; not needed for structural/drift
    except ImportError:
        return None
    descs = {d.name: _desc(d) for d in canonical_skill_dirs()}
    descs = {n: t for n, t in descs.items() if t}
    names = list(descs)
    if not names:
        return {"pairs": [], "near_dups": []}
    names, vecs = _dominant_dimension_vectors(names, [embed(descs[n]) or [] for n in names])
    if not vecs:
        return {"pairs": [], "near_dups": []}
    V = np.array(vecs, dtype=float)
    if V.size == 0:
        return {"pairs": [], "near_dups": []}
    norms = np.linalg.norm(V, axis=1, keepdims=True) + 1e-9
    V = V / norms
    S = V @ V.T
    np.fill_diagonal(S, -1)
    pairs = []
    seen: set[tuple[str, str]] = set()
    for i, a in enumerate(names):
        j = int(S[i].argmax())
        b = names[j]
        lo, hi = (a, b) if a <= b else (b, a)
        key = (lo, hi)
        if key in seen:
            continue
        seen.add(key)
        pairs.append((float(S[i][j]), a, b))
    pairs.sort(reverse=True)
    near = [(sc, a, b) for sc, a, b in pairs[:top_pairs] if sc >= threshold]
    return {"pairs": pairs[:top_pairs], "near_dups": near}


# ---------------------------------------------------------------- bench
def bench(fixtures: list[tuple[str, str]] | None = None) -> dict | None:
    """prompt -> skill hit@1/hit@3 lower bound on the embedding router.

    Fixtures: list of (prompt, expected_skill_name). Default: a tiny built-in set.
    Returns {hit1, hit3, n, details} or None if ollama down.
    """
    if not is_alive():
        return None
    try:
        import numpy as np
    except ImportError:
        return None
    if fixtures is None:
        fixtures = _default_fixtures()
    skills = catalog()
    if not skills:
        return None
    names = [sk.name for sk in skills]
    descs = [sk.description for sk in skills]
    names, vecs = _dominant_dimension_vectors(names, [embed(d) or [] for d in descs])
    if not vecs:
        return None
    M = np.array(vecs, dtype=float)
    if M.size == 0:
        return None
    M /= np.linalg.norm(M, axis=1, keepdims=True) + 1e-9
    hit1 = hit3 = 0
    details = []
    for prompt, expected in fixtures:
        pv_raw = embed(prompt)
        if pv_raw is None:
            continue
        if len(pv_raw) != M.shape[1]:
            continue
        pv = np.array(pv_raw, dtype=float)
        pv = pv / (np.linalg.norm(pv) + 1e-9)
        sims = M @ pv
        order = sorted(zip(sims.tolist(), names, strict=False), reverse=True)
        top = [n for _, n in order[:3]]
        details.append({"prompt": prompt[:60], "expected": expected, "top3": top})
        if top and top[0] == expected:
            hit1 += 1
        if expected in top:
            hit3 += 1
    n = len(fixtures)
    return {"hit1": hit1, "hit3": hit3, "n": n, "details": details}


def _default_fixtures() -> list[tuple[str, str]]:
    return [
        ("how to write a Spring Boot REST controller", "spring-boot-engineer"),
        ("Angular standalone component with signals", "angular"),
        ("FastAPI async endpoint with SQLAlchemy", "python-backend"),
        ("JPA LazyInitializationException fix", "jpa-patterns"),
        ("GitHub PR review via gh CLI", "github-cli"),
    ]


# ---------------------------------------------------------------- gate
def check() -> int:
    """CI gate. 0 = pass, 1 = fail. discrim/bench are advisory (never fail)."""
    errors: list[str] = []
    s = structural()
    for k in ("missing_fm", "missing_desc", "missing_name", "orphans"):
        if s[k]:
            errors.append(f"structural.{k}: {s[k]}")
    if s["name_mismatch"]:
        errors.append(f"structural.name_mismatch: {s['name_mismatch']}")
    d = drift()
    for label, info in d.items():
        if info.get("absent_target"):
            continue
        miss = info.get("missing", [])
        if miss:
            errors.append(f"drift.{label}: missing {len(miss)} -> {miss[:6]}")
    if errors:
        return 1
    return 0


# Description cap exports (for CLI rendering)
__all__ = [
    "structural",
    "drift",
    "discrim",
    "bench",
    "check",
    "canonical_skill_dirs",
    "DESC_CAP",
    "DESC_WARN_VERBOSE",
]
