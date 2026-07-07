"""Structured routing table for skill-router.

Each route declares regex patterns, the compact hook hint, and machine-readable
metadata for skill loading, tool routing, workers, and documentation namespaces.
Priority controls which matched hints survive the UserPromptSubmit budget; source
order breaks ties.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    """One routing rule plus orchestration metadata."""

    patterns: tuple[str, ...]
    hint: str
    skills: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    workers: tuple[str, ...] = ()
    doc_namespaces: tuple[str, ...] = ()
    priority: int = 50


ROUTES: list[Route] = [
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
    Route(
        patterns=('\\b(payload|payloadcms|payload cms|payload\\.config|collectionconfig)\\b',
         '\\b(collections?|fields?|hooks?|access control)\\b.*\\b(payload|cms)\\b'),
        hint=('Skill: load `payload` for Payload CMS 3.x configs, collections, fields, hooks, access control, '
         'Local API security, transactions, plugins, and Next.js integration.'),
        skills=('payload',),
        doc_namespaces=('payload', 'nextjs'),
    ),
    Route(
        patterns=('\\b(jenkins|jenkinsfile|jcasc|job dsl)\\b',
         '\\b(declarative pipeline|scripted pipeline|shared librar(?:y|ies))\\b'),
        hint=('Skill: load `jenkins` for Jenkinsfile, Declarative/Scripted Pipeline, shared libraries, JCasC, '
         'credentials safety, agents, plugins, and CI/CD troubleshooting.'),
        skills=('jenkins',),
        doc_namespaces=('jenkins',),
    ),
    Route(
        patterns=('\\b(ag[- ]?grid|data grid|angular grid|celdas?|grid community)\\b',
         '\\b(row group|tree data|master detail|excel export|cell renderer)\\b.*\\b(ag[- ]?grid|grid)\\b'),
        hint=('Skill: load `ag-grid-community-angular` for AG Grid Community (free) patterns in Angular — setup '
         'v34+, themes, cell renderers, infinite scroll, and workarounds for tree-data, grouping, '
         'master/detail, Excel export, and clipboard without Enterprise license.'),
        skills=('ag-grid-community-angular',),
        doc_namespaces=('ag-grid',),
    ),
    Route(
        patterns=('\\b(react|reactjs|\\bjsx\\b|\\btsx\\b|next\\.?js|nextjs|server '
         'components?\\b|usestate|useeffect|usememo|react compiler|use action state)\\b',),
        hint=('Skill: load `react` for React 19 (hooks, Server Components, Actions, React Compiler, state, '
         'Next.js App Router); `frontend-design` for UI craft; `typescript-pro` for typed JSX.'),
        skills=('react', 'frontend-design', 'typescript-pro'),
        tools=('context7',),
        doc_namespaces=('react', 'nextjs'),
        priority=75,
    ),
    Route(
        patterns=('\\b(angular|ngfor|ngif|@component|@injectable|rxjs|signals?\\b|angular cli|ng serve|ng '
         'build|standalone component|inject\\(\\)|providezoneless)\\b',),
        hint=('Skill: load `angular` for current Angular v22+ (standalone components, signals, zoneless, control '
         'flow @if/@for, inject(), RxJS, CLI); `frontend-design` for UI craft; `typescript-pro` for typed '
         'templates.'),
        skills=('angular', 'frontend-design', 'typescript-pro'),
        tools=('context7',),
        doc_namespaces=('angular', 'rxjs'),
        priority=75,
    ),
    Route(
        patterns=('\\b(vue|vuejs|vue\\.js|script setup|composition '
         'api|composables?\\b|pinia|nuxt|defineprops|defineemits)\\b',),
        hint=('Skill: load `vue` for Vue 3.5 (Composition API, <script setup>, ref/reactive/computed/watch, '
         'composables, Pinia, Nuxt); `frontend-design` for UI craft.'),
        skills=('vue', 'frontend-design'),
        tools=('context7',),
        doc_namespaces=('vue', 'nuxt'),
    ),
    Route(
        patterns=('\\b(svelte|sveltekit|runes|\\$state|\\$derived|\\$effect)\\b',),
        hint=('Skill: load `svelte` for Svelte 5 runes ($state/$derived/$effect, onclick, $props) + SvelteKit '
         '(load/form actions/SSR); `frontend-design` for UI craft.'),
        skills=('svelte', 'frontend-design'),
        tools=('context7',),
        doc_namespaces=('svelte', 'sveltekit'),
    ),
    Route(
        patterns=('\\b(tailwind|tailwindcss|utility[- ]first|@theme|@apply|\\btw-)\\b',),
        hint=('Skill: load `tailwind` for Tailwind v4 (Oxide, CSS-first @theme config, responsive/container '
         'variants, @apply discipline); `css` for the language; `ux-ui` for token theory.'),
        skills=('tailwind', 'css', 'ux-ui'),
        tools=('context7',),
        doc_namespaces=('tailwind',),
    ),
    Route(
        patterns=('\\b(good interface|responsive layout|adaptive design|component architecture|web vitals|core web '
         'vitals|\\blcp\\b|\\binp\\b|\\bcls\\b|design system in code|progressive enhancement|frontend '
         'design|semantic html|html form|css layout|flexbox|css grid)\\b',
         '\\b(diseño|interfaz|interfaces de usuario|buena interfaz|c[oó]mo dise[ñn]ar|componente '
         'visual|layout)\\b'),
        hint=('Skill: load `frontend-design` for the craft of building good interfaces (component thinking, '
         'responsive/layout, design-system-in-code, web vitals, a11y) — framework-agnostic. Bases: '
         'html+css+javascript-pro; load `react`/`angular`/`vue`/`svelte` when the framework is known.'),
        skills=('frontend-design', 'html', 'css', 'javascript-pro'),
        priority=70,
    ),
    Route(
        patterns=('\\b(figma|pixel[- ]?perfect|dise[nñ]o figma|sync design|visual discrepancy|compara con '
         'figma|pantallazo|screenshot comparison|design fidelity)\\b',),
        hint=('Skill: load `figma-design-sync` or load `design-implementation-reviewer` or load '
         '`design-iterator` to compare, sync, and iteratively refine live web UI implementations against '
         'Figma designs.'),
        skills=('figma-design-sync', 'design-implementation-reviewer', 'design-iterator'),
    ),
    Route(
        patterns=('\\b(azure[- ]?foundry|ai[- ]?foundry|foundry[- ]?agent|prompt[- ]?optimizer|agent\\.yaml)\\b',
         '\\b(hosted[- ]?agent|container[- ]?agent|foundry[- ]?project|foundry[- ]?eval)\\b'),
        hint=('Skill: load `microsoft-foundry` for Azure AI Foundry — deploy/evaluate agents, prompt '
         'optimization, batch eval, dataset curation from traces, RBAC, and quota management. No direct '
         'deploy for general Azure resources.'),
        skills=('microsoft-foundry', 'azure-foundry-agents'),
        tools=('azure-mcp', 'context7'),
        doc_namespaces=('azure-ai-foundry', 'azure'),
        priority=78,
    ),
    Route(
        patterns=('\\b(copilot[- ]?studio|power[- ]?platform|copilot[- ]?agent|pac cli|solution\\.zip)\\b',
         '\\b(sharepoint[- ]?knowledge|dataverse|power[- ]?automate|virtual[- ]?agent)\\b'),
        hint=('Skill: load `copilot-studio` for Microsoft Copilot Studio and Power Platform CLI (pac) — manage '
         'AI agents, templates, solutions, and SharePoint knowledge sources.'),
        skills=('copilot-studio',),
        doc_namespaces=('copilot-studio', 'power-platform'),
    ),
    Route(
        patterns=('\\b(java|spring boot|springboot|jpa|hibernate|maven|gradle|@entity|@controller)\\b',
         '\\b(spring security|restcontroller|repository|service layer|dto|bean validation)\\b'),
        hint=('Skill: load `spring-boot-engineer` or `java-architect` for Spring Boot 3.x, `jpa-patterns` for '
         'query optimization, `java-code-review` for quality checks, and `security-audit` for OWASP '
         'validation.'),
        skills=('spring-boot-engineer', 'java-architect', 'jpa-patterns', 'java-code-review', 'security-audit'),
        tools=('context7',),
        doc_namespaces=('spring', 'spring-boot', 'java', 'hibernate'),
        priority=75,
    ),
    Route(
        patterns=('\\b(nestjs|nest\\.?js|@module|@controller|@injectable|typeorm|prisma|guard|interceptor)\\b',
         '\\b(dto|validationpipe|swagger|openapi|nestjs|nestjs-expert)\\b'),
        hint=('Skill: load `nestjs-expert` for NestJS modules, controllers, services, DTOs, guards, and '
         'TypeORM/Prisma integration; `typescript-pro` for advanced TS patterns; `api-contract-review` for '
         'REST design.'),
        skills=('nestjs-expert', 'typescript-pro', 'api-contract-review'),
        doc_namespaces=('nestjs',),
    ),
    Route(
        patterns=('\\b(typescript|\\.ts\\b|type guard|utility type|branded type|discriminated union|mapped type)\\b',
         '\\b(trpc|zod|strict mode|generics?|conditional type|infer keyword)\\b'),
        hint=('Skill: load `typescript-pro` for advanced type systems, custom type guards, utility types, and '
         'tRPC end-to-end type safety.'),
        skills=('typescript-pro',),
        doc_namespaces=('typescript',),
    ),
    Route(
        patterns=('\\b(azure[- ]?functions|function[- ]?app|httptrigger|timertrigger|blobtrigger)\\b',
         '\\b(local\\.settings\\.json|host\\.json|function_app|@function_name)\\b'),
        hint=('Skill: load `azure-functions` or `azure-functions-python` for triggers, bindings, local dev with '
         '`func start`, and deployment patterns. Deploy: pipeline by default; direct zip deploy only on '
         'explicit user opt-in.'),
        skills=('azure-functions', 'azure-functions-python'),
        tools=('azure-mcp', 'context7'),
        doc_namespaces=('azure-functions', 'azure'),
        priority=78,
    ),
    Route(
        patterns=('\\b(python|fastapi|sqlalchemy|pydantic|uvicorn|async def|pytest|mypy|ruff)\\b',
         '\\b(api rest python|backend python|python backend|fast api)\\b'),
        hint=('Skill: load `python-backend` for FastAPI, async patterns, SQLAlchemy, testing, and deployment; '
         '`python-pro` for general/modern Python (uv, ruff, mypy, types, async); `javascript-pro` for '
         'Node.js if mixing stacks.'),
        skills=('python-backend', 'python-pro', 'javascript-pro'),
        tools=('context7',),
        doc_namespaces=('python', 'fastapi', 'sqlalchemy', 'pydantic'),
        priority=70,
    ),
    Route(
        patterns=('\\.docx\\b|\\b(word document|documento word|\\.docx|python-docx|docx)\\b',),
        hint=('Skill: load `docx` for Word editing (paragraphs, tables, styles, find/replace) via python-docx; '
         'use `doc-convert` only for format conversion (md↔docx).'),
    ),
    Route(
        patterns=('\\b(hubspot|hub spot|crm|contactos?|deal[s]?|lead scoring|sales pipeline|workflow crm)\\b',
         '\\b(companies?|empresas?)\\b.*\\b(hubspot|crm)\\b'),
        hint=('Skill: load `hubspot` for CRM audits, contacts/companies/deals/lists, hygiene, enrichment, '
         'segmentation, and workflow automation.'),
        skills=('hubspot',),
        doc_namespaces=('hubspot',),
    ),
    Route(
        patterns=('\\b(dynamics?[- ]?365|dataverse|power platform|fetchxml|solution import|customizaci[oó]n '
         'dynamics)\\b',
         '\\b(early bound|late bound|plugin registration|web api odata)\\b'),
        hint=('Skill: load `dynamics-365` for Dataverse connection, security roles, FetchXML, metadata, data '
         'operations, and solution management.'),
        skills=('dynamics-365',),
        tools=('azure-mcp',),
        doc_namespaces=('dynamics-365', 'dataverse', 'power-platform'),
        priority=78,
    ),
    Route(
        patterns=('\\b(azure[- ]?devops|ado|azure[- ]?pipelines?|yaml pipeline|service connection|release '
         'pipeline)\\b',
         '\\b(AzureFunctionApp@|azure-pipelines\\.yml|agent pool|artifact)\\b'),
        hint=('Skill: load `azure-devops` for pipelines, service connections, agents, and Azure Functions '
         'deploy tasks. Deploy: default pipeline; explicit user zip-deploy opt-in OK (`az '
         'functionapp/webapp deploy --type zip`).'),
        skills=('azure-devops',),
        doc_namespaces=('azure-devops', 'azure-pipelines'),
    ),
    Route(
        patterns=('\\b(pull request|pr review|merge request|gh pr|gh issue|github cli|gh repo)\\b',
         '\\b(crea (un )?pr|abre (un )?pr|revisa el pr|cierra el issue)\\b'),
        hint=('GitHub: use `gh` CLI (skill `github-cli`) for PRs, issues, reviews, and repo ops. Prefer `gh` '
         'over manual git for platform actions.'),
        skills=('github-cli',),
        tools=('gh', 'git'),
    ),
    Route(
        patterns=('\\b(git worktree|worktree|isolated branch|paralelo|historial de git|git history|git '
         'blame|arqueolog[ií]a|commit msg|mensaje de commit|git commit)\\b',),
        hint=('Skill: load `git-worktree` for managing parallel worktrees, load `git-history-analyzer` to trace '
         'code history/blame, or load `git-commit` for generating conventional commits.'),
    ),
    Route(
        patterns=('\\b(security audit|vulnerabilidades|vulnerability|vulnerabilidad|security '
         'check|owasp|auditor[ií]a de seguridad|seguridad de c[oó]digo|secret leak|leak secrets)\\b',),
        hint=('Skill: load `security-audit` for code/app security review, input validation, auth risks, and '
         'OWASP checks; load `security-multi-cli-audit` for cross-CLI/MCP/hooks surface. Pair with '
         '`codescan sec`/`codescan secrets` before shipping.'),
        skills=('security-audit', 'security-multi-cli-audit'),
        tools=('codescan',),
        doc_namespaces=('owasp', 'security'),
        priority=82,
    ),
    Route(
        patterns=('\\b(openai|codex|chatgpt|responses api|agents sdk)\\b',),
        hint=('OpenAI docs: prefer `openaiDeveloperDocs` before web search; use the Codex `research` profile '
         'only when live web is needed.'),
        tools=('openaiDeveloperDocs',),
        doc_namespaces=('openai', 'codex'),
        priority=82,
    ),
    Route(
        patterns=('\\b(next\\.?js|react|tailwind|payload|supabase|postgres|fastapi|spring boot)\\b',
         '\\b(documentacion|documentation|docs|api reference|best practices)\\b'),
        hint=('Framework docs: use Context7 or official docs; avoid relying on stale model memory for current '
         'APIs.'),
        tools=('context7',),
        doc_namespaces=('framework-docs',),
        priority=78,
    ),
    Route(
        patterns=('\\b(implement|create|build|scaffold|generate)\\b.*\\b(function|class|module|component|test|file|endpoint)\\b',
         '\\b(write|run|execute)\\b.*\\b(unit test|tests for|scaffold|boilerplate)\\b',
         '\\b(migrate|convert)\\b.*\\b(\\bmodule|codebase|across|throughout|files?)\\b'),
        hint=('Bridge: `@codex-coder` (gpt-5.4) handles bounded code work; passes task via `cworker --mode '
         'codex-coding --write --write-scope "path" "task"`. Scoped writes only.'),
        workers=('codex-coder', 'cworker'),
        priority=70,
    ),
    Route(
        patterns=('\\b(analy[zs]e|lee|read|revis[ae]|examina)\\b.*\\b(entire|all of|whole|completo|todo '
         'el|repos?itorio)\\b',
         '\\b(these|estos|all)\\b.*\\b(files|archivos|logs?)\\b.*\\b(and|y|then)\\b.*\\b(summari[zs]e|resum[ei]|find|extrae)\\b',
         '\\b(1m|million|huge|gran|largo|completo)\\b.*\\b(context|token|file|repo)\\b'),
        hint=('Bridge: `@antigravity-longctx` (gemini-3.1-pro-preview, 1M context) handles whole-repo analysis; '
         'passes task via `cworker --mode agy3-pro`. Read-only.'),
        workers=('antigravity-longctx', 'agy3-pro'),
        priority=70,
    ),
    Route(
        patterns=('\\b(multi[- ]?file|cross[- '
         ']?file|several|many|varios)\\b.*\\b(refactor|edit|change|rewrite|migration)\\b',
         '\\b(worktree|isolated edit|opencode|multi[- ]?agent)\\b',
         '\\b(refactor|migrat|restructur)\\b.*\\b(across|throughout|module|system)\\b'),
        hint=('Bridge: `@opencode-multi` delegates multi-file refactors; passes task via `opencode run '
         '[message]`. Use when work spans 5+ files.'),
        workers=('opencode-multi', 'opencode'),
        priority=70,
    ),
    Route(
        patterns=('\\b(analiza bien|reason|reasoning|step by step|paso a paso|piensa antes|think through)\\b',
         '\\b(root cause|causa ra[ií]z|por qu[eé] falla|por que falla|debug|troubleshoot|investiga)\\b',
         '\\b(evaluate options|compare approaches|opciones|alternativas|tradeoffs|pros and cons)\\b'),
        hint=('Reasoning: invoke skill `structured-reasoning` first to decompose, hypothesize, or evaluate '
         'options before acting.'),
        skills=('structured-reasoning',),
        priority=80,
    ),
    Route(
        patterns=('\\b(TaskCreate|TaskUpdate|TaskList|TodoWrite|todo[_ -]?write|update_plan|ExitPlanMode|plan '
         'mode)\\b',
         '\\b(tareas?|task list|checklist|implementation guide|gu[ií]a de implementaci[oó]n|plan de '
         'trabajo|currentTask|objective registry)\\b',
         '\\b(no pierda el norte|mant[eé]n el foco|recupera el hilo|seguir como gu[ií]a)\\b'),
        hint=('Task guidance: load `task-native`. Claude uses native TaskCreate/TaskUpdate + ExitPlanMode '
         'bridge; Codex uses `update_plan`; durable cross-CLI pointer lives in '
         '`.memory-bank/currentTask.md` + `current-objective.json`.'),
        skills=('task-native',),
        priority=75,
    ),
    Route(
        patterns=('\\b(valida|verifica|revisa que est[eé] bien|check that|make sure|segunda vez|second check)\\b',
         '\\b(confirm|confirma|double[- ]?check|re[- ]?verify|sanity check|regression)\\b'),
        hint=('Validate: run the smallest verification first, inspect the diff, and read '
         '`.memory-bank/activeContext.md` + `progress.md` for verified state.'),
    ),
    Route(
        patterns=('\\b(continua|continue|retoma|resume|after compact|despu[eé]s de compactar|pick up)\\b',
         '\\b(donde quedamos|where were we|what was next|cu[aá]l es el siguiente paso)\\b'),
        hint=('Reflect/handoff: read `.memory-bank/activeContext.md` + `progress.md` first, then resume the '
         'next step.'),
        skills=('project-memory',),
        priority=75,
    ),
    Route(
        patterns=('\\b(prompt engineering|ingenier[ií]a de prompts|improve (this|the) prompt|system prompt|prompt '
         'template)\\b',
         '\\b(prompt pattern|few[- ]?shot|chain[- ]?of[- ]?thought|prompt optimi[sz]ation|debug agent '
         'behavior)\\b'),
        hint=('Skill: load `prompt-engineer` for prompt patterns (few-shot, CoT), frameworks '
         '(RTF/RISEN/RODES/Chain-of-Density), system-prompt design, and prompt optimization.'),
        skills=('prompt-engineer',),
    ),
    Route(
        patterns=('\\b(kubernetes|k8s|kubectl|pod|deployment|ingress|gateway api|helm manifest|kubeadm|metallb)\\b',),
        hint=('Skill: load `kubernetes` for manifests, Gateway API, autoscaling (HPA/KEDA), Pod Security, Helm, '
         'GitOps; load `k8s-self-hosted-ubuntu` for kubeadm, bare-metal CNI Calico/Flannel, MetalLB, NFS '
         'storage.'),
        skills=('kubernetes', 'k8s-self-hosted-ubuntu'),
        tools=('kubectl',),
        doc_namespaces=('kubernetes',),
    ),
    Route(
        patterns=('\\b(postgresql|postgres|psql|pgvector|rls policy|database index|b[- ]?tree|create index|explain '
         'analyze)\\b',),
        hint=('Skill: load `postgres` for PG17/18, indexing/EXPLAIN, RLS, pgvector, partitioning. '
         'Supabase-specific → `supabase-api`.'),
        skills=('postgres', 'supabase-api'),
        doc_namespaces=('postgres', 'supabase', 'pgvector'),
    ),
    Route(
        patterns=('\\b(claude code|claude-code|claude '
         'hooks|pretooluse|posttooluse|userpromptsubmit|sessionstart|precompact|subagent|settings\\.json|skill '
         'authoring)\\b',
         '\\b(codex config|codex agent|gpt-5|spawn_agents_on_csv)\\b'),
        hint=('Skill: load `claude-code` (hooks/skills/agents/plugins/MCP/settings) or `codex` (profiles, TOML '
         'agents, sandbox, multi-agent) for harness meta-questions.'),
        skills=('claude-code', 'codex'),
        doc_namespaces=('claude-code', 'codex'),
        priority=78,
    ),
    Route(
        patterns=('\\b(testing strategy|ci/?cd|code review|observability|definition of done|best practices)\\b',),
        hint=('Skill: load `software-development` for test pyramid, CI/CD, code review, observability, DoD, '
         'error handling, clean code/SRP.'),
        skills=('software-development',),
    ),
    Route(
        patterns=('\\b(rag|retrieval[- ]augmented|semantic search|vector db|embeddings|chunking|knowledge '
         'base|grounding)\\b',
         '\\b(machine learning|ml|model training|classification|regression|overfitting|feature '
         'engineering|pytorch|scikit-learn)\\b',
         '\\b(foundry agent|azure ai foundry|openai tools|function calling|responses api|agent\\.yaml)\\b'),
        hint=('Skill: load `rag` (retrieval/embeddings/vector stores/eval), `machine-learning` '
         '(workflow/metrics/overfitting), or `azure-foundry-agents` (Foundry hosted agents + OpenAI '
         'function-tool authoring).'),
        skills=('rag', 'machine-learning', 'azure-foundry-agents'),
        doc_namespaces=('rag', 'vector-search', 'azure-ai-foundry'),
        priority=78,
    ),
    Route(
        patterns=('\\b(node\\.?js|event loop|streams|npm|pnpm|package\\.json|worker_threads)\\b',),
        hint=('Skill: load `node-js` for the Node runtime/platform (event loop, streams, fs/http, '
         'worker_threads, npm/pnpm). Language syntax → javascript-pro; markup/a11y → frontend-design/html.'),
    ),
    Route(
        patterns=('\\b(clean code|single responsibility|refactor|maintainable|god object|code '
         'smell|simplifica|simplify|yagni)\\b',),
        hint=('Skill: load `clean-code` or load `code-simplicity-reviewer` or load `software-development` for '
         'clean code, SRP, simplicity, YAGNI, and maintainability.'),
    ),
    Route(
        patterns=('\\b(playwright|navegador|browser automation|abre (la )?(web|p[aá]gina)|inicia '
         'sesi[oó]n|login.*mfa|copilot[- ]?studio|scrape|web app test|e2e)\\b',
         '\\b(mcp__playwright|agent-browser|browser_snapshot|browser_click|browser_navigate)\\b'),
        hint=('Browser: snapshot-first (`browser_snapshot`/`agent-browser snapshot -i`), interact by `ref` not '
         'coordinates, screenshot only for visual/layout. Headed persistent `mcp__playwright__*` for '
         'Microsoft/MFA/Copilot Studio; `mcp__playwright-headless__*` or `agent-browser` for quick unauth '
         'checks. Rule: `rules/browser-automation.md`; skill: `playwright-mcp`.'),
        skills=('playwright-mcp', 'agent-browser'),
        tools=('playwright', 'playwright-headless'),
    ),
    Route(
        patterns=('n8n',
         '\\b(workflow n8n|n8n workflow|nodo n8n|n8n node|ejecuci[oó]n n8n|n8n execution)\\b',
         '\\b(\\{\\{\\$json\\}\\}|\\{\\{\\$node\\}\\}|mcp-n8n-builder|revopsgp\\.app\\.n8n)\\b'),
        hint=('n8n: MCP is read-only. Load `n8n-api` skill to query n8n cloud, inspect workflows, or debug '
         'failed executions via REST API. Edit workflow JSON locally and import manually.'),
        skills=('n8n-api',),
        tools=('n8n-workflow-builder',),
        doc_namespaces=('n8n',),
    ),
    Route(
        patterns=('\\b(xlsx?|csv|excel|spreadsheet|google[- ]?sheets?|gspread|openpyxl)\\b',),
        hint=('Skill: load `spreadsheet` for Excel, Google Sheets, CSV/Parquet operations, formulas, '
         'formatting, and pandas data analysis.'),
    ),
    Route(
        patterns=('\\b(pptx?|powerpoint|slides?|presentation|presentaci[oó]n)\\b',),
        hint=('Skill: load `presentation` or `pptx` or `pptx-official` for PowerPoint slide deck creation, '
         'layouts, templates, and python-pptx scripting.'),
    ),
    Route(
        patterns=('\\b(pdf|ocr|scanned document|extraer tablas pdf)\\b',),
        hint=('Skill: load `pdf-tools` or `pdf-ocr-feedback` for high-accuracy PDF text extraction, OCR '
         'consensus pipelines, and layout/table extraction. Unlimited OCR is PDF-only; standalone images '
         'should use native vision support or a vision-capable model/tool.'),
        skills=('pdf-tools', 'pdf-ocr-feedback'),
    ),
    Route(
        patterns=('\\b(rclone|s3|cloudflare r2|backblaze b2|google drive|dropbox|bucket|upload to cloud|subir a la '
         'nube)\\b',),
        hint=('Skill: load `rclone` to copy, sync, or backup files and media to cloud storage buckets (S3, R2, '
         'B2, Drive, Dropbox).'),
    ),
    Route(
        patterns=('\\b(dspy\\.rb|dspy-ruby|ruby l[lm]m|ruby agent)\\b',),
        hint='Skill: load `dspy-ruby` to build type-safe LLM applications and modules with DSPy.rb in Ruby.',
    ),
    Route(
        patterns=('\\b(reprodu(?:cir|ce)|bug reproduction|valida bug|bug report|reporte de bug)\\b',),
        hint=('Skill: load `bug-reproduction-validator` to systematically reproduce, diagnose, and confirm '
         'reported bugs before fixing them.'),
    ),
    Route(
        patterns=('\\b(trim|compact|compacta|compactar|contexto|memory bank|memoria)\\b',
         '\\b(continua|continue)\\b.*\\b(revisando|working|analizando)\\b'),
        hint=('Context hygiene: load `project-memory` for `.memory-bank/`; keep outputs concise, update '
         'decisions/progress, and prefer on-demand skills/MCP over dumping catalogs.'),
        skills=('project-memory',),
        priority=75,
    ),
]
