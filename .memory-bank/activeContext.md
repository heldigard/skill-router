# Active Context
> Updated: 2026-07-19

## Handoff
- Host: native Ubuntu 26.
- Budget health fails only on **first-party** over-cap descriptions; skills-sources + plugins + Codex `.system` are managed.
- Codex listing still dynamically squeezes ~all entries when catalog is large (`effective≈27ch`); descriptions ≤185 fix *source* debt, not dynamic squeeze.
- Pipeline controllers: `claude`, `codex`, `gemini`, `antigravity`, **`grok`**.
- Install: `uv tool install -e '.[semantic]'` → `~/.local/bin/skill-router`.

## Verify
```bash
uv run pytest && uv run ruff check . && uv run mypy src tests
skill-router audit check && skill-router audit budget
skill-router catalog --oversized 300
```

## Notes
- Do not push skills-sources to chrisbanes/android upstream remotes.
- Do not reintroduce WSL routes.
