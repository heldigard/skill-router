"""Platform Cloud route definitions."""

from ..route import Route

PLATFORM_CLOUD_ROUTES: list[Route] = [
    Route(
        patterns=(
            "\\b(azure[- ]?foundry|ai[- ]?foundry|foundry[- ]?agent|prompt[- ]?optimizer|agent\\.yaml)\\b",
            "\\b(microsoft[- ]?foundry|hosted[- ]?agent|container[- ]?agent|foundry[- ]?project|foundry[- ]?eval)\\b",
            "\\b(azure|foundry)\\b.*\\b(reasoning summar(?:y|ies)|encrypted reasoning|agent trac(?:e|ing))\\b",
        ),
        hint=(
            "Skill: load `azure-foundry-agents` for Microsoft Foundry Agent Service, Responses API, reasoning "
            "summaries, hosted agents, eval/optimizer, tracing, RBAC, and quota-aware design. Use `azure-cli` "
            "for read-only Azure inventory when needed. Never request raw chain-of-thought or deploy without "
            "explicit authorization."
        ),
        skills=("azure-foundry-agents", "azure-cli"),
        tools=("azure-mcp", "context7"),
        doc_namespaces=("azure-ai-foundry", "azure"),
        # Domain-specific Foundry guidance must survive ahead of generic
        # "reasoning" and OpenAI-doc routes in the merged prompt budget.
        priority=92,
    ),
    Route(
        patterns=(
            "\\b(copilot[- ]?studio|power[- ]?platform|copilot[- ]?agent|pac cli|solution\\.zip)\\b",
            "\\b(sharepoint[- ]?knowledge|dataverse|power[- ]?automate|virtual[- ]?agent)\\b",
        ),
        hint=(
            "Skill: load `copilot-studio` for Microsoft Copilot Studio and Power Platform CLI (pac) — manage "
            "AI agents, templates, solutions, and SharePoint knowledge sources."
        ),
        skills=("copilot-studio",),
        doc_namespaces=("copilot-studio", "power-platform"),
    ),
    Route(
        patterns=(
            "\\b(java|spring boot|springboot|jpa|hibernate|maven|gradle|@entity|@controller)\\b",
            "\\b(spring security|restcontroller|repository|service layer|dto|bean validation)\\b",
            "\\b(thread safety|race condition|deadlock|virtual thread|completablefuture|concurrenc)\\b",
            "\\b(rabbitmq|spring amqp|@rabbitlistener|@async|slf4j|mdc)\\b",
        ),
        hint=(
            "Skill (Java/Spring): `spring-boot` is the version index → `spring-boot-engineer` (scaffold) or "
            "`spring-boot-patterns` (review: transactional boundaries, DI anti-patterns, idempotency, layering). "
            "Architecture: `java-architect`, `architecture-review`. Data/messaging: `jpa-patterns`, `rabbitmq`. "
            "Quality: `java-code-review`, `concurrency-review`, `logging-patterns`, `solid-principles`, "
            "`design-patterns`, `performance-smell-detection`, `test-quality`. Ops: `java-migration`, "
            "`maven-dependency-audit`. Security: `security-audit`."
        ),
        skills=(
            "spring-boot",
            "spring-boot-engineer",
            "spring-boot-patterns",
            "java-architect",
            "architecture-review",
            "jpa-patterns",
            "rabbitmq",
            "java-code-review",
            "concurrency-review",
            "logging-patterns",
            "solid-principles",
            "design-patterns",
            "performance-smell-detection",
            "test-quality",
            "java-migration",
            "maven-dependency-audit",
            "security-audit",
        ),
        tools=("context7",),
        doc_namespaces=("spring", "spring-boot", "java", "hibernate"),
        priority=75,
    ),
    Route(
        patterns=(
            "\\b(nestjs|nest\\.?js|@module|@controller|@injectable|typeorm|prisma|guard|interceptor)\\b",
            "\\b(dto|validationpipe|swagger|openapi|nestjs|nestjs-expert)\\b",
        ),
        hint=(
            "Skill: load `nestjs-expert` for NestJS modules, controllers, services, DTOs, guards, and "
            "TypeORM/Prisma integration; `typescript-pro` for advanced TS patterns; `api-contract-review` for "
            "REST design."
        ),
        skills=("nestjs-expert", "typescript-pro", "api-contract-review"),
        doc_namespaces=("nestjs",),
    ),
    Route(
        patterns=(
            "\\b(typescript|\\.ts\\b|type guard|utility type|branded type|discriminated union|mapped type)\\b",
            "\\b(trpc|zod|strict mode|generics?|conditional type|infer keyword)\\b",
        ),
        hint=(
            "Skill: load `typescript-pro` for advanced type systems, custom type guards, utility types, and "
            "tRPC end-to-end type safety."
        ),
        skills=("typescript-pro",),
        doc_namespaces=("typescript",),
    ),
    Route(
        patterns=(
            "\\b(azure[- ]?functions?|function[- ]?app|httptrigger|timertrigger|blobtrigger)\\b",
            "\\b(local\\.settings\\.json|host\\.json|function_app|@function_name)\\b",
        ),
        hint=(
            "Skill: load `azure-functions` or `azure-functions-python` for triggers, bindings, local dev with "
            "`func start`, and deployment patterns. Deploy: pipeline by default; direct zip deploy only on "
            "explicit user opt-in. Use the installed `azure-cli` skill for read-only resource operations; an "
            "`azure-mcp` server may assist only when the active caller actually exposes it."
        ),
        skills=("azure-functions", "azure-functions-python", "azure-cli"),
        tools=("azure-mcp", "context7"),
        doc_namespaces=("azure-functions", "azure"),
        # Prefer the concrete runtime route over generic Python/tooling hints.
        priority=90,
    ),
    Route(
        patterns=(
            "\\b(python|fastapi|sqlalchemy|pydantic|uvicorn|async def|pytest|mypy|ruff)\\b",
            "\\b(api rest python|backend python|python backend|fast api)\\b",
        ),
        hint=(
            "Skills: `python-backend` for FastAPI/SQLAlchemy/Pydantic/tests/deploy; "
            "`python-pro` for language/types/async/uv/Ruff/mypy. Use the separate "
            "Node.js route when JavaScript is explicit."
        ),
        skills=("python-backend", "python-pro"),
        tools=("context7",),
        doc_namespaces=("python", "fastapi", "sqlalchemy", "pydantic"),
        priority=70,
    ),
    Route(
        patterns=("\\.docx\\b|\\b(word document|documento word|\\.docx|python-docx|docx)\\b",),
        hint=(
            "Skill: load `docx` for Word editing (paragraphs, tables, styles, find/replace) via python-docx; "
            "use `doc-convert` only for format conversion (md↔docx)."
        ),
        skills=("docx", "doc-convert"),
    ),
    Route(
        patterns=(
            "\\b(hubspot|hub spot|crm|contactos?|deal[s]?|lead scoring|sales pipeline|workflow crm)\\b",
            "\\b(companies?|empresas?)\\b.*\\b(hubspot|crm)\\b",
        ),
        hint=(
            "Skill: load `hubspot` for CRM audits, contacts/companies/deals/lists, hygiene, enrichment, "
            "segmentation, and workflow automation."
        ),
        skills=("hubspot",),
        doc_namespaces=("hubspot",),
    ),
    Route(
        patterns=(
            "\\b(dynamics?[- ]?365|dataverse|power platform|fetchxml|solution import|customizaci[oó]n "
            "dynamics)\\b",
            "\\b(early bound|late bound|plugin registration|web api odata)\\b",
        ),
        hint=(
            "Skill: load `dynamics-365` for Dataverse connection, security roles, FetchXML, metadata, data "
            "operations, and solution management."
        ),
        skills=("dynamics-365",),
        tools=("azure-mcp",),
        doc_namespaces=("dynamics-365", "dataverse", "power-platform"),
        priority=78,
    ),
    Route(
        patterns=(
            "\\b(azure[- ]?devops|ado|azure[- ]?pipelines?|yaml pipeline|service connection|release "
            "pipeline)\\b",
            "\\b(AzureFunctionApp@|azure-pipelines\\.yml|agent pool|artifact)\\b",
        ),
        hint=(
            "Skill: load `azure-devops` for pipelines, service connections, agents, and Azure Functions "
            "deploy tasks. Deploy: default pipeline; explicit user zip-deploy opt-in OK (`az "
            "functionapp/webapp deploy --type zip`). For general Azure resource ops when `azure-mcp` is "
            "unavailable, fall back to the `azure-cli` skill (az + azmcp CLIs)."
        ),
        skills=("azure-devops", "azure-cli"),
        doc_namespaces=("azure-devops", "azure-pipelines"),
    ),
    Route(
        patterns=(
            "\\b(apollo\\.io|zoominfo|outbound prospecting|lead generation|find leads|firmographics|reveal (email|phone)|visitor id|reverse[- ]?ip|b2b (contacts|companies|leads)|lead enrichment|enrichment)\\b",
        ),
        hint=(
            "Skill: load `apollo-io` for outbound prospecting, finding leads/accounts, running sequences, "
            "OAuth, and syncing to HubSpot/Salesforce; load `zoominfo` for reverse-IP visitor ID (WebSights), "
            "intent, scoops/news, and bulk B2B contact/company enrichment."
        ),
        skills=("apollo-io", "zoominfo"),
        doc_namespaces=("apollo-io", "zoominfo"),
    ),
    Route(
        patterns=(
            "\\b(bicep|\\.bicep\\b|arm template|azure iac|infrastructure as code azure|"
            "az deployment (?:group|sub)|what-if deployment)\\b",
            "\\b(module\\s+'[^']+'\\s*:|param\\s+\\w+\\s+(string|int|bool|object|array))\\b",
        ),
        hint=(
            "Skill: load `azure-bicep` for Bicep modules, parameters, what-if, and pipeline-first deploys. "
            "App code deploy → `azure-functions`/`azure-devops`; resource inventory → `azure-cli`."
        ),
        skills=("azure-bicep", "azure-cli", "azure-devops", "azure-functions"),
        doc_namespaces=("azure-bicep", "azure"),
        priority=86,
    ),
    Route(
        patterns=(
            "\\b(ms[- ]?graph|microsoft graph|graph\\.microsoft\\.com|/me/messages|/users/|"
            "graph api|entra (?:id )?app registration graph)\\b",
            "\\b(outlook (?:mail|calendar) api|teams (?:chat|channel) api|onedrive graph)\\b",
        ),
        hint=(
            "Skill: load `ms-graph` for Microsoft Graph REST (mail, calendar, users, groups, files). "
            "Auth via Entra app + delegated/app permissions; never store tokens in skills. "
            "Copilot Studio agents → `copilot-studio`; Dataverse → `dynamics-365`."
        ),
        skills=("ms-graph", "copilot-studio", "dynamics-365"),
        doc_namespaces=("microsoft-graph", "entra"),
        priority=84,
    ),
    Route(
        patterns=(
            "\\b(android|kotlin|jetpack compose|@composable|compose ui|material3|material 3)\\b",
            "\\b(androidx|activity-compose|hilt viewmodel|room database|gradle\\.kts)\\b.*\\b(android|compose)\\b",
            "\\b(adb|android emulator|play console|aab|apk|navigation[- ]?3|edge[- ]to[- ]edge)\\b",
            "\\b(android studio|agp|android gradle plugin|baseline profile|r8 shrink)\\b",
            "\\b(camerax|wear compose|credential manager)\\b",
        ),
        hint=(
            "Skill: load `android-kotlin` hub for native Kotlin/Compose apps (architecture, Hilt, Room, "
            "Gradle). Depth: Chris Banes Compose/Kotlin skills (`compose-state-authoring`, "
            "`kotlin-coroutines-structured-concurrency`, …); Google specialists (`navigation-3`, "
            "`edge-to-edge`, `r8-analyzer`, `testing-setup`, `agp-9-upgrade`). Docs: Context7 android/"
            "jetpack-compose. SDK/adb may be missing on host until Android tools are installed."
        ),
        skills=(
            "android-kotlin",
            "using-chrisbanes-skills",
            "compose-state-authoring",
            "compose-recomposition-performance",
            "kotlin-coroutines-structured-concurrency",
            "kotlin-flow-state-event-modeling",
            "compose-ui-testing-patterns",
            "navigation-3",
            "edge-to-edge",
            "r8-analyzer",
            "testing-setup",
            "agp-9-upgrade",
            "android-compose-adaptive",
            "android-compose-styles",
            "android-intent-security",
            "android-cli",
        ),
        tools=("context7",),
        doc_namespaces=("android", "jetpack-compose", "kotlin"),
        priority=88,
    ),
]
