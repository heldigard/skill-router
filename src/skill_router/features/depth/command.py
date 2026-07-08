"""Depth selector: for a multi-level skill + prompt, recommend a load level.

Levels:
  - "summary"  — load SKILL.md (frontmatter + TOC only); body too broad, prompt is exploratory.
  - "section"  — load SKILL.md TOC + one specific sections/<slug>.md file.
  - "body"     — load full SKILL.md body (legacy monolith, or no section matched).

Strategy:
  1. If the skill is legacy (no sections/), level = body. Nothing to segment.
  2. If Ollama is down, degrade to summary (cheap; let the model pick a section
     by reading the TOC).
  3. Embed prompt + each section title; rank by cosine. If top score >= threshold,
     level = section with that slug. Else level = summary.

Returns a dict suitable for both CLI (`skill-router depth`) and hook injection.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ...shared.config import DEPTH_SECTION_THRESHOLD
from ...shared.embed import embed, is_alive
from ...shared.skill_io import Section, Skill


@dataclass
class DepthDecision:
    """One depth recommendation."""

    level: str  # "summary" | "section" | "body"
    skill: str  # skill name
    section: str = ""  # slug when level == "section"
    section_path: str = ""  # absolute path when level == "section"
    score: float = 0.0  # top cosine similarity (section mode)
    reason: str = ""  # one-line explanation
    doc_namespaces: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()

    def as_hint(self) -> str:
        """Render as a routing hint for the UserPromptSubmit envelope."""
        if self.level == "section":
            doc_hint = ""
            if self.doc_namespaces:
                doc_hint = (
                    f" For API details, prefer docs namespaces: "
                    f"{', '.join(self.doc_namespaces[:4])}."
                )
            return (
                f"Depth: skill `{self.skill}` is multi-level and your prompt matches "
                f"section `{self.section}` (cos={self.score:.2f}). Load the SKILL.md TOC, "
                f"then Read `~/.claude/skills/{self.skill}/sections/{self.section}.md` "
                f"directly instead of scanning the whole body."
                + doc_hint
            )
        if self.level == "summary":
            return (
                f"Depth: skill `{self.skill}` is multi-level but your prompt is broad. "
                f"Load the SKILL.md summary/TOC and pick a section explicitly — do not "
                f"load every section file."
            )
        return f"Depth: skill `{self.skill}` is a legacy monolith — load the full SKILL.md body."


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _rank_sections(prompt_vec: list[float], skill: Skill) -> list[tuple[float, str]]:
    """Return [(score, slug), ...] sorted desc. Empty if embeddings failed."""
    scored: list[tuple[float, str]] = []
    for sec in skill.sections:
        v = _section_vec(skill, sec)
        if v is None:
            continue
        scored.append((_cosine(prompt_vec, v), sec.slug))
    scored.sort(reverse=True)
    return scored


# Process-local cache of section title embeddings.
# Key: f"{skill_name}|{slug}|{title}" — collision-safe across skills.
# Section titles are static within a session, but the same multi-level skill
# gets consulted on every relevant prompt; without this, embeddinggemma is
# called N_sections times PER decide() call (~1s each).
_SECTION_VEC_CACHE: dict[str, list[float]] = {}


def _section_vec(skill: Skill, sec: Section) -> list[float] | None:
    """Embed (and cache) one section's compact search surrogate."""
    text = _section_search_text(sec)
    key = f"{skill.name}|{sec.slug}|{text}"
    cached = _SECTION_VEC_CACHE.get(key)
    if cached is not None:
        return cached
    v = embed(text)
    if v is not None:
        _SECTION_VEC_CACHE[key] = v
    return v


def _section_search_text(sec: Section) -> str:
    """Compact text used for section relevance embeddings."""
    parts = [sec.title, sec.slug]
    parts.extend(getattr(sec, "keywords", ()) or ())
    parts.extend(getattr(sec, "aliases", ()) or ())
    parts.extend(getattr(sec, "tools", ()) or ())
    parts.extend(getattr(sec, "doc_namespaces", ()) or ())
    return " ".join(str(part) for part in parts if part).strip()


def clear_section_cache() -> None:
    """Reset the section-embedding cache. Tests swap `embed` via monkeypatch."""
    _SECTION_VEC_CACHE.clear()


def decide(prompt: str, skill: Skill, threshold: float = DEPTH_SECTION_THRESHOLD) -> DepthDecision:
    """Pick a load level for `skill` given `prompt`. Never raises."""
    if skill.legacy:
        return DepthDecision(
            level="body", skill=skill.name, reason="legacy monolith; no sections/ to segment"
        )
    if not is_alive():
        return DepthDecision(
            level="summary", skill=skill.name, reason="ollama down; degrade to TOC + model picks"
        )
    prompt_vec = embed(prompt)
    if prompt_vec is None:
        return DepthDecision(
            level="summary", skill=skill.name, reason="prompt embed failed; degrade to TOC"
        )
    ranked = _rank_sections(prompt_vec, skill)
    if not ranked:
        return DepthDecision(
            level="summary",
            skill=skill.name,
            reason="section embeddings unavailable; degrade to TOC",
        )
    top_score, top_slug = ranked[0]
    if top_score < threshold:
        return DepthDecision(
            level="summary",
            skill=skill.name,
            score=top_score,
            reason=f"top cosine {top_score:.2f} < {threshold}; prompt too broad",
        )
    section_path = ""
    for sec in skill.sections:
        if sec.slug == top_slug:
            section_path = str(sec.path)
            doc_namespaces = tuple(getattr(sec, "doc_namespaces", ()) or ())
            tools = tuple(getattr(sec, "tools", ()) or ())
            break
    else:
        doc_namespaces = ()
        tools = ()
    return DepthDecision(
        level="section",
        skill=skill.name,
        section=top_slug,
        section_path=section_path,
        score=top_score,
        reason=f"top section match cos={top_score:.2f}",
        doc_namespaces=doc_namespaces,
        tools=tools,
    )


def decide_for_skills(prompt: str, skills: list[Skill]) -> list[DepthDecision]:
    """Run decide() over the skills the router is recommending. Multi-level only."""
    out: list[DepthDecision] = []
    for sk in skills:
        if sk.legacy:
            continue  # legacy skills load body whole; no hint needed
        out.append(decide(prompt, sk))
    return out
