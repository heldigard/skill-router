# Skill catalog health
> Updated: 2026-07-18

## Snapshot after autonomous catalog pass

- Routes: 67 (was 63). Added agent-evals, docker-compose, azure-bicep, ms-graph.
- Coverage: 134/134 catalog skills, hint_drift=0, ghost=0, unrouted=0.
- Budget: over_cap local=0 (managed plugin over_cap only).
- Oversized body >300L: 0.
- Multilevel: ~81 skills with sections/ (was ~30).
- Descriptions: all local ≤185 chars.
- Ghost wsl: gone (source already retired; PATH reinstall + _archive excluded from audit).
- New Tier-1 skills: docker-compose, agent-evals, ms-graph, azure-bicep, plan-grill, react-performance, web-a11y-audit.
- hubspot + dynamics-365 parents rewritten as multi-level dispatchers.
- Batch split: 42 monoliths → multi-level via split_skill.py.
- Audit: canonical_skill_dirs skips `_` prefixes (_archive).
- Sync: sync-all-clis + sync-codex-skills + manual antigravity/gemini/grok/opencode links for new skills.

## Gates

- `uv run pytest` green
- `skill-router audit check` OK
- PATH: `uv tool install -e '.[semantic]' --force`
