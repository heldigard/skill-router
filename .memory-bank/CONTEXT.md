# CONTEXT - Current State
> Updated: 2026-07-19

## Active Focus
- skill-router healthy on native Ubuntu 26: gates green, budget fixed, catalog complete.

## Recent Changes (2026-07-19)
- Budget: vendored `~/.claude/skills-sources/*` classified as **managed** (symlink-aware); local over_cap 27→0.
- DESC_CAP/DESC_WARN aligned to Codex HARD_CAP **185**; structural uses strict `>185`.
- Ecosystem: compacted 27+ skills-sources descriptions ≤185; multilevel split for 6 oversized vendored skills.
- Pipeline: `grok` added to `_CONTROLLER_CALLERS` (Claude + Grok hook copies).
- Routes 70; coverage 170/170; oversized 0; pytest green.

## Blockers / Risks
- Codex still squeezes **all** listing descriptions (`effective≈27ch`) when 83 skills are loaded — catalog size, not description debt.
- skills-sources commits are **local vendored patches**; remotes point at upstream (chrisbanes/android) — do not push without a personal fork/PR.

## Next Steps
- Keep `catalog --oversized 300` at 0 when adding skills.
- New domain skills → declare full family on routes (not recommender-only).
- Optional: reduce Codex visible catalog / skillListingBudgetFraction if 27ch squeeze hurts selection.
