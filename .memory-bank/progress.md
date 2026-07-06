# Progress

## 2026-07-05
- Memory bank initialized.

## Format
- [YYYY-MM-DD]: What was done + verification status
- 2026-07-05T18:50:54Z | status:completed | 2026-07-05: Implemented structured routing, enriched section metadata parser, depth doc/tool propagation, route --explain, split_skill --dry-run/--force/--claude-home, threshold 0.60, and test coverage. Verification: pytest 64 passed, ruff clean, skill-router audit all drift missing=0 for Codex/Gemini/Kimi/Qwen/OpenCode/Antigravity.
- 2026-07-05T19:09:22Z | status:completed | 2026-07-05: Second review after cross-CLI skill-router and prompt-improve naming work. Verified skill-router tests, ruff, audit all, hook resolution, and cworker config. Corrected Antigravity long-context docs outside repo to keep agy3-pro=Gemini 3.1 Pro High and agy35-flash=Gemini 3.5 Flash High.
- 2026-07-05Tsnapshot | status:completed | Second-pass hardening: (1) catalog() mtime-signature cache + clear_catalog_cache() — kills per-prompt FS scan in UserPromptSubmit hook; (2) classify() fail-open bug fix (cheap_complete raising or returning None/ non-dict no longer escapes); (3) mypy 7->0 (skill_io _as_str_tuple helper, audit out: dict[str,list[Any]], numpy pv_raw rename); (4) dead code removed (embed_batch, scripts/split_jpa_patterns.py); (5) +5 tests (cache invalidation + classify robustness). Gate: pytest 69 passed, ruff clean, mypy clean, coverage 76% (was 74%).
- 2026-07-06T00:15:36Z | status:completed | session:93483d3a-1e3e-42d2-b269-0d52eba07bc6 | claude: Autonomous review + hardening pass on skill-router (perf, correctness, debt,...
