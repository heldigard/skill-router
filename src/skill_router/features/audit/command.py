"""Catalog health gate. Five probes (four migrated verbatim from skills-audit.py):

  structural — frontmatter validity, name==dir, orphans, description bounds.
  drift      — canonical skills missing from cross-CLI sync targets.
  coverage   — route table vs catalog: hint/skills= drift, ghost skills, unrouted.
  discrim    — embedding pairwise overlap; flags near-duplicate descriptions.
  bench      — prompt -> skill embed-rank hit@1/hit@3 (lower bound on router).

Pure stdlib for structural/drift/coverage; ollama via shared.embed for
discrim/bench. Coverage takes the route table by injection (RouteLike) so this
slice never imports the routing feature — the CLI is the composition root.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NamedTuple, Protocol

from ...shared.config import (
    AUDIT_EMBED_TIMEOUT,
    DESC_CAP,
    DESC_WARN_VERBOSE,
    PLUGIN_SKILL_ALLOWLIST,
)
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
    """Valid skill directories in the canonical catalog.

    Skips hidden dirs and underscore-prefixed reserves (e.g. ``_archive``),
    which hold retired skills and must not gate drift/structural audits.
    """
    root = skills_root()
    if not root.is_dir():
        return []
    return sorted(
        d
        for d in root.iterdir()
        if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("_")
    )


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


def _embedding_ready() -> bool:
    """True when an embedding call succeeds quickly enough for audit probes."""
    return embed("skill-router audit probe", timeout=AUDIT_EMBED_TIMEOUT) is not None


def _embed_for_audit(text: str) -> list[float] | None:
    return embed(text, timeout=AUDIT_EMBED_TIMEOUT)


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


# ---------------------------------------------------------------- coverage
class RouteLike(Protocol):
    """Duck type for injected routes; keeps this slice decoupled from routing.

    Read-only properties so frozen dataclasses (the real Route) conform.
    """

    @property
    def hint(self) -> str: ...

    @property
    def skills(self) -> tuple[str, ...]: ...

    @property
    def patterns(self) -> tuple[str, ...]: ...


# Backtick-quoted names in hints; same shape as skill dir names (kebab-case).
_HINT_SKILL_RE = re.compile(r"`([a-z0-9][a-z0-9_-]+)`")


def coverage(routes: Sequence[RouteLike]) -> dict:
    """Route table vs catalog cross-check.

    Returns:
      hint_drift   — per route: catalog skills the hint recommends (backticks)
                     but skills= does not declare. Routes must declare metadata
                     explicitly; consumers never parse hint prose.
      ghost_skills — per route: declared skills absent from the catalog and not
                     in PLUGIN_SKILL_ALLOWLIST (typo or removed skill).
      unrouted     — catalog skills no route declares (informational; leaves
                     like search engines are intentionally reachable only via
                     their router skill).
    """
    cat_names = {sk.name for sk in catalog()}
    hint_drift: list[dict[str, Any]] = []
    ghost_skills: list[dict[str, Any]] = []
    declared: set[str] = set()
    for idx, route in enumerate(routes):
        route_skills = set(route.skills)
        declared |= route_skills
        mentioned = {m for m in _HINT_SKILL_RE.findall(route.hint) if m in cat_names}
        undeclared = sorted(mentioned - route_skills)
        if undeclared:
            hint_drift.append({"index": idx, "undeclared": undeclared, "hint": route.hint[:80]})
        ghosts = sorted(route_skills - cat_names - PLUGIN_SKILL_ALLOWLIST)
        if ghosts:
            ghost_skills.append({"index": idx, "skills": ghosts})
    return {
        "hint_drift": hint_drift,
        "ghost_skills": ghost_skills,
        "unrouted": sorted(cat_names - declared),
        "catalog_count": len(cat_names),
        "routed_count": len(declared & cat_names),
    }


# ---------------------------------------------------------------- discrim
def discrim(top_pairs: int = 15, threshold: float = 0.80) -> dict | None:
    """Embedding pairwise overlap. Returns {pairs, near_dups} or None if ollama down."""
    if not is_alive():
        return None
    try:
        import numpy as np  # local import; not needed for structural/drift
    except ImportError:
        return None
    if not _embedding_ready():
        return None
    descs = {d.name: _desc(d) for d in canonical_skill_dirs()}
    descs = {n: t for n, t in descs.items() if t}
    names = list(descs)
    if not names:
        return {"pairs": [], "near_dups": []}
    names, vecs = _dominant_dimension_vectors(
        names, [_embed_for_audit(descs[n]) or [] for n in names]
    )
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
    if not _embedding_ready():
        return None
    if fixtures is None:
        fixtures = _default_fixtures()
    skills = catalog()
    if not skills:
        return None
    names = [sk.name for sk in skills]
    descs = [sk.description for sk in skills]
    names, vecs = _dominant_dimension_vectors(names, [_embed_for_audit(d) or [] for d in descs])
    if not vecs:
        return None
    M = np.array(vecs, dtype=float)
    if M.size == 0:
        return None
    M /= np.linalg.norm(M, axis=1, keepdims=True) + 1e-9
    hit1 = hit3 = 0
    details = []
    for prompt, expected in fixtures:
        pv_raw = _embed_for_audit(prompt)
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


# ---------------------------------------------------------------- overlap
# Synthetic corpus for the overlap probe. Each string is a representative of
# a domain that *some* route matches. The probe does NOT need Ollama.
_OVERLAP_CORPUS: tuple[str, ...] = (
    "how do I write an Angular standalone component with signals",
    "build a FastAPI async endpoint with SQLAlchemy",
    "Spring Boot REST controller pattern",
    "configure n8n workflow via REST API",
    "implement OAuth2 JWT auth in Node",
    "PostgreSQL slow query EXPLAIN ANALYZE",
    "review this PR before merge",
    "run security scan before commit",
    "find references to function foo",
    "split this monolith into vertical slices",
    "k8s cluster failing to start",
    "Azure Functions Python v2 deployment",
    "React 19 server component data fetch",
    "Vue 3 composable state pattern",
    "Spring Boot JPA N+1 lazy loading fix",
    "JUnit 5 test with Mockito",
    "git checkout branch from origin",
    "GitHub PR review via gh CLI",
    "agent-browser a11y snapshot",
    "subagent fan out across 3 files",
    "improvement loop until budget exhausted",
    "improvement loop until count reached",
    "agentic cycle route prompt",
    "delegate to cworker bounded task",
    "swarm run multiple models for consensus",
    "deep research multi-source synthesis",
    "codex skill catalog audit budget",
    "AGENTS.md prompt routing",
    "Codex worker profile schema",
    "Codex openai-agents MCP setup",
)


def overlap(routes: Sequence[RouteLike]) -> dict:
    """Pairwise regex-overlap report.

    For every route pair, compute the Jaccard similarity of synthetic-prompt
    match counts. Pairs with Jaccard >= threshold and identical first hit
    indicate redundancy: the lower-priority route is a candidate to merge.

    Pure stdlib (no Ollama, no embedding service). Returns the top-N pairs
    regardless of threshold so the CLI / CI gate can decide.

    Note: this probe measures pattern equivalence, NOT semantic equivalence.
    Two routes with distinct regex but identical hint prose still trigger
    hint dedup (see command._assemble_hints). This probe is the complementary
    signal: redundant PATTERNS that should be merged into one route.
    """
    corpus = _OVERLAP_CORPUS
    # matched_sets[i] corresponds to routes[i]; empty set for routes whose
    # patterns failed to compile so index alignment is preserved.
    matched_sets: list[set[int]] = []
    for r in routes:
        try:
            pats = tuple(re.compile(p, re.IGNORECASE) for p in r.patterns)
        except re.error:
            matched_sets.append(set())
            continue
        hit_idx = {idx for idx, text in enumerate(corpus) if any(p.search(text) for p in pats)}
        matched_sets.append(hit_idx)

    pairs: list[tuple[float, int, int]] = []
    n = len(routes)
    for i in range(n):
        for j in range(i + 1, n):
            a = matched_sets[i]
            b = matched_sets[j]
            if not a and not b:
                continue
            union = a | b
            jacc = len(a & b) / len(union) if union else 0.0
            if jacc <= 0.0:
                continue
            pairs.append((round(jacc, 3), i, j))
    pairs.sort(reverse=True)
    top = [
        {"jaccard": j, "a": i, "b": k, "a_hint": routes[i].hint[:60], "b_hint": routes[k].hint[:60]}
        for j, i, k in pairs[:20]
    ]
    return {"top": top, "corpus_size": len(corpus), "route_count": n}


# ---------------------------------------------------------------- gate
def check(routes: Sequence[RouteLike] | None = None) -> int:
    """CI gate. 0 = pass, 1 = fail. discrim/bench/overlap are advisory (never fail).

    When `routes` is injected (the CLI passes the live route table), coverage
    hint_drift and ghost_skills also gate; unrouted stays informational.
    """
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
    if routes is not None:
        cov = coverage(routes)
        if cov["hint_drift"]:
            errors.append(f"coverage.hint_drift: {cov['hint_drift']}")
        if cov["ghost_skills"]:
            errors.append(f"coverage.ghost_skills: {cov['ghost_skills']}")
    if errors:
        return 1
    return 0


# Description cap exports (for CLI rendering)
__all__ = [
    "structural",
    "drift",
    "coverage",
    "overlap",
    "discrim",
    "bench",
    "check",
    "canonical_skill_dirs",
    "RouteLike",
    "DESC_CAP",
    "DESC_WARN_VERBOSE",
]
