# REFERENCE - Stable Facts

## Tech Stack
- Python ≥3.11 (dev on 3.14), hatchling, pytest, ruff, mypy
- Optional: numpy (semantic recommend / audit discrim)
- Runtime deps resolved via `shared/compat.py`: cheap_llm, ollama_client

## Commands
- Install: `uv tool install -e '.[semantic]'` or `pip install --user -e .`
- Test: `uv run pytest` (174 offline)
- Lint/type: `uv run ruff check .` · `uv run mypy src tests`
- Layout: `python3 ~/.claude/hooks/vertical-slice-guard.py src/skill_router/`
- Smoke: `skill-router catalog` · `audit check` · `route --prompt "..."` · `discover`

## Entrypoints
- Hook: `~/.claude/hooks/skill-router.py` → `skill_router.command.main`
- CLI: `~/.local/bin/skill-router` (editable) · `python3 -m skill_router`

## Conventions
- Hook always fails open (`{"continue": true}`)
- Routes declare full skill families; depth lexical-only on hook path
- Canonical skills: `~/.claude/skills/`; other CLIs symlink

## Budget / description caps
- Codex model-visible description hard rule: **185** chars (`features/budget.HARD_CAP`).
- Structural advisory `verbose` uses the same threshold (`DESC_CAP` / `DESC_WARN_VERBOSE`).
- `skill-router audit budget` needs live `codex debug prompt-input`; health = no first-party over-cap.
- Vendored packs live under `~/.claude/skills-sources/` (managed, not local debt).
