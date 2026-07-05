"""Routing table: regex patterns -> hint text.

Migrated verbatim from the monolithic ~/.claude/hooks/prompt-router.py (429L).
Each entry is (patterns, hint). Patterns use re.IGNORECASE via _COMPILED in
command.py. Order matters: hints[:MAX_HINTS] takes the first matches.

To add a skill -> append one tuple. No control-flow to touch.

vs-soft-allow  — pure data table (regex -> hint). Cohesion intact: this file's
sole responsibility is "declare the routing table"; logic lives in command.py.
"""

from __future__ import annotations

ROUTES: list[tuple[list[str], str]] = [
    (
        [
            r"\b(swarm|multi[- ]?agent|varias opiniones|consenso|varios modelos)\b",
            r"\b(segunda opinion|segunda opinión|cross[- ]?check|multiple perspectives)\b",
            r"\b(ejecuta varios agentes|lanza swarm|agent team|equipo de agentes)\b",
            r"\b(worker|workers|delegar|delegaci[oó]n|modelo peque[nñ]o|modelo barato)\b",
        ],
        "Worker routing: for bounded side tasks, use `cworker`/`ai-delegate` (wrapper over codex-worker-router); keep default workers read-only, require `--write --write-scope` for edits, and reserve `swarm_run` for consensus or independent validation.",
    ),
    (
        [
            r"\b(investiga|research|latest|reciente|actual|mayo de 2026|today|hoy)\b",
            r"\b(busca en internet|web search|look up|novedades|tendencias)\b",
        ],
        "Research routing: use the `web-search`/`search-smart`/`web-reader` skills first (`web-research.py` local stack: SearXNG -> Firecrawl -> Z.AI/MiniMax fallback). Official docs/Context7 for product and framework facts. Perplexity/MiniMax MCPs are fallback only when the local stack is down or a deep cited research tool is explicitly needed.",
    ),
    (
        [
            r"\b(dead code|unused code|c[oó]digo muerto|sin usar|unused (func|import|var))\b",
            r"\b(security scan|escaneo de seguridad|vulnerab|sast|semgrep)\b",
            r"\b(secret leak|hardcoded (secret|key|token)|secretos|leaked (key|token))\b",
            r"\b(circular dep|layering violation|arch rule|dependency rule|import rule)\b",
            r"\b(revisa antes de (commit|push|ship)|antes de commitear|before (commit|shipping|push) (review|scan|check))\b",
        ],
        "Quality sensors (ship-time): run `codescan` (`dead`/`sec`/`secrets`/`arch`/`all`) — dead-code (vulture/knip), SAST (semgrep), leaked secrets (gitleaks), import-rule violations (dependency-cruiser). Normalized summary, vendor-excluded. Ref: rules/code-quality-sensors.md. (Edit-time facts → `codeq`.)",
    ),
    (
        [
            r"\b(documentaci[oó]n oficial|official docs|framework docs|best practices|buenas pr[aá]cticas|est[aá]ndar de la industria|industry standard|c[oó]mo se estructura|structure project)\b",
        ],
        "Skill: load `best-practices-researcher` or load `framework-docs-researcher` to gather industry standards, community conventions, or official library/framework documentation.",
    ),
    (
        [
            r"\b(payload|payloadcms|payload cms|payload\.config|collectionconfig)\b",
            r"\b(collections?|fields?|hooks?|access control)\b.*\b(payload|cms)\b",
        ],
        "Skill: load `payload` for Payload CMS 3.x configs, collections, fields, hooks, access control, Local API security, transactions, plugins, and Next.js integration.",
    ),
    (
        [
            r"\b(jenkins|jenkinsfile|jcasc|job dsl)\b",
            r"\b(declarative pipeline|scripted pipeline|shared librar(?:y|ies))\b",
        ],
        "Skill: load `jenkins` for Jenkinsfile, Declarative/Scripted Pipeline, shared libraries, JCasC, credentials safety, agents, plugins, and CI/CD troubleshooting.",
    ),
    (
        [
            r"\b(ag[- ]?grid|data grid|angular grid|celdas?|grid community)\b",
            r"\b(row group|tree data|master detail|excel export|cell renderer)\b.*\b(ag[- ]?grid|grid)\b",
        ],
        "Skill: load `ag-grid-community-angular` for AG Grid Community (free) patterns in Angular — setup v34+, themes, cell renderers, infinite scroll, and workarounds for tree-data, grouping, master/detail, Excel export, and clipboard without Enterprise license.",
    ),
    # Per-framework frontend dispatch (one skill per technology). Bases = html+css+js.
    (
        [
            r"\b(react|reactjs|\bjsx\b|\btsx\b|next\.?js|nextjs|server components?\b|usestate|useeffect|usememo|react compiler|use action state)\b"
        ],
        "Skill: load `react` for React 19 (hooks, Server Components, Actions, React Compiler, state, Next.js App Router); `frontend-design` for UI craft; `typescript-pro` for typed JSX.",
    ),
    (
        [
            r"\b(angular|ngfor|ngif|@component|@injectable|rxjs|signals?\b|angular cli|ng serve|ng build|standalone component|inject\(\)|providezoneless)\b"
        ],
        "Skill: load `angular` for Angular v19/v20 (standalone components, signals, zoneless, control flow @if/@for, inject(), RxJS, CLI); `frontend-design` for UI craft; `typescript-pro` for typed templates.",
    ),
    (
        [
            r"\b(vue|vuejs|vue\.js|script setup|composition api|composables?\b|pinia|nuxt|defineprops|defineemits)\b"
        ],
        "Skill: load `vue` for Vue 3.5 (Composition API, <script setup>, ref/reactive/computed/watch, composables, Pinia, Nuxt); `frontend-design` for UI craft.",
    ),
    (
        [r"\b(svelte|sveltekit|runes|\$state|\$derived|\$effect)\b"],
        "Skill: load `svelte` for Svelte 5 runes ($state/$derived/$effect, onclick, $props) + SvelteKit (load/form actions/SSR); `frontend-design` for UI craft.",
    ),
    (
        [r"\b(tailwind|tailwindcss|utility[- ]first|@theme|@apply|\btw-)\b"],
        "Skill: load `tailwind` for Tailwind v4 (Oxide, CSS-first @theme config, responsive/container variants, @apply discipline); `css` for the language; `ux-ui` for token theory.",
    ),
    # Framework-agnostic UI craft — the frontend entry point.
    (
        [
            r"\b(good interface|responsive layout|adaptive design|component architecture|web vitals|core web vitals|\blcp\b|\binp\b|\bcls\b|design system in code|progressive enhancement|frontend design|semantic html|html form|css layout|flexbox|css grid)\b",
            r"\b(diseño|interfaz|interfaces de usuario|buena interfaz|c[oó]mo dise[ñn]ar|componente visual|layout)\b",
        ],
        "Skill: load `frontend-design` for the craft of building good interfaces (component thinking, responsive/layout, design-system-in-code, web vitals, a11y) — framework-agnostic. Bases: html+css+javascript-pro; load `react`/`angular`/`vue`/`svelte` when the framework is known.",
    ),
    (
        [
            r"\b(figma|pixel[- ]?perfect|dise[nñ]o figma|sync design|visual discrepancy|compara con figma|pantallazo|screenshot comparison|design fidelity)\b"
        ],
        "Skill: load `figma-design-sync` or load `design-implementation-reviewer` or load `design-iterator` to compare, sync, and iteratively refine live web UI implementations against Figma designs.",
    ),
    (
        [
            r"\b(azure[- ]?foundry|ai[- ]?foundry|foundry[- ]?agent|prompt[- ]?optimizer|agent\.yaml)\b",
            r"\b(hosted[- ]?agent|container[- ]?agent|foundry[- ]?project|foundry[- ]?eval)\b",
        ],
        "Skill: load `microsoft-foundry` for Azure AI Foundry — deploy/evaluate agents, prompt optimization, batch eval, dataset curation from traces, RBAC, and quota management. No direct deploy for general Azure resources.",
    ),
    (
        [
            r"\b(copilot[- ]?studio|power[- ]?platform|copilot[- ]?agent|pac cli|solution\.zip)\b",
            r"\b(sharepoint[- ]?knowledge|dataverse|power[- ]?automate|virtual[- ]?agent)\b",
        ],
        "Skill: load `copilot-studio` for Microsoft Copilot Studio and Power Platform CLI (pac) — manage AI agents, templates, solutions, and SharePoint knowledge sources.",
    ),
    (
        [
            r"\b(java|spring boot|springboot|jpa|hibernate|maven|gradle|@entity|@controller)\b",
            r"\b(spring security|restcontroller|repository|service layer|dto|bean validation)\b",
        ],
        "Skill: load `spring-boot-engineer` or `java-architect` for Spring Boot 3.x, `jpa-patterns` for query optimization, `java-code-review` for quality checks, and `security-audit` for OWASP validation.",
    ),
    (
        [
            r"\b(nestjs|nest\.?js|@module|@controller|@injectable|typeorm|prisma|guard|interceptor)\b",
            r"\b(dto|validationpipe|swagger|openapi|nestjs|nestjs-expert)\b",
        ],
        "Skill: load `nestjs-expert` for NestJS modules, controllers, services, DTOs, guards, and TypeORM/Prisma integration; `typescript-pro` for advanced TS patterns; `api-contract-review` for REST design.",
    ),
    (
        [
            r"\b(typescript|\.ts\b|type guard|utility type|branded type|discriminated union|mapped type)\b",
            r"\b(trpc|zod|strict mode|generics?|conditional type|infer keyword)\b",
        ],
        "Skill: load `typescript-pro` for advanced type systems, custom type guards, utility types, and tRPC end-to-end type safety.",
    ),
    (
        [
            r"\b(azure[- ]?functions|function[- ]?app|httptrigger|timertrigger|blobtrigger)\b",
            r"\b(local\.settings\.json|host\.json|function_app|@function_name)\b",
        ],
        "Skill: load `azure-functions` or `azure-functions-python` for triggers, bindings, local dev with `func start`, and deployment patterns. Deploy: pipeline by default; direct zip deploy only on explicit user opt-in.",
    ),
    (
        [
            r"\b(python|fastapi|sqlalchemy|pydantic|uvicorn|async def|pytest|mypy|ruff)\b",
            r"\b(api rest python|backend python|python backend|fast api)\b",
        ],
        "Skill: load `python-backend` for FastAPI, async patterns, SQLAlchemy, testing, and deployment; `python-pro` for general/modern Python (uv, ruff, mypy, types, async); `javascript-pro` for Node.js if mixing stacks.",
    ),
    (
        [r"\.docx\b|\b(word document|documento word|\.docx|python-docx|docx)\b"],
        "Skill: load `docx` for Word editing (paragraphs, tables, styles, find/replace) via python-docx; use `doc-convert` only for format conversion (md↔docx).",
    ),
    (
        [
            r"\b(hubspot|hub spot|crm|contactos?|deal[s]?|lead scoring|sales pipeline|workflow crm)\b",
            r"\b(companies?|empresas?)\b.*\b(hubspot|crm)\b",
        ],
        "Skill: load `hubspot` for CRM audits, contacts/companies/deals/lists, hygiene, enrichment, segmentation, and workflow automation.",
    ),
    (
        [
            r"\b(dynamics?[- ]?365|dataverse|power platform|fetchxml|solution import|customizaci[oó]n dynamics)\b",
            r"\b(early bound|late bound|plugin registration|web api odata)\b",
        ],
        "Skill: load `dynamics-365` for Dataverse connection, security roles, FetchXML, metadata, data operations, and solution management.",
    ),
    (
        [
            r"\b(azure[- ]?devops|ado|azure[- ]?pipelines?|yaml pipeline|service connection|release pipeline)\b",
            r"\b(AzureFunctionApp@|azure-pipelines\.yml|agent pool|artifact)\b",
        ],
        "Skill: load `azure-devops` for pipelines, service connections, agents, and Azure Functions deploy tasks. Deploy: default pipeline; explicit user zip-deploy opt-in OK (`az functionapp/webapp deploy --type zip`).",
    ),
    (
        [
            r"\b(pull request|pr review|merge request|gh pr|gh issue|github cli|gh repo)\b",
            r"\b(crea (un )?pr|abre (un )?pr|revisa el pr|cierra el issue)\b",
        ],
        "GitHub: use `gh` CLI (skill `github-cli`) for PRs, issues, reviews, and repo ops. Prefer `gh` over manual git for platform actions.",
    ),
    (
        [
            r"\b(git worktree|worktree|isolated branch|paralelo|historial de git|git history|git blame|arqueolog[ií]a|commit msg|mensaje de commit|git commit)\b"
        ],
        "Skill: load `git-worktree` for managing parallel worktrees, load `git-history-analyzer` to trace code history/blame, or load `git-commit` for generating conventional commits.",
    ),
    (
        [
            r"\b(security audit|vulnerabilidades|vulnerability|vulnerabilidad|security check|owasp|auditor[ií]a de seguridad|seguridad de c[oó]digo|secret leak|leak secrets)\b"
        ],
        "Skill: load `security-audit` for code/app security review, input validation, auth risks, and OWASP checks; load `security-multi-cli-audit` for cross-CLI/MCP/hooks surface. Pair with `codescan sec`/`codescan secrets` before shipping.",
    ),
    (
        [r"\b(openai|codex|chatgpt|responses api|agents sdk)\b"],
        "OpenAI docs: prefer `openaiDeveloperDocs` before web search; use the Codex `research` profile only when live web is needed.",
    ),
    (
        [
            r"\b(next\.?js|react|tailwind|payload|supabase|postgres|fastapi|spring boot)\b",
            r"\b(documentacion|documentation|docs|api reference|best practices)\b",
        ],
        "Framework docs: use Context7 or official docs; avoid relying on stale model memory for current APIs.",
    ),
    # Cross-CLI bridge triggers (2026-06)
    (
        [
            r"\b(implement|create|build|scaffold|generate)\b.*\b(function|class|module|component|test|file|endpoint)\b",
            r"\b(write|run|execute)\b.*\b(unit test|tests for|scaffold|boilerplate)\b",
            r"\b(migrate|convert)\b.*\b(\bmodule|codebase|across|throughout|files?)\b",
        ],
        'Bridge: `@codex-coder` (gpt-5.4) handles bounded code work; passes task via `cworker --mode codex-coding --write --write-scope "path" "task"`. Scoped writes only.',
    ),
    (
        [
            r"\b(analy[zs]e|lee|read|revis[ae]|examina)\b.*\b(entire|all of|whole|completo|todo el|repos?itorio)\b",
            r"\b(these|estos|all)\b.*\b(files|archivos|logs?)\b.*\b(and|y|then)\b.*\b(summari[zs]e|resum[ei]|find|extrae)\b",
            r"\b(1m|million|huge|gran|largo|completo)\b.*\b(context|token|file|repo)\b",
        ],
        "Bridge: `@antigravity-longctx` (gemini-3.1-pro-preview, 1M context) handles whole-repo analysis; passes task via `cworker --mode agy3-pro`. Read-only.",
    ),
    (
        [
            r"\b(multi[- ]?file|cross[- ]?file|several|many|varios)\b.*\b(refactor|edit|change|rewrite|migration)\b",
            r"\b(worktree|isolated edit|opencode|multi[- ]?agent)\b",
            r"\b(refactor|migrat|restructur)\b.*\b(across|throughout|module|system)\b",
        ],
        "Bridge: `@opencode-multi` delegates multi-file refactors; passes task via `opencode run [message]`. Use when work spans 5+ files.",
    ),
    (
        [
            r"\b(analiza bien|reason|reasoning|step by step|paso a paso|piensa antes|think through)\b",
            r"\b(root cause|causa ra[ií]z|por qu[eé] falla|por que falla|debug|troubleshoot|investiga)\b",
            r"\b(evaluate options|compare approaches|opciones|alternativas|tradeoffs|pros and cons)\b",
        ],
        "Reasoning: invoke skill `structured-reasoning` first to decompose, hypothesize, or evaluate options before acting.",
    ),
    (
        [
            r"\b(TaskCreate|TaskUpdate|TaskList|TodoWrite|todo[_ -]?write|update_plan|ExitPlanMode|plan mode)\b",
            r"\b(tareas?|task list|checklist|implementation guide|gu[ií]a de implementaci[oó]n|plan de trabajo|currentTask|objective registry)\b",
            r"\b(no pierda el norte|mant[eé]n el foco|recupera el hilo|seguir como gu[ií]a)\b",
        ],
        "Task guidance: load `task-native`. Claude uses native TaskCreate/TaskUpdate + ExitPlanMode bridge; Codex uses `update_plan`; durable cross-CLI pointer lives in `.memory-bank/currentTask.md` + `current-objective.json`.",
    ),
    (
        [
            r"\b(valida|verifica|revisa que est[eé] bien|check that|make sure|segunda vez|second check)\b",
            r"\b(confirm|confirma|double[- ]?check|re[- ]?verify|sanity check|regression)\b",
        ],
        "Validate: run the smallest verification first, inspect the diff, and read `.memory-bank/activeContext.md` + `progress.md` for verified state.",
    ),
    (
        [
            r"\b(continua|continue|retoma|resume|after compact|despu[eé]s de compactar|pick up)\b",
            r"\b(donde quedamos|where were we|what was next|cu[aá]l es el siguiente paso)\b",
        ],
        "Reflect/handoff: read `.memory-bank/activeContext.md` + `progress.md` first, then resume the next step.",
    ),
    (
        [
            r"\b(prompt engineering|ingenier[ií]a de prompts|improve (this|the) prompt|system prompt|prompt template)\b",
            r"\b(prompt pattern|few[- ]?shot|chain[- ]?of[- ]?thought|prompt optimi[sz]ation|debug agent behavior)\b",
        ],
        "Skill: load `prompt-engineer` for prompt patterns (few-shot, CoT), frameworks (RTF/RISEN/RODES/Chain-of-Density), system-prompt design, and prompt optimization.",
    ),
    (
        [
            r"\b(kubernetes|k8s|kubectl|pod|deployment|ingress|gateway api|helm manifest|kubeadm|metallb)\b"
        ],
        "Skill: load `kubernetes` for manifests, Gateway API, autoscaling (HPA/KEDA), Pod Security, Helm, GitOps; load `k8s-self-hosted-ubuntu` for kubeadm, bare-metal CNI Calico/Flannel, MetalLB, NFS storage.",
    ),
    (
        [
            r"\b(postgresql|postgres|psql|pgvector|rls policy|database index|b[- ]?tree|create index|explain analyze)\b"
        ],
        "Skill: load `postgres` for PG17/18, indexing/EXPLAIN, RLS, pgvector, partitioning. Supabase-specific → `supabase-api`.",
    ),
    (
        [
            r"\b(claude code|claude-code|claude hooks|pretooluse|posttooluse|userpromptsubmit|sessionstart|precompact|subagent|settings\.json|skill authoring)\b",
            r"\b(codex config|codex agent|gpt-5|spawn_agents_on_csv)\b",
        ],
        "Skill: load `claude-code` (hooks/skills/agents/plugins/MCP/settings) or `codex` (profiles, TOML agents, sandbox, multi-agent) for harness meta-questions.",
    ),
    (
        [
            r"\b(testing strategy|ci/?cd|code review|observability|definition of done|best practices)\b"
        ],
        "Skill: load `software-development` for test pyramid, CI/CD, code review, observability, DoD, error handling, clean code/SRP.",
    ),
    (
        [
            r"\b(rag|retrieval[- ]augmented|semantic search|vector db|embeddings|chunking|knowledge base|grounding)\b",
            r"\b(machine learning|ml|model training|classification|regression|overfitting|feature engineering|pytorch|scikit-learn)\b",
            r"\b(foundry agent|azure ai foundry|openai tools|function calling|responses api|agent\.yaml)\b",
        ],
        "Skill: load `rag` (retrieval/embeddings/vector stores/eval), `machine-learning` (workflow/metrics/overfitting), or `azure-foundry-agents` (Foundry hosted agents + OpenAI function-tool authoring).",
    ),
    (
        [r"\b(node\.?js|event loop|streams|npm|pnpm|package\.json|worker_threads)\b"],
        "Skill: load `node-js` for the Node runtime/platform (event loop, streams, fs/http, worker_threads, npm/pnpm). Language syntax → javascript-pro; markup/a11y → frontend-design/html.",
    ),
    (
        [
            r"\b(clean code|single responsibility|refactor|maintainable|god object|code smell|simplifica|simplify|yagni)\b"
        ],
        "Skill: load `clean-code` or load `code-simplicity-reviewer` or load `software-development` for clean code, SRP, simplicity, YAGNI, and maintainability.",
    ),
    (
        [
            r"\b(playwright|navegador|browser automation|abre (la )?(web|p[aá]gina)|inicia sesi[oó]n|login.*mfa|copilot[- ]?studio|scrape|web app test|e2e)\b",
            r"\b(mcp__playwright|agent-browser|browser_snapshot|browser_click|browser_navigate)\b",
        ],
        "Browser: snapshot-first (`browser_snapshot`/`agent-browser snapshot -i`), interact by `ref` not coordinates, screenshot only for visual/layout. Headed persistent `mcp__playwright__*` for Microsoft/MFA/Copilot Studio; `mcp__playwright-headless__*` or `agent-browser` for quick unauth checks. Rule: `rules/browser-automation.md`; skill: `playwright-mcp`.",
    ),
    (
        [
            r"n8n",
            r"\b(workflow n8n|n8n workflow|nodo n8n|n8n node|ejecuci[oó]n n8n|n8n execution)\b",
            r"\b(\{\{\$json\}\}|\{\{\$node\}\}|mcp-n8n-builder|revopsgp\.app\.n8n)\b",
        ],
        "n8n: MCP is read-only. Load `n8n-api` skill to query n8n cloud, inspect workflows, or debug failed executions via REST API. Edit workflow JSON locally and import manually.",
    ),
    (
        [r"\b(xlsx?|csv|excel|spreadsheet|google[- ]?sheets?|gspread|openpyxl)\b"],
        "Skill: load `spreadsheet` for Excel, Google Sheets, CSV/Parquet operations, formulas, formatting, and pandas data analysis.",
    ),
    (
        [r"\b(pptx?|powerpoint|slides?|presentation|presentaci[oó]n)\b"],
        "Skill: load `presentation` or `pptx` or `pptx-official` for PowerPoint slide deck creation, layouts, templates, and python-pptx scripting.",
    ),
    (
        [r"\b(pdf|ocr|scanned document|extraer tablas pdf)\b"],
        "Skill: load `pdf-tools` or `pdf-ocr-feedback` for high-accuracy PDF text extraction, OCR consensus pipelines, and layout/table extraction. Unlimited OCR is PDF-only; standalone images should use native vision support or a vision-capable model/tool.",
    ),
    (
        [
            r"\b(rclone|s3|cloudflare r2|backblaze b2|google drive|dropbox|bucket|upload to cloud|subir a la nube)\b"
        ],
        "Skill: load `rclone` to copy, sync, or backup files and media to cloud storage buckets (S3, R2, B2, Drive, Dropbox).",
    ),
    (
        [r"\b(dspy\.rb|dspy-ruby|ruby l[lm]m|ruby agent)\b"],
        "Skill: load `dspy-ruby` to build type-safe LLM applications and modules with DSPy.rb in Ruby.",
    ),
    (
        [r"\b(reprodu(?:cir|ce)|bug reproduction|valida bug|bug report|reporte de bug)\b"],
        "Skill: load `bug-reproduction-validator` to systematically reproduce, diagnose, and confirm reported bugs before fixing them.",
    ),
    (
        [
            r"\b(trim|compact|compacta|compactar|contexto|memory bank|memoria)\b",
            r"\b(continua|continue)\b.*\b(revisando|working|analizando)\b",
        ],
        "Context hygiene: load `project-memory` for `.memory-bank/`; keep outputs concise, update decisions/progress, and prefer on-demand skills/MCP over dumping catalogs.",
    ),
]
