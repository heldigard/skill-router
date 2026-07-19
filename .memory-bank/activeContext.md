# Active Context
> Updated: 2026-07-19

## Handoff
- Host: native Ubuntu 26 (WSL route retired 2026-07-18).
- Latest ship: shepherd + implement-issue dedicated routes; full catalog coverage;
  multi-level split of six Android/workflow monolitos; embed pyright fix; docs.
- Verify: `uv run pytest && uv run ruff check . && uv run mypy src && skill-router audit check`
- Smoke: `skill-router route --prompt "shepherd my open PRs"` → `shepherd`
- Install: editable uv tool at `~/.local/bin/skill-router` → this repo.

## Notes
- Recommender rescue is for unmatched prompts only; domain routes must declare skill families.
- Do not reintroduce WSL routes or CODEX_HOME as claude_home fallback.
