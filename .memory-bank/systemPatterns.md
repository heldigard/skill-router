# System Patterns

## Format
- [YYYY-MM-DD]: Decision -> Reason -> Alternative considered

## Decisions
- None yet.
- 2026-07-05T18:50:54Z | status:completed | 2026-07-05: skill-router routes are structured Route records with explicit skills/tools/workers/doc_namespaces/priority. Hook analysis uses match_routes(), collect_metadata(), route_records(), and depth decisions; skill extraction from human hint text is retired.
- 2026-07-05 | status:live | Catalog cache via mtime-signature -> Reason: catalog() is called on every UserPromptSubmit (hook path) AND by audit/bench; reading 100+ SKILL.md + parsing frontmatter per prompt is wasteful when the FS rarely changes between prompts. Signature = max mtime across skills_root + every skill dir + every SKILL.md; stat() is ~10x cheaper than read_text()+parse. Invalidation is automatic on add/remove/rename/edit. Keyed by skills_root() Path so per-test tmp_path never collides. `use_cache=False` escape hatch for audit-after-edit; `clear_catalog_cache()` for tests. -> Alternative rejected: TTL cache (time-based) would serve stale data briefly and adds a clock dep; mtime-signature is exact.
- 2026-07-05 | status:live | classify() defensive envelope -> Reason: cheap_llm.cheap_complete() is an external dep whose exact return contract (dict vs None vs raise) is not guaranteed across versions; classify() promises "never raises" and feeds the hook fail-open contract. Wrap the call in try/except + isinstance(out, dict) guard so a broken/None/raising cascade degrades to meta-tier fallback instead of AttributeError. Applies to any wrapper over an external LLM cascade.
