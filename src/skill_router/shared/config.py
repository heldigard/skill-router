"""Configuration constants for skill-router.

Largely ported from the monolithic routing hook + skills-audit.py + intent_route.py.
Kept here as data, not logic, so features import constants without circular deps.
"""

from __future__ import annotations

# ---- skill-router guards --------------------------------------------------
# Presence of any of these (in prompt or env) skips routing entirely.
SKIP_PROMPT_MARKERS: tuple[str, ...] = ("[NO_DELEGATE]", "[CODEX_WORKER]", "[NO_SWARM]")
SKIP_ENV_VARS: tuple[str, ...] = ("NO_DELEGATE", "CODEX_WORKER", "SWARM_WORKER")

# Maximum hints injected per UserPromptSubmit (preserve signal, avoid noise).
MAX_HINTS: int = 5

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
DESC_CAP = 300  # frontmatter description soft cap (chars)
DESC_WARN_VERBOSE = 290  # at-cap => likely verbose; report (advisory)
AUDIT_EMBED_TIMEOUT = 1.5  # skip advisory embed probes when Ollama is cold/busy

# ---- depth selector --------------------------------------------------------
# Embedding cosine threshold above which a section is deemed relevant to a prompt.
DEPTH_SECTION_THRESHOLD = 0.60
# Depth runs inside the prompt hook/route command, so it must degrade quickly
# when Ollama is cold or busy. Full audit/bench probes keep the default timeout.
DEPTH_EMBED_TIMEOUT = 1.5
# Maximum multi-level skills to depth-evaluate per prompt. Routing hints remain
# intact; this only bounds advisory section selection latency on cold caches.
MAX_DEPTH_SKILLS = 2
