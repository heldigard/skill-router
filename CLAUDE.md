# Project: skill-router

`skill-router` — unified skill routing for cross-CLI coding agents (Claude Code,
Codex, Antigravity/Gemini). Graduated from three monolithic scripts in
`~/.claude/` into one vertical-slice package. Mirrors the `codeq`,
`prompt-improve`, `smart-trim`, `web-research`, `cheap-llm` layouts.

## Architecture: vertical-slice hook package + CLI

skill-router is BOTH a **UserPromptSubmit hook** AND a **CLI**.

- Hook entry: `~/.claude/hooks/skill-router.py` — a thin **entrypoint** that does
  `from skill_router.command import main; main()`. Wired in `settings.json`.
- CLI entry: PATH wrapper `~/.local/bin/skill-router` (mirrors codeq/codescan),
  `~/.claude/scripts/skill-router`, and `python3 -m skill_router`.
  Five subcommands: `route`, `classify`, `depth`,
  `catalog`, `audit`.

## What it consolidates

| Previous piece                           | Now                              |
|------------------------------------------|----------------------------------|
| pre-package routing hook monolith (429L)| `features/routing/` + hook entrypoint |
| `~/.claude/scripts/intent_route.py` (194L)| `features/classify/` (RETIRED — use `skill-router classify`) |
| `~/.claude/scripts/skills-audit.py` (218L)| `features/audit/` (RETIRED — use `skill-router audit`) |
| **(new)** depth selector                 | `features/depth/`                |

Old script names (`intent_route`, `skills-audit`) were retired, not shimmed —
their subcommands live under the unified `skill-router` CLI.

`codex-worker-router.py` (1500+L) is NOT migrated — different domain (worker
model routing, not skill routing).

## Layout

```
src/skill_router/
  shared/        paths, config, compat (sys.path bootstrap), skill_io, embed
  features/
    catalog/     list/inspect skills, multi-level detection, oversized finder
    classify/    prompt -> {category, tier} (cheap_llm cascade, $0 sub)
    routing/     structured Route table split by domain + skills/tools/workers/docs metadata
    depth/       section-level load selection via embeddings + section metadata
    recommend/   SEMANTIC skill recommender: prompt -> top-k skills via Ollama
                 embeddings + on-disk index. Resuscitates the ~33% of skills with
                 no Route regex and entries dropped past skillListingBudgetFraction.
    audit/       structural / drift / discrim / bench / check
  command.py     UserPromptSubmit hook entry (fail-open). On regex-unmatched, falls
                 back to features/recommend before declaring unmatched.
  cli.py         argparse CLI dispatcher (route/classify/depth/recommend/catalog/audit)
  __main__.py    `python3 -m skill_router`
tests/           offline (Ollama stubbed); `recommend` smoke is via the CLI live
scripts/
  split_skill.py    generalized monolith -> multi-level splitter (--map or auto-kebab)
```

## Conventions

- **One responsibility per feature folder** (cohesion > size).
- Hook **always fails OPEN**: any internal error returns `{"continue": true}`.
  Prompt submission never blocks on router bugs.
- **Late binding** for monkeypatched embed/is_alive in tests.
- `shared/compat.py` bootstraps `~/.claude/scripts/` onto sys.path so
  `cheap_llm` and `ollama_client` resolve. Uses `Path(__file__).resolve()`
  (symlink-safe: the hook entrypoint is invoked via symlinked paths from Codex/Gemini).

## Structured routing + multi-level skill format

Routes are `Route(...)` records, not hint-only tuples. Each route owns its
human hint plus machine-readable `skills`, `tools`, `workers`,
`doc_namespaces`, and `priority`. `routes.py` aggregates domain route groups
from `features/routing/route_groups/`, preserving source order for stable
priority ties. `skill-router route --json` returns those records; `--explain`
prints a readable trace.

A skill gains a `sections/` subdir + a `sections:` frontmatter index:

```
~/.claude/skills/<name>/
  SKILL.md                # frontmatter (with `sections:` list) + summary + TOC
  sections/
    <slug>.md             # one focused topic per file
```

The depth selector embeds prompt + section metadata; if top cosine >= 0.60, the
hook appends a hint telling the agent to Read that one section file directly
instead of scanning the whole body.

Section frontmatter can include `keywords`, `aliases`, `tools`, and
`doc_namespaces`; depth uses those compact terms for ranking. All previously
oversized local skills are now multi-level indexes; `catalog --oversized 300`
should stay at 0.

## Commands

- Install (dev): `pip install --user -e .`
- Test: `uv run pytest` (174 tests, offline)
- Lint: `uv run ruff check .`
- Type check: `uv run mypy src tests`
- Layout gate: `python3 ~/.claude/hooks/vertical-slice-guard.py src/skill_router/`
- Smoke: `python3 -m skill_router catalog` / `audit structural` / `route --prompt "..."`

## Model / cascade

- Classification + depth use `cheap_llm.cheap_complete` (T1 local Ollama
  embeddinggemma -> T2 cloud) and `ollama_client.embed`. Both resolved at
  runtime via `shared/compat.py`. Degrade gracefully when Ollama is down
  (depth returns "summary", classify returns "meta" tier T1).
- Classification requires `cheap_llm>=1.2` and caps its four-field JSON result
  at 256 output tokens; this keeps the high-frequency hook bounded on both
  Ollama and cloud fallbacks.

## Things that look wrong but aren't

- PostToolUse `vertical-slice-guard.py` reports `nesting_depth 4/5/6/7` on
  Write/Edit — these are FALSE POSITIVES in the intermediate (pre-format) state.
  Running the guard manually on the final tree (`guard src/skill_router/`)
  returns exit 0. The hook fires on a stale snapshot.
- Pyright `Import ".X" could not be resolved` warnings on `...shared.*` are
  workspace-config false positives — the package is `pip install --user -e`'d
  and resolves at runtime (smoke tests prove it).
- The hook entrypoint is invoked via symlinks from `~/.codex/hooks/` and
  `~/.gemini/hooks/`. `Path(__file__).resolve()` in compat.py unwraps the
  symlink so sibling imports land in the real `~/.claude/scripts/`.

## Workflow

- New routing entry → append one `Route(...)` to the appropriate
  `features/routing/route_groups/*.py` list with explicit `skills`, `tools`,
  `workers`, `doc_namespaces`, and `priority`.
- New multi-level skill → `python3 scripts/split_skill.py <name> --dry-run`,
  then run without `--dry-run` when the H2 split is sane. It auto-generates
  section keywords and refuses existing `sections/` unless `--force`.
- Before shipping → `pytest tests/ -q && ruff check src/skill_router/`.
- Register durable decisions in this repo's memory (or `~/.claude` project bank).
