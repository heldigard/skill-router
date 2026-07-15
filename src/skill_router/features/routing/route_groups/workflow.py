"""Workflow route definitions."""

from ..route import Route

WORKFLOW_ROUTES: list[Route] = [
    Route(
        patterns=(
            "\\b(brainstorm(?:ing)?|lluvia de ideas|idear|ideaci[oó]n|generate ideas)\\b",
            "\\b(explore approaches|explorar enfoques|compare approaches|pros and cons|pros y contras)\\b",
            "\\b(design options|opciones de dise[nñ]o|discutir alternativas|think through.*(?:options|design|approach))\\b",
        ),
        hint=(
            "Brainstorming: load `brainstorming`. Let the brain frame and synthesize. Routine ambiguity stays "
            "native; use `fusion --preset subs` for cheap diverse alternatives, `fusion --preset intelligence` "
            "for consequential design, and one `cworker --min-intelligence ultra 'independent critique: ...'` "
            "for an orthogonal challenge. The panel advises; the brain decides."
        ),
        skills=("brainstorming",),
        tools=("fusion", "cworker"),
        priority=90,
    ),
    Route(
        patterns=(
            "\\b(analiza bien|reason|reasoning|step by step|paso a paso|piensa antes|think through)\\b",
            "\\b(root cause|causa ra[ií]z|por qu[eé] falla|por que falla|debug|troubleshoot|investiga)\\b",
            "\\b(evaluate options|opciones|alternativas|tradeoffs)\\b",
        ),
        hint=(
            "Reasoning: prefer native reasoning between tool calls; consult `structured-reasoning` "
            "templates only if an attempt already failed, requirements conflict, or the user asks for an "
            "explicit framework."
        ),
        skills=("structured-reasoning",),
        priority=80,
    ),
    Route(
        patterns=(
            "\\b(TaskCreate|TaskUpdate|TaskList|TodoWrite|todo[_ -]?write|update_plan|ExitPlanMode|plan "
            "mode)\\b",
            "\\b(tareas?|task list|checklist|implementation guide|gu[ií]a de implementaci[oó]n|plan de "
            "trabajo|currentTask|objective registry)\\b",
            "\\b(no pierda el norte|mant[eé]n el foco|recupera el hilo|seguir como gu[ií]a)\\b",
        ),
        hint=(
            "Task guidance: load `task-native`. Claude uses native TaskCreate/TaskUpdate + ExitPlanMode "
            "bridge; Codex uses `update_plan`; durable cross-CLI pointer lives in "
            "`.memory-bank/currentTask.md` + `current-objective.json`."
        ),
        skills=("task-native",),
        priority=75,
    ),
    Route(
        patterns=(
            "\\b(valida|verifica|revisa que est[eé] bien|check that|make sure|segunda vez|second check)\\b",
            "\\b(confirm|confirma|double[- ]?check|re[- ]?verify|sanity check|regression)\\b",
        ),
        hint=(
            "Validate: run the smallest verification first, inspect the diff, and read "
            "`.memory-bank/activeContext.md` + `progress.md` for verified state."
        ),
    ),
    Route(
        patterns=(
            "\\b(continua|continue|retoma|resume|after compact|despu[eé]s de compactar|pick up)\\b",
            "\\b(donde quedamos|where were we|what was next|cu[aá]l es el siguiente paso)\\b",
        ),
        hint=(
            "Reflect/handoff: read `.memory-bank/activeContext.md` + `progress.md` first, then resume the "
            "next step."
        ),
        skills=("agent-memory",),
        priority=75,
    ),
    Route(
        patterns=(
            "\\b(prompt engineering|ingenier[ií]a de prompts|improve (this|the) prompt|system prompt|prompt "
            "template)\\b",
            "\\b(prompt pattern|few[- ]?shot|chain[- ]?of[- ]?thought|prompt optimi[sz]ation|debug agent "
            "behavior)\\b",
        ),
        hint=(
            "Skill: load `prompt-engineer` for prompt patterns (few-shot, CoT), frameworks "
            "(RTF/RISEN/RODES/Chain-of-Density), system-prompt design, and prompt optimization."
        ),
        skills=("prompt-engineer",),
    ),
    Route(
        patterns=(
            "\\b(kubernetes|k8s|kubectl|pod|deployment|ingress|gateway api|helm manifest|kubeadm|metallb)\\b",
        ),
        hint=(
            "Skill: load `kubernetes` for manifests, Gateway API, autoscaling (HPA/KEDA), Pod Security, Helm, "
            "GitOps; load `k8s-self-hosted-ubuntu` for kubeadm, bare-metal CNI Calico/Flannel, MetalLB, NFS "
            "storage."
        ),
        skills=("kubernetes", "k8s-self-hosted-ubuntu"),
        tools=("kubectl",),
        doc_namespaces=("kubernetes",),
    ),
    Route(
        patterns=(
            "\\b(postgresql|postgres|psql|pgvector|rls policy|database index|b[- ]?tree|create index|explain "
            "analyze)\\b",
        ),
        hint=(
            "Skill: load `postgres` for PG17/18, indexing/EXPLAIN, RLS, pgvector, partitioning. "
            "Supabase-specific → `supabase-api`."
        ),
        skills=("postgres", "supabase-api"),
        doc_namespaces=("postgres", "supabase", "pgvector"),
    ),
    Route(
        patterns=(
            "\\b(claude code|claude-code|claude "
            "hooks|pretooluse|posttooluse|userpromptsubmit|sessionstart|precompact|subagent|settings\\.json|skill "
            "authoring)\\b",
            "\\b(codex config|codex agent|gpt-5|spawn_agents_on_csv)\\b",
        ),
        hint=(
            "Skill: load `claude-code` (hooks/skills/agents/plugins/MCP/settings) or `codex` (profiles, TOML "
            "agents, sandbox, multi-agent) for harness meta-questions."
        ),
        skills=("claude-code", "codex"),
        doc_namespaces=("claude-code", "codex"),
        priority=78,
    ),
    Route(
        patterns=(
            "\\b(antigravity|antigravity cli|google antigravity|agy3?-pro|gemini cli|agent-first "
            "coding|agent skills)\\b",
            "\\b(antigravity skills|antigravity hooks|antigravity plugins|antigravity artifacts)\\b",
        ),
        hint=(
            "Skill: load `antigravity` for Google Antigravity/CLI, agent skills, artifacts, long-context "
            "workers, and cross-CLI skill sync. Use `@antigravity-longctx`/`cworker --mode agy3-pro` only for "
            "bounded read-heavy repo analysis."
        ),
        skills=("antigravity",),
        workers=("antigravity-longctx", "agy3-pro"),
        doc_namespaces=("antigravity",),
        priority=78,
    ),
    Route(
        patterns=(
            "\\b(wsl|wsl2|wslg|windows subsystem for linux|\\.wslconfig|wsl\\.conf|wsl\\.exe|/mnt/c|/mnt/wslg)\\b",
            "\\b(systemd.*wsl|wsl.*systemd|wsl.*dns|wsl.*network|wsl.*docker|wsl.*gui|wsl.*playwright)\\b",
        ),
        hint=(
            "Skill: load `wsl` for WSL/WSL2/WSLg setup, `.wslconfig`, `wsl.conf`, systemd, networking, "
            "filesystem performance, GUI/browser automation, and Windows/Linux interop troubleshooting."
        ),
        skills=("wsl",),
        doc_namespaces=("wsl", "microsoft-learn"),
        priority=78,
    ),
    Route(
        patterns=(
            "\\b(testing strategy|ci/?cd|code review|observability|definition of done|best practices)\\b",
        ),
        hint=(
            "Skill: load `software-development` for test pyramid, CI/CD, code review, observability, DoD, "
            "error handling, clean code/SRP."
        ),
        skills=("software-development",),
    ),
    Route(
        patterns=(
            "\\b(rag|retrieval[- ]augmented|semantic search|vector db|embeddings|chunking|knowledge "
            "base|grounding)\\b",
            "\\b(machine learning|ml|model training|classification|regression|overfitting|feature "
            "engineering|pytorch|scikit-learn)\\b",
            "\\b(foundry agent|azure ai foundry|openai tools|function calling|responses api|agent\\.yaml)\\b",
        ),
        hint=(
            "Skill: load `rag` (retrieval/embeddings/vector stores/eval), `machine-learning` "
            "(workflow/metrics/overfitting), or `azure-foundry-agents` (Foundry hosted agents + OpenAI "
            "function-tool authoring)."
        ),
        skills=("rag", "machine-learning", "azure-foundry-agents"),
        doc_namespaces=("rag", "vector-search", "azure-ai-foundry"),
        priority=78,
    ),
    Route(
        patterns=(
            "\\b(fine[- ]?tun(?:e|ing|ed)(?:\\b.*\\b(?:model|llm|gpt|claude|dataset|lora))?|"
            "lora|qlora|supervised fine[- ]?tun)\\b",
            "\\b(?:llm|language model).*(?:\\beval\\w*|\\bquality|\\bbenchmark|\\bmetric)\\b",
            "\\bhallucination\\w* (?:detect\\w*|rate\\w*|check\\w*)\\b",
            "\\b(?:faithfulness|ragas|bertscore|llm[- ]as[- ]?judge|golden (?:set|eval\\w*))\\b",
            "\\b(?:model select\\w*|choose (?:a |the )?(?:llm|model)|model comparison|model tier|which "
            "(?:llm|model) (?:to use|should)|frontier vs (?:small|cheap|fast))\\b",
            "\\b(?:select|choose|pick|compar\\w*)\\b.*\\b(?:gpt|claude|llm|language model)\\b",
            "\\b(?:llm|language model).*(?:deploy|production|monitoring|cost|budget)\\b",
            "\\b(?:deploy|production).*(?:llm|chatbot|language model|ai agent)\\b",
            "\\b(?:gpt|claude|openai|gemini).*(?:deploy|production|cost|monitoring)\\b",
            "\\btoken (?:budget|optimi[sz]ation|cost)\\b",
            "\\bcontext window (?:manag\\w*|optimi[sz]ation)\\b",
            "\\brate limit.*\\bllm\\b|\\bllm.*guardrail\\b",
            "\\b(multi[- ]?model (?:rout\\w*|orchestrat\\w*|chain)|model cascade|model fallback|llm routing|tiered "
            "model)\\b",
        ),
        hint=(
            "Skill: load `llm-engineering` for the LLM application lifecycle — model selection "
            "(sections/model-selection.md), fine-tuning vs RAG vs prompts (sections/fine-tuning.md), "
            "evaluation and hallucination detection (sections/evaluation.md), production deployment "
            "with cost/guardrails (sections/production.md), context window management "
            "(sections/context-management.md), and multi-model orchestration (sections/multi-model.md). "
            "For Azure Foundry hosted agents → `azure-foundry-agents`; RAG pipeline → `rag`; "
            "prompt patterns → `prompt-engineer`."
        ),
        skills=("llm-engineering",),
        doc_namespaces=("openai", "azure-ai-foundry"),
        priority=77,
    ),
]
