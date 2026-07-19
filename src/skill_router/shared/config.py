"""Configuration constants for skill-router.

Largely ported from the monolithic routing hook + skills-audit.py + intent_route.py.
Kept here as data, not logic, so features import constants without circular deps.
"""

from __future__ import annotations

import os

# ---- skill-router guards --------------------------------------------------
# Presence of any of these (in prompt or env) skips routing entirely.
SKIP_PROMPT_MARKERS: tuple[str, ...] = ("[NO_DELEGATE]", "[CODEX_WORKER]", "[NO_SWARM]")
SKIP_ENV_VARS: tuple[str, ...] = ("NO_DELEGATE", "CODEX_WORKER", "SWARM_WORKER")

# Maximum hints injected per UserPromptSubmit (preserve signal, avoid noise).
MAX_HINTS: int = 5
# Codex's dynamic per-entry listing squeezes descriptions once the catalog
# overflows. Trimming hint count on Codex frees budget for hidden-skill rescue
# hints without losing the highest-signal route.
MAX_HINTS_CODEX: int = 4


def max_hints() -> int:
    """Per-CLI hint budget.

    Claude default = 5; Codex default = 4 (catalog squeeze overhead). Override
    both via SKILL_ROUTER_MAX_HINTS / SKILL_ROUTER_MAX_HINTS_CODEX.
    """
    if os.environ.get("CLI_ORCHESTRATION_CALLER", "").lower() == "codex":
        return _positive_int("SKILL_ROUTER_MAX_HINTS_CODEX", MAX_HINTS_CODEX)
    return _positive_int("SKILL_ROUTER_MAX_HINTS", MAX_HINTS)


def _positive_int(env_key: str, default: int) -> int:
    raw = os.environ.get(env_key)
    if not raw:
        return default
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


# ---- intent_route classifier -----------------------------------------------
CATEGORIES: list[str] = [
    "trivial",
    "lookup",
    "code-edit",
    "refactor",
    "feature",
    "debug",
    "architecture",
    "security",
    "meta",
]

# Tier = the model tier that should DO the substantive work. The cheap cascade
# only PREPROCESSES (classify / extract / draft-msg / review-notes /
# error-triage) — it never WRITES code. Code-producing + reasoning tasks go to
# T3 (controller tier: Claude Opus, Codex gpt-5.x, the codex-coder / swarm-coding
# bridges with kimi-k2 / deepseek-v4).
CATEGORY_TIER: dict[str, str] = {
    "trivial": "T0",  # grep/docs, no LLM
    "lookup": "T0",  # grep/docs, no LLM
    "meta": "T1",  # tooling/config; local fine
    "code-edit": "T3",  # writes/edits code -> coding-capable model
    "refactor": "T3",  # multi-file restructure -> coding-capable
    "feature": "T3",  # new code -> coding-capable
    "debug": "T3",  # investigation/reasoning -> controller
    "architecture": "T3",  # design decision -> controller
    "security": "T3",  # security -> controller
}

INTENT_SYSTEM_PROMPT = (
    "You classify a developer's natural-language prompt into exactly one category. "
    "Categories: " + ", ".join(CATEGORIES) + ".\n"
    'Reply with JSON only: {"category": "<one>", "confidence": 0..1, '
    '"reason": "<one short sentence>", "cheaper_alternative": "<what could answer '
    'this without the big model, or empty if none>"}.'
)

INTENT_LOG_DIR_NAME = "intent-route"  # ~/.claude/state/intent-route/
INTENT_TIMEOUT_DEFAULT = 12.0

# ---- skills-audit ----------------------------------------------------------
# Route-declared plugin skills that intentionally have no canonical catalog
# entry. Keep empty unless every supported caller can actually resolve a name;
# marketplace source trees alone do not make a skill installed.
PLUGIN_SKILL_ALLOWLIST: frozenset[str] = frozenset()
# Align structural "verbose" with Codex's model-visible description hard rule
# (features/budget.HARD_CAP=185). Longer descriptions lose trigger words in
# Codex listings; report them as advisory verbose in `audit structural`.
DESC_CAP = 185
DESC_WARN_VERBOSE = 185
# Full catalog audits are explicit, on-demand diagnostics.  Give a cold embedding
# model enough time to load; prompt-time depth routing keeps its separate 1.5 s cap.
AUDIT_EMBED_TIMEOUT = 12.0

# ---- depth selector --------------------------------------------------------
# Embedding cosine threshold above which a section is deemed relevant to a prompt.
DEPTH_SECTION_THRESHOLD = 0.60
# Depth runs inside the prompt hook/route command, so it must degrade quickly
# when Ollama is cold or busy. Full audit/bench probes keep the default timeout.
DEPTH_EMBED_TIMEOUT = 1.5
# Maximum multi-level skills to depth-evaluate per prompt. Routing hints remain
# intact; this only bounds advisory section selection latency on cold caches.
MAX_DEPTH_SKILLS = 2
