# skill-router

Unified skill routing for cross-CLI coding agents (Claude Code, Codex,
Antigravity/Gemini). Consolidates three formerly-fragmented pieces into one
vertical-slice package, and adds a **structured router + depth selector** so
agents load only the skill sections and documentation namespaces a prompt needs.

## What it consolidates

| Previous monolith | Migrated module |
|--------------------------|-----------------|
| pre-package routing hook monolith (429L) | `features/routing/` |
| `~/.claude/scripts/intent_route.py` (194L CLI) | `features/classify/` |
| `~/.claude/scripts/skills-audit.py` (218L gate) | `features/audit/` |
| structured routing metadata + depth selector | `features/routing/` + `features/depth/` |

## Why

The routing logic was scattered across four files (hook routes, intent_route,
skill-router rule, codex-worker-router). Three of them are skill-routing
concerns; consolidating them into one package lets the depth selector reuse the
classifier + catalog without crossing script boundaries. The fourth
(codex-worker-router, 1500+L) is a different domain (worker/model routing) and
stays put.

## Multi-level skills (progressive disclosure L2)

A single-file skill is one `SKILL.md`. A multi-level skill adds a `sections/` dir:

```
~/.claude/skills/jpa-patterns/
  SKILL.md                # frontmatter + summary + TOC (~120L)
  sections/
    lazy-loading.md
    n-plus-1.md
    transactions.md
```

The router stores machine-readable metadata on each route: `skills`, `tools`,
`workers`, `doc_namespaces`, and `priority`. Route definitions are grouped by
domain under `features/routing/route_groups/` and aggregated in stable order by
`routes.py`. The hook uses that metadata directly instead of parsing human hint
text. The depth selector embeds the prompt + section
title/slug/keywords/aliases/tool/doc metadata; if the top cosine clears a
threshold, the hook tells the agent to Read that one section file instead of
scanning the whole body.

The hook also emits a compact doc-routing line when routes declare
documentation namespaces. That keeps broad platform docs out of the prompt
until an agent needs exact API details via Context7, OpenAI docs, or a local docs
MCP.

Current harness skills also route directly for Codex, Claude Code, Playwright
MCP, Context7, and Antigravity so agent-runtime questions land on focused
runbooks instead of generic web/code advice. Host is native Ubuntu (WSL route
retired).

## CLI

```
skill-router discover --prompt "find references, edit safely, then validate" --json
skill-router discover --examples              # compact starter intents
skill-router route --prompt "..."          # show routing hints + depth
skill-router route --prompt "..." --explain # include route metadata
skill-router route --prompt "..." --json    # includes matched/unmatched/skipped decision
skill-router classify --prompt "..."       # category + tier (was intent_route)
skill-router depth --skill jpa-patterns --prompt "..."
skill-router catalog [--multilevel|--oversized]
skill-router audit [structural|drift|coverage|discrim|bench|budget|all|check]
# coverage: route table vs catalog — hint/skills= drift, ghost skills, unrouted
# budget: actual Codex-visible entries and descriptions shortened by its 2% cap
```

`discover` is the deterministic front door for the graduated ecosystem. It
reports live command availability, cost/side-effect cards, exact skill paths,
and the cheapest next actions without calling an LLM or embedding service.

## Install (dev)

```
pip install -e .
uv run pytest
uv run ruff check .
uv run mypy src tests
```

For the semantic `audit discrim` and `audit bench` probes in an isolated CLI
installation, install the semantic extra: `uv tool install '.[semantic]'`.

## Ecosystem Entrypoints

Ecosystem entrypoints:

- `~/.claude/hooks/skill-router.py` → `skill_router.command.main` (UserPromptSubmit)
- `~/.claude/scripts/skill-router` → `skill_router.cli`

## License

MIT.
