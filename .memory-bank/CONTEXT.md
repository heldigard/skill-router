# CONTEXT - Current State
> Updated: 2026-07-19

## Active Focus
- skill-router on native Ubuntu 26: routing coverage complete, gates green.

## Recent Changes
- Dedicated `shepherd` + `implement-issue` routes (prio 88); catalog 170/170, unrouted=0.
- Six oversized skills split multi-level (`catalog --oversized 300` = 0).
- WSL residual docs cleaned; embed timeout call typed for pyright.
- Routes 70; pytest 174; audit check green.

## Blockers / Risks
- None. Concurrent foreign CLI sessions may touch `~/.claude` outside this repo.

## Next Steps
- Keep `catalog --oversized 300` at 0 when adding skills.
- New domain skills → declare full family on routes (not recommender-only).
