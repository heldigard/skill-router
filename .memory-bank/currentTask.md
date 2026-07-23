# Current Task
> Updated: 2026-07-23

## Goal
Ship Cosmos DB knowledge-base routing and shared skill support for Microsoft Foundry agents.

## Status
- **DONE** — implementation and validation complete; selective commit/push pending.

## Acceptance Criteria
- [x] `azure-cosmos-rag` multi-level skill authored from Microsoft Learn
- [x] dedicated Cosmos RAG route and regression coverage
- [x] transactional Cosmos prompts remain outside RAG route
- [x] pytest / ruff / mypy / audits / smokes green
- [x] shared skill synced to Codex, Qwen, Kimi, Gemini, and Antigravity
- [x] memory refreshed
- [ ] selective commits pushed

## Related
- `features/routing/route_groups/platform_cloud.py`
- `tests/test_routing.py`, `tests/test_command_hook.py`
- `~/.claude/skills/azure-cosmos-rag/`
