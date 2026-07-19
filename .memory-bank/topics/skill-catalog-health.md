# Skill catalog health
> Updated: 2026-07-19

## Snapshot (native Ubuntu pass)

- Routes: **70** (shepherd + implement-issue dedicated; WSL retired).
- Coverage: **170/170**, hint_drift=0, ghost=0, unrouted=0.
- Oversized body >300L: **0** (split implement-issue, verified-email, edge-to-edge,
  android-intent-security, compose-modifier-and-layout-style,
  kotlin-coroutines-structured-concurrency).
- Host: native Ubuntu 26; no WSL route.
- Multi-CLI: symlinks under codex/gemini/kimi/qwen/opencode inherit `sections/`.

## Gates

- `uv run pytest` → 174 offline
- `skill-router audit check` → OK
- `skill-router catalog --oversized 300` → 0
- PATH: editable `uv tool install -e '.[semantic]'` → this repo

## Android native (2026-07-18)

- Hub: `android-kotlin` multi-level
- Sources: `~/.claude/skills-sources/{android-skills-google,chrisbanes-skills}`
- Route: platform_cloud android domain (priority 88)
