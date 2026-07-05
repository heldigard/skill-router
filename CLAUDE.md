# Project: skill-router

`skill-router` — unified skill routing for cross-CLI coding agents (Claude Code,
Codex, Antigravity/Gemini). Graduated from three monolithic scripts in
`~/.claude/` into one vertical-slice package. Mirrors the `codeq`,
`prompt-improve`, `smart-trim`, `web-research`, `cheap-llm` layouts.

## Architecture: vertical-slice hook package + CLI

skill-router is BOTH a **UserPromptSubmit hook** AND a **CLI**.

- Hook entry: `~/.claude/hooks/prompt-router.py` — a ~40-line **shim** that does
  `from skill_router.command import main; main()`. Wired in `settings.json`.
- CLI entry: `python3 -m skill_router <sub>` and the `~/.claude/scripts/skill-router`
  launcher. Five subcommands: `route`, `classify`, `depth`, `catalog`, `audit`.

## What it consolidates

| Legacy piece (was)                       | Now                          |
|------------------------------------------|------------------------------|
| `~/.claude/hooks/prompt-router.py` (429L)| `features/routing/` + shim   |
| `~/.claude/scripts/intent_route.py` (194L)| `features/classify/` + shim |
| `~/.claude/scripts/skills-audit.py` (218L)| `features/audit/` + shim    |
| **(new)** depth selector                 | `features/depth/`            |

`codex-worker-router.py` (1500+L) is NOT migrated — different domain (worker
model routing, not skill routing).

## Layout

```
src/skill_router/
  shared/        paths, config, compat (sys.path bootstrap), skill_io, embed
  features/
    catalog/     list/inspect skills, multi-level detection, oversized finder
    classify/    prompt -> {category, tier} (cheap_llm cascade, $0 sub)
    routing/     regex -> hint table + match logic (ROUTES data + command)
    depth/       NEW: section-level load selection via embeddings
    audit/       structural / drift / discrim / bench / check
  command.py     UserPromptSubmit hook entry (fail-open)
  cli.py         argparse CLI dispatcher
  __main__.py    `python3 -m skill_router`
tests/           38 tests, fake CLAUDE_HOME fixtures, offline (no Ollama needed)
scripts/
  split_jpa_patterns.py   one-shot pilot splitter (monolith -> multi-level)
```

## Conventions

- **One responsibility per feature folder** (cohesion > size).
- Hook **always fails OPEN**: any internal error returns `{"continue": true}`.
  Prompt submission never blocks on router bugs.
- **Late binding** for monkeypatched embed/is_alive in tests.
- `shared/compat.py` bootstraps `~/.claude/scripts/` onto sys.path so
  `cheap_llm` and `ollama_client` resolve. Uses `Path(__file__).resolve()`
  (symlink-safe — the hook shim is invoked via symlinked paths from Codex/Gemini).

## Multi-level skill format

A skill gains a `sections/` subdir + a `sections:` frontmatter index:

```
~/.claude/skills/<name>/
  SKILL.md                # frontmatter (with `sections:` list) + summary + TOC
  sections/
    <slug>.md             # one focused topic per file
```

The depth selector embeds prompt + section titles; if top cosine >= 0.62, the
hook appends a hint telling the agent to Read that one section file directly
instead of scanning the whole body.

`jpa-patterns` is the pilot: 658L monolith -> 192L index + 5 section files.

## Commands

- Install (dev): `pip install --user -e .`
- Test: `python3 -m pytest tests/ -q` (38 tests, offline)
- Lint: `ruff check src/skill_router/`
- Layout gate: `python3 ~/.claude/hooks/vertical-slice-guard.py src/skill_router/`
- Smoke: `python3 -m skill_router catalog` / `audit structural` / `route --prompt "..."`

## Model / cascade

- Classification + depth use `cheap_llm.cheap_complete` (T1 local Ollama
  embeddinggemma -> T2 cloud) and `ollama_client.embed`. Both resolved at
  runtime via `shared/compat.py`. Degrade gracefully when Ollama is down
  (depth returns "summary", classify returns "meta" tier T1).

## Things that look wrong but aren't

- PostToolUse `vertical-slice-guard.py` reports `nesting_depth 4/5/6/7` on
  Write/Edit — these are FALSE POSITIVES in the intermediate (pre-format) state.
  Running the guard manually on the final tree (`guard src/skill_router/`)
  returns exit 0. The hook fires on a stale snapshot.
- Pyright `Import ".X" could not be resolved` warnings on `...shared.*` are
  workspace-config false positives — the package is `pip install --user -e`'d
  and resolves at runtime (smoke tests prove it).
- The hook shim is invoked via symlinks from `~/.codex/hooks/` and
  `~/.gemini/hooks/`. `Path(__file__).resolve()` in compat.py unwraps the
  symlink so sibling imports land in the real `~/.claude/scripts/`.

## Backups (rollback path)

Before swapping to shims, the originals were preserved:
- `~/.claude/hooks/prompt-router.py.pre-graduation.bak`     (429L monolith)
- `~/.claude/scripts/intent_route.py.pre-graduation.bak`    (194L monolith)
- `~/.claude/scripts/skills-audit.py.pre-graduation.bak`    (218L monolith)
- `~/.claude/skills/jpa-patterns/SKILL.md.pre-multilevel.bak` (658L monolith)

To roll back: `cp <file>.bak <file>` (remove the shim) and `pip uninstall skill-router`.

## Workflow

- New routing entry → append one tuple to `features/routing/routes.py::ROUTES`.
- New multi-level skill → run `scripts/split_jpa_patterns.py` adapted to the
  target skill dir (or hand-write the `sections:` frontmatter + `sections/*.md`).
- Before shipping → `pytest tests/ -q && ruff check src/skill_router/`.
- Register durable decisions in this repo's memory (or `~/.claude` project bank).
