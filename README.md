# skill-router

Unified skill routing for cross-CLI coding agents (Claude Code, Codex,
Antigravity/Gemini). Consolidates three formerly-fragmented pieces into one
vertical-slice package, and adds a new **depth selector** so multi-level skills
load only the section the prompt needs.

## What it consolidates

| Legacy piece (monolith) | Migrated module |
|--------------------------|-----------------|
| `~/.claude/hooks/prompt-router.py` (429L hook) | `features/routing/` |
| `~/.claude/scripts/intent_route.py` (194L CLI) | `features/classify/` |
| `~/.claude/scripts/skills-audit.py` (218L gate) | `features/audit/` |
| **(new)** depth selector | `features/depth/` |

## Why

The routing logic was scattered across four files (prompt-router, intent_route,
skill-router rule, codex-worker-router). Three of them are skill-routing
concerns; consolidating them into one package lets the depth selector reuse the
classifier + catalog without crossing script boundaries. The fourth
(codex-worker-router, 1500+L) is a different domain (worker/model routing) and
stays put.

## Multi-level skills (progressive disclosure L2)

A legacy skill is one `SKILL.md`. A multi-level skill adds a `sections/` dir:

```
~/.claude/skills/jpa-patterns/
  SKILL.md                # frontmatter + summary + TOC (~120L)
  sections/
    lazy-loading.md
    n-plus-1.md
    transactions.md
```

The depth selector embeds the prompt + each section title; if the top cosine
clears a threshold, the hook tells the agent to Read that one section file
instead of scanning the whole body.

## CLI

```
skill-router route --prompt "..."          # show routing hints + depth
skill-router classify --prompt "..."       # category + tier (was intent_route)
skill-router depth --skill jpa-patterns --prompt "..."
skill-router catalog [--multilevel|--oversized]
skill-router audit [structural|drift|discrim|bench|all|check]
```

## Install (dev)

```
pip install -e .
pytest tests/ -q
ruff check src/skill_router/
```

## Shims (backward-compat)

Three ecosystem shims preserve the wired paths so `settings.json` /
`hooks.json` keep resolving untouched:

- `~/.claude/hooks/prompt-router.py` → `skill_router.command.main` (UserPromptSubmit)
- `~/.claude/scripts/intent_route` → `skill_router.cli` (`classify`)
- `~/.claude/scripts/skills-audit` → `skill_router.cli` (`audit`)
- `~/.claude/scripts/skill-router` → `skill_router.cli` (NEW unified)

## License

MIT.
