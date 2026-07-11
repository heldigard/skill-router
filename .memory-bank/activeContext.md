# Active Context

## 2026-07-05
- Second-pass hardening shipped: catalog cache, classify fail-open fix, mypy 7->0,
  dead code removed, +5 tests. Gate green (pytest 69, ruff, mypy, coverage 76%).
- See `progress.md` for the full entry and `systemPatterns.md` for the two new
  durable decisions (catalog cache, classify defensive envelope).

## Handoff Format
When ending a session, run `agent-memory handoff` and paste the output here.
- 2026-07-11T18:20:42Z | status:active | session:cworker:codex-frontier:20260711-132041:a55b4a805533 | cworker:codex-frontier — write intent without --write; return patch suggestion; upgraded by --min-intelligence frontier: CONSULTATION (advisory only, no edits). Context: cross-CLI agent harness; controllers are frontier reasoning models (Claude Fable 5, Codex GPT-5.6 Sol, Gemini 3
