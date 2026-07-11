"""Tools Misc route definitions."""

from ..route import Route

TOOLS_MISC_ROUTES: list[Route] = [
    Route(
        patterns=("\\b(node\\.?js|event loop|streams|npm|pnpm|package\\.json|worker_threads)\\b",),
        hint=(
            "Skill: load `node-js` for the Node runtime/platform (event loop, streams, fs/http, "
            "worker_threads, npm/pnpm). Language syntax → javascript-pro; markup/a11y → frontend-design/html."
        ),
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
            "checks. Rule: `rules/browser-automation.md`; skill: `playwright-mcp`."
        ),
        skills=("playwright-mcp", "agent-browser"),
        tools=("playwright", "playwright-headless"),
    ),
    Route(
        patterns=(
            "n8n",
            "\\b(workflow n8n|n8n workflow|nodo n8n|n8n node|ejecuci[oó]n n8n|n8n execution)\\b",
            "\\b(\\{\\{\\$json\\}\\}|\\{\\{\\$node\\}\\}|mcp-n8n-builder|revopsgp\\.app\\.n8n)\\b",
        ),
        hint=(
            "n8n: read-only por política. Load `n8n-api` skill to query n8n cloud, inspect workflows, or debug "
            "failed executions via REST API (GET only; n8n MCPs retired from Claude/Codex/OpenCode). "
            "Edit workflow JSON locally and import manually."
        ),
        skills=("n8n-api",),
        doc_namespaces=("n8n",),
    ),
    Route(
        patterns=("\\b(xlsx?|csv|excel|spreadsheet|google[- ]?sheets?|gspread|openpyxl)\\b",),
        hint=(
            "Skill: load `spreadsheet` for Excel, Google Sheets, CSV/Parquet operations, formulas, "
            "formatting, and pandas data analysis."
        ),
    ),
    Route(
        patterns=("\\b(pptx?|powerpoint|slides?|presentation|presentaci[oó]n)\\b",),
        hint=(
            "Skill: load `presentation` or `pptx` or `pptx-official` for PowerPoint slide deck creation, "
            "layouts, templates, and python-pptx scripting."
        ),
    ),
    Route(
        patterns=("\\b(pdf|ocr|scanned document|extraer tablas pdf)\\b",),
        hint=(
            "Skill: load `pdf-tools` or `pdf-ocr-feedback` for high-accuracy PDF text extraction, OCR "
            "consensus pipelines, and layout/table extraction. Unlimited OCR is PDF-only; standalone images "
            "should use native vision support or a vision-capable model/tool."
        ),
        skills=("pdf-tools", "pdf-ocr-feedback"),
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
    ),
    Route(
        patterns=("\\b(dspy\\.rb|dspy-ruby|ruby l[lm]m|ruby agent)\\b",),
        hint="Skill: load `dspy-ruby` to build type-safe LLM applications and modules with DSPy.rb in Ruby.",
    ),
    Route(
        patterns=(
            "\\b(reprodu(?:cir|ce)|bug reproduction|valida bug|bug report|reporte de bug)\\b",
        ),
        hint=(
            "Skill: load `bug-reproduction-validator` to systematically reproduce, diagnose, and confirm "
            "reported bugs before fixing them."
        ),
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
