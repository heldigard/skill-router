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
import re
from dataclasses import dataclass

from ...shared.config import DEPTH_EMBED_TIMEOUT, DEPTH_SECTION_THRESHOLD, MAX_DEPTH_SKILLS
from ...shared.embed import embed, is_alive
from ...shared.skill_io import Section, Skill

# Deterministic lexical-fallback thresholds (pure token-overlap Jaccard; no
# embeddings). Below these scores a lexical match is too weak to pin a section.
LEX_FALLBACK_THRESHOLD = 0.05  # used whenever cosine embeddings are unavailable
LEX_OVERRIDE_THRESHOLD = 0.20  # a strong lexical match overrides a low cosine score

# Hint message templates. Kept module-level (flat indent) so DepthDecision.as_hint
# stays within the nesting budget; placeholders are filled via str.format at render.
_BODY_HINT = "Depth: `{skill}` is monolithic; load its SKILL.md body."
_SUMMARY_HINT = (
    "Depth: `{skill}` is multi-level; read its SKILL.md TOC and select one section."
)
_SECTION_HINT = (
    "Depth: `{skill}` -> `{path}` (score={score:.2f}); "
    "read the SKILL.md TOC plus this section only."
)


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
        if self.level == "body":
            return _BODY_HINT.format(skill=self.skill)
        if self.level == "summary":
            return _SUMMARY_HINT.format(skill=self.skill)
        # level == "section"
        doc_hint = ""
        if self.doc_namespaces:
            joined = ", ".join(self.doc_namespaces[:4])
            doc_hint = f" Docs: {joined}."
        section_path = self.section_path or (
            f"~/.claude/skills/{self.skill}/sections/{self.section}.md"
        )
        return (
            _SECTION_HINT.format(
                skill=self.skill,
                path=section_path,
                score=self.score,
            )
            + doc_hint
        )


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _tokens(text: str) -> set[str]:
    """Cheap lexical tokens for prefiltering section candidates."""
    return {tok for tok in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", text.lower()) if len(tok) >= 4}


def _lexical_overlap(prompt_tokens: set[str], sec_tokens: set[str]) -> set[str]:
    """Return prompt tokens that match section tokens via stem/prefix or substring.

    A prompt token matches if it shares a 4-char stem with a section token, or if
    one is a substring of the other (covers optimize↔optimization, queries↔query).
    """
    matched = set()
    for p in prompt_tokens:
        p_stem = p[:4]
        if any(p_stem == s[:4] or p in s or s in p for s in sec_tokens):
            matched.add(p)
    return matched


def _candidate_sections(prompt: str, skill: Skill) -> list[Section]:
    """Return sections with at least one lexical overlap with the prompt."""
    prompt_tokens = _tokens(prompt)
    if not prompt_tokens:
        return []
    out = []
    for sec in skill.sections:
        sec_tokens = _tokens(_section_search_text(sec))
        if _lexical_overlap(prompt_tokens, sec_tokens):
            out.append(sec)
    return out


def _rank_sections(
    prompt_vec: list[float], skill: Skill, sections: list[Section]
) -> list[tuple[float, str]]:
    """Return [(score, slug), ...] sorted desc. Empty if embeddings failed."""
    scored: list[tuple[float, str]] = []
    for sec in sections:
        v = _section_vec(skill, sec)
        if v is None:
            continue
        scored.append((_cosine(prompt_vec, v), sec.slug))
    # Deterministic on score ties: highest score first, then slug ascending
    # (plain reverse=True would order tied slugs Z->A).
    scored.sort(key=lambda t: (-t[0], t[1]))
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
    v = embed(text, timeout=DEPTH_EMBED_TIMEOUT)
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


def _lexical_match(prompt: str, candidates: list[Section]) -> tuple[float, str] | None:
    """Best section match by pure token overlap. Returns (jaccard, slug) or None.

    Sections rank by a composite of intersect-size + Jaccard (size dominates,
    Jaccard tie-breaks), but the returned score is the Jaccard itself, since the
    thresholds in decide() are calibrated against it.
    """
    prompt_tokens = _tokens(prompt)
    if not prompt_tokens or not candidates:
        return None
    best_slug = ""
    best_jaccard = -1.0
    best_composite = -1.0
    for sec in candidates:
        sec_tokens = _tokens(_section_search_text(sec))
        if not sec_tokens:
            continue
        intersect = _lexical_overlap(prompt_tokens, sec_tokens)
        if not intersect:
            continue
        jaccard = len(intersect) / len(prompt_tokens | sec_tokens)
        composite = len(intersect) + jaccard
        if composite > best_composite:
            best_composite = composite
            best_jaccard = jaccard
            best_slug = sec.slug
    if not best_slug:
        return None
    return best_jaccard, best_slug


def _try_lexical_section(
    prompt: str,
    skill: Skill,
    sections: list[Section],
    threshold: float,
    reason_template: str,
) -> DepthDecision | None:
    """Return a section decision if a lexical match clears `threshold`, else None.

    Encapsulates the deterministic fallback used whenever cosine embeddings are
    unavailable (Ollama down, prompt/section embed failed). `reason_template` may
    use ``{jaccard:.2f}``; unused kwargs are ignored by str.format. The caller
    owns the summary fallback with its own reason.
    """
    lex = _lexical_match(prompt, sections)
    if lex and lex[0] >= threshold:
        score, slug = lex
        return _build_decision(skill, slug, score, reason_template.format(jaccard=score))
    return None


def _build_decision(skill: Skill, slug: str, score: float, reason: str) -> DepthDecision:
    """Helper to build a Section DepthDecision."""
    section_path = ""
    doc_namespaces = ()
    tools = ()
    for sec in skill.sections:
        if sec.slug == slug:
            section_path = str(sec.path)
            doc_namespaces = tuple(getattr(sec, "doc_namespaces", ()) or ())
            tools = tuple(getattr(sec, "tools", ()) or ())
            break
    return DepthDecision(
        level="section",
        skill=skill.name,
        section=slug,
        section_path=section_path,
        score=score,
        reason=reason,
        doc_namespaces=doc_namespaces,
        tools=tools,
    )


def decide(
    prompt: str,
    skill: Skill,
    threshold: float = DEPTH_SECTION_THRESHOLD,
    lexical_only: bool = False,
) -> DepthDecision:
    """Pick a load level for `skill` given `prompt`. Never raises."""
    if skill.legacy:
        return DepthDecision(
            level="body", skill=skill.name, reason="legacy monolith; no sections/ to segment"
        )

    candidates = _candidate_sections(prompt, skill)

    if lexical_only:
        return _try_lexical_section(
            prompt,
            skill,
            skill.sections,
            LEX_FALLBACK_THRESHOLD,
            "lexical match (Jaccard={jaccard:.2f})",
        ) or DepthDecision(
            level="summary",
            skill=skill.name,
            reason="no strong lexical section match; load TOC",
        )

    if not is_alive():
        return _try_lexical_section(
            prompt,
            skill,
            skill.sections,
            LEX_FALLBACK_THRESHOLD,
            "lexical match fallback (Jaccard={jaccard:.2f})",
        ) or DepthDecision(
            level="summary",
            skill=skill.name,
            reason="ollama down; degrade to TOC + model picks",
        )

    if not candidates:
        return DepthDecision(
            level="summary",
            skill=skill.name,
            reason="no lexical section match; load TOC and pick explicitly",
        )

    prompt_vec = embed(prompt, timeout=DEPTH_EMBED_TIMEOUT)
    if prompt_vec is None:
        return _try_lexical_section(
            prompt,
            skill,
            candidates,
            LEX_FALLBACK_THRESHOLD,
            "lexical match fallback (embed failed)",
        ) or DepthDecision(
            level="summary",
            skill=skill.name,
            reason="prompt embed failed; degrade to TOC",
        )

    ranked = _rank_sections(prompt_vec, skill, candidates)
    if not ranked:
        return _try_lexical_section(
            prompt,
            skill,
            candidates,
            LEX_FALLBACK_THRESHOLD,
            "lexical match fallback (sections embed failed)",
        ) or DepthDecision(
            level="summary",
            skill=skill.name,
            reason="section embeddings unavailable; degrade to TOC",
        )

    top_score, top_slug = ranked[0]
    if top_score < threshold:
        # A strong lexical match overrides a low cosine score.
        lex = _lexical_match(prompt, candidates)
        if lex and lex[0] >= LEX_OVERRIDE_THRESHOLD:
            score, slug = lex
            reason = f"lexical override (Jaccard={score:.2f}, cos={top_score:.2f})"
            return _build_decision(skill, slug, score, reason)
        return DepthDecision(
            level="summary",
            skill=skill.name,
            score=top_score,
            reason=f"top cosine {top_score:.2f} < {threshold}; prompt too broad",
        )

    return _build_decision(skill, top_slug, top_score, f"top section match cos={top_score:.2f}")


def decide_for_skills(
    prompt: str,
    skills: list[Skill],
    lexical_only: bool = False,
) -> list[DepthDecision]:
    """Run decide() over the skills the router is recommending. Multi-level only."""
    out: list[DepthDecision] = []
    for sk in skills:
        if sk.legacy:
            continue  # legacy skills load body whole; no hint needed
        out.append(decide(prompt, sk, lexical_only=lexical_only))
        if len(out) >= MAX_DEPTH_SKILLS:
            break
    return out
