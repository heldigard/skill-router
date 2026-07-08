"""Core route definitions."""

from ..route import Route

CORE_ROUTES: list[Route] = [
    Route(
        patterns=(
            '\\b(deliberaci[oó]n|deliberation|fusion|contradicciones|blind spots?|coverage gaps?)\\b',
            '\\b(arquitectura|architecture|dise[nñ]o|design|plan|review|revisi[oó]n)\\b.*\\b(segunda opini[oó]n|consenso|razonamiento|reasoning|validaci[oó]n)\\b',
            '\\b(segunda opini[oó]n|consenso|razonamiento|reasoning|validaci[oó]n)\\b.*\\b(arquitectura|architecture|dise[nñ]o|design|plan|review|revisi[oó]n)\\b',
            '\\b(ecosistema|ecosystem|system design|dise[nñ]o de sistema)\\b.*\\b(mejorar|optimizar|potenciar|calidad)\\b',
            '\\b(mejorar|optimizar|potenciar|calidad)\\b.*\\b(ecosistema|ecosystem|system design|dise[nñ]o de sistema)\\b',
        ),
        hint=(
            'Deliberation: for high-stakes architecture/review/planning, run `fusion`/`fusion-local` '
            'to get the 5-field analysis (consensus, contradictions, coverage gaps, unique insights, '
            'blind spots). Treat it as advisory signal; the controller brain still makes the final call.'
        ),
        tools=('fusion-local', 'fusion'),
        workers=('cworker',),
        priority=88,
    ),
    Route(
        patterns=('\\b(swarm|multi[- ]?agent|varias opiniones|consenso|varios modelos)\\b',
         '\\b(segunda opinion|segunda opinión|cross[- ]?check|multiple perspectives)\\b',
         '\\b(ejecuta varios agentes|lanza swarm|agent team|equipo de agentes)\\b',
         '\\b(worker|workers|delegar|delegaci[oó]n|modelo peque[nñ]o|modelo barato)\\b'),
        hint=('Worker routing: for bounded side tasks, use `cworker`/`ai-delegate` (wrapper over '
         'codex-worker-router); keep default workers read-only, require `--write --write-scope` for edits, '
         'and reserve `swarm_run` for consensus or independent validation.'),
        workers=('cworker', 'ai-delegate', 'swarm-mcp'),
        priority=70,
    ),
    Route(
        patterns=('\\b(investiga|research|latest|reciente|actual|mayo de 2026|today|hoy)\\b',
         '\\b(busca en internet|web search|look up|novedades|tendencias)\\b'),
        hint=('Research routing: use the `web-search`/`search-smart`/`web-reader` skills first '
         '(`web-research.py` local stack: SearXNG -> Firecrawl -> Z.AI/MiniMax fallback). Official '
         'docs/Context7 for product and framework facts. Perplexity/MiniMax MCPs are fallback only when '
         'the local stack is down or a deep cited research tool is explicitly needed.'),
        skills=('web-search', 'search-smart', 'web-reader'),
        tools=('searxng', 'firecrawl', 'context7'),
        priority=85,
    ),
    Route(
        patterns=('\\b(dead code|unused code|c[oó]digo muerto|sin usar|unused (func|import|var))\\b',
         '\\b(code review|review de c[oó]digo|revisi[oó]n de c[oó]digo|revisa(?:r)? (este )?proyecto)\\b',
         '\\b(arquitectura|architecture|layering|capas)\\b.*\\b(review|revisi[oó]n|validar|validate|auditar|audit)\\b',
         '\\b(security scan|escaneo de seguridad|vulnerab|sast|semgrep)\\b',
         '\\b(secret leak|hardcoded (secret|key|token)|secretos|leaked (key|token))\\b',
         '\\b(circular dep|layering violation|arch rule|dependency rule|import rule)\\b',
         '\\b(revisa antes de (commit|push|ship)|antes de commitear|before (commit|shipping|push) '
         '(review|scan|check))\\b'),
        hint=('Quality sensors (ship-time): call `codescan capabilities` once for local sensor metadata, '
         'then run the narrowest useful `codescan` sensor (`dead`/`sec`/`secrets`/`arch`/`all`) — '
         'dead-code (vulture/knip), SAST (semgrep), leaked secrets (gitleaks), import-rule violations '
         '(dependency-cruiser). Normalized summary, vendor-excluded. Ref: rules/code-quality-sensors.md. '
         '(Edit-time facts → `codeq`.)'),
        tools=('codescan',),
        priority=80,
    ),
    Route(
        patterns=(
            '\\b(code facts?|symbol|signature|call sites?|references|refs|imports?|deps|rdeps)\\b',
            '\\b(find where|where is|d[oó]nde est[aá]|definici[oó]n|definition)\\b.*\\b(function|funci[oó]n|class|clase|symbol|s[ií]mbolo)\\b',
            '\\b(edit|editar|modificar|refactor|cambiar)\\b.*\\b(function|funci[oó]n|method|m[eé]todo|class|clase|symbol|s[ií]mbolo)\\b',
            '\\b(codeq|ctags|ast-grep|tree-sitter|structured code context)\\b',
        ),
        hint=(
            'Code intelligence: use `codeq` for edit-time facts before reading whole files. '
            'For scripts/workers call `codeq --json capabilities` once, then prefer '
            '`codeq --json context NAME FILE -p PROJ --no-llm` before edits or '
            '`codeq --json relations NAME FILE -p PROJ --no-llm` for compact call orientation. '
            'Use Markdown `codeq context` only for direct controller reading.'
        ),
        skills=('code-intelligence',),
        tools=('codeq', 'ast-grep', 'ctags'),
        priority=82,
    ),
    Route(
        patterns=('\\b(documentaci[oó]n oficial|official docs|framework docs|best practices|buenas '
         'pr[aá]cticas|est[aá]ndar de la industria|industry standard|c[oó]mo se estructura|structure '
         'project)\\b',),
        hint=('Skill: load `best-practices-researcher` or load `framework-docs-researcher` to gather industry '
         'standards, community conventions, or official library/framework documentation.'),
        skills=('best-practices-researcher', 'framework-docs-researcher'),
    ),
]
