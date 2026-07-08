"""Platform Cloud route definitions."""

from ..route import Route

PLATFORM_CLOUD_ROUTES: list[Route] = [
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
]
