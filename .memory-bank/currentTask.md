# Current Task
> Updated: 2026-07-05

## Goal
- Autonomous review + hardening pass on skill-router (perf, correctness, debt, noise).

## Scope
- Included: catalog cache, classify fail-open, mypy fixes, dead-code purge, tests, memory.
- Not included: routes.py rework (clean data table, no change needed), depth is_alive()
  micro-opt (correct as-is; would need measurement to justify behavior change).

## Acceptance Criteria
- [x] Gate green: pytest, ruff, mypy all clean.
- [x] No untracked noise; memory bank updated.
- [x] Commit + push on main.

## Related
- Files: src/skill_router/shared/{skill_io,embed}.py,
  src/skill_router/features/{classify,audit}/command.py,
  src/skill_router/CLAUDE.md, tests/test_{skill_io,classify}.py,
  scripts/split_jpa_patterns.py (deleted).
