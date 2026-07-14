"""Tools Misc route definitions."""

from ..route import Route

TOOLS_MISC_ROUTES: list[Route] = [
    Route(
        patterns=("\\b(node\\.?js|event loop|streams|npm|pnpm|package\\.json|worker_threads)\\b",),
        hint=(
            "Skill: load `node-js` for the Node runtime/platform (event loop, streams, fs/http, "
            "worker_threads, npm/pnpm). Language syntax → javascript-pro; markup/a11y → frontend-design/html."
        ),
        skills=("node-js",),
        doc_namespaces=("nodejs",),
    ),
    Route(
        patterns=(
            "\\b(clean code|single responsibility|refactor|maintainable|god object|code "
            "smell|simplifica|simplify|yagni)\\b",
        ),
        hint=(
            "Skill: load `clean-code` or load `code-simplicity-reviewer` or load `software-development` for "
            "clean code, SRP, simplicity, YAGNI, and maintainability."
        ),
        skills=("clean-code", "code-simplicity-reviewer", "software-development"),
    ),
    Route(
        patterns=(
            "\\b(split (this|the|este|esa) (file|archivo|class|clase)|divide (esto|este|esa|this) "
            "(archivo|file|clase|class|monolith|monolito))\\b",
            "\\b(vertical[- ]?slice|split by feature|divide por (feature|caracter[ií]stica|dominio))\\b",
            "\\b(mucho c[oó]digo|too much code|monolith|god file|archivo muy (largo|grande)|(file|archivo) "
            "(too|very) (long|large))\\b",
            "\\b(reducir (tama[nñ]o|complejidad)|reduce (file )?size|extrae? (a|un) (archivo|file|m[oó]dulo|module))\\b",
            "\\b\\d{3,4}\\s?(LOC|lines|l[ií]neas)\\b",
        ),
        hint=(
            "Skill: load `vertical-slice-architect` to split an oversized or mixed-responsibility file into "
            "`features/<feature>/<use-case>/` folders — it produces a responsibility map → proposed structure → "
            "diff-ready split (one responsibility per folder, cohesion over size). Enforced at write time by the "
            "`vertical-slice-guard.py` PostToolUse hook; pair with `clean-code` for the underlying principles."
        ),
        skills=("vertical-slice-architect", "clean-code"),
    ),
    Route(
        patterns=(
            "\\b(playwright|navegador|browser automation|abre (la )?(web|p[aá]gina)|inicia "
            "sesi[oó]n|login.*mfa|copilot[- ]?studio|scrape|web app test|e2e)\\b",
            "\\b(mcp__playwright|agent-browser|browser_snapshot|browser_click|browser_navigate)\\b",
        ),
        hint=(
            "Browser: snapshot-first (`browser_snapshot`/`agent-browser snapshot -i`), interact by `ref` not "
            "coordinates, screenshot only for visual/layout. Headed persistent `mcp__playwright__*` for "
            "Microsoft/MFA/Copilot Studio; `mcp__playwright-headless__*` or `agent-browser` for quick unauth "
            "checks. To codify a repeatable flow as a deterministic CI spec, load `test-browser`; for one-off "
            "driving use `agent-browser`/`playwright-mcp`. Rule: `rules/browser-automation.md`."
        ),
        skills=("playwright-mcp", "agent-browser", "test-browser"),
        tools=("playwright", "playwright-headless"),
    ),
    Route(
        patterns=(
            "n8n",
            "\\b(workflow n8n|n8n workflow|nodo n8n|n8n node|ejecuci[oó]n n8n|n8n execution)\\b",
            "\\b(\\{\\{\\$json\\}\\}|\\{\\{\\$node\\}\\}|mcp-n8n-builder|revopsgp\\.app\\.n8n)\\b",
            "\\b(code node|n8n code|n8n expression|n8n sub[- ]?workflow|n8n agent|mcp agent)\\b",
        ),
        hint=(
            "n8n: cloud stays read-only por política — inspect/debug via `n8n-api` (REST GET; n8n MCPs "
            "retired from Claude/Codex/OpenCode; edit workflow JSON locally). For local authoring load the "
            "matching specialist: Code nodes → `n8n-code-javascript`/`n8n-code-python`; expressions `{{}}` → "
            "`n8n-expression-syntax`; node config → `n8n-node-configuration`; structure → "
            "`n8n-workflow-patterns`/`n8n-sub-workflows`; failures → `n8n-error-handling`/`n8n-validation-expert`; "
            "agents → `n8n-mcp-agents`."
        ),
        skills=(
            "n8n-api",
            "n8n-code-javascript",
            "n8n-code-python",
            "n8n-expression-syntax",
            "n8n-node-configuration",
            "n8n-workflow-patterns",
            "n8n-sub-workflows",
            "n8n-error-handling",
            "n8n-validation-expert",
            "n8n-mcp-tools-expert",
            "n8n-mcp-agents",
        ),
        doc_namespaces=("n8n",),
    ),
    Route(
        patterns=("\\b(xlsx?|csv|excel|spreadsheet|google[- ]?sheets?|gspread|openpyxl)\\b",),
        hint=(
            "Skill: load `spreadsheet` for Excel, Google Sheets, CSV/Parquet operations, formulas, "
            "formatting, and pandas data analysis."
        ),
        skills=("spreadsheet",),
    ),
    Route(
        patterns=("\\b(pptx?|powerpoint|slides?|presentation|presentaci[oó]n)\\b",),
        hint=(
            "Skill: load `presentation` or `pptx` or `pptx-official` for PowerPoint slide deck creation, "
            "layouts, templates, and python-pptx scripting."
        ),
        skills=("presentation", "pptx", "pptx-official"),
    ),
    Route(
        patterns=("\\b(pdf|ocr|scanned document|extraer tablas pdf)\\b",),
        hint=(
            "Skill: load `pdf-tools` (default extraction) or `pdf-ocr-feedback` (high-accuracy OCR consensus "
            "for degraded scans). When you need STRUCTURED FIELDS from a PDF (invoice/contact/PO/contract → "
            "validated JSON, schema-driven, abstention on absent fields) load `pdf-extract-structured`. "
            "Unlimited OCR is PDF-only; standalone images use native vision or a vision-capable model/tool."
        ),
        skills=("pdf-tools", "pdf-ocr-feedback", "pdf-extract-structured"),
    ),
    Route(
        patterns=(
            "\\b(rclone|s3|cloudflare r2|backblaze b2|google drive|dropbox|bucket|upload to cloud|subir a la "
            "nube)\\b",
        ),
        hint=(
            "Skill: load `rclone` to copy, sync, or backup files and media to cloud storage buckets (S3, R2, "
            "B2, Drive, Dropbox)."
        ),
        skills=("rclone",),
        tools=("rclone",),
    ),
    Route(
        patterns=("\\b(dspy\\.rb|dspy-ruby|ruby l[lm]m|ruby agent)\\b",),
        hint="Skill: load `dspy-ruby` to build type-safe LLM applications and modules with DSPy.rb in Ruby.",
        skills=("dspy-ruby",),
    ),
    Route(
        patterns=(
            "\\b(reprodu(?:cir|ce)|bug reproduction|valida bug|bug report|reporte de bug)\\b",
        ),
        hint=(
            "Skill: load `bug-reproduction-validator` to systematically reproduce, diagnose, and confirm "
            "reported bugs before fixing them."
        ),
        skills=("bug-reproduction-validator",),
    ),
    Route(
        patterns=(
            "\\b(minimax|mmx|generate (video|speech|music)|generar (video|voz|m[uú]sica|imagen|texto))\\b",
            "\\b(mmx[- ]?cli|minimax[- ]?cli)\\b",
        ),
        hint=(
            "Skill: load `mmx-cli` to generate text, images, video, speech, or music via the MiniMax (mmx) CLI."
        ),
        skills=("mmx-cli",),
    ),
    Route(
        patterns=(
            "\\b(trim|compact|compacta|compactar|contexto|memory bank|memoria)\\b",
            "\\b(continua|continue)\\b.*\\b(revisando|working|analizando)\\b",
        ),
        hint=(
            "Context hygiene: load `agent-memory` for `.memory-bank/`; keep outputs concise, update "
            "decisions/progress, and prefer on-demand skills/MCP over dumping catalogs."
        ),
        skills=("agent-memory",),
        priority=75,
    ),
]
