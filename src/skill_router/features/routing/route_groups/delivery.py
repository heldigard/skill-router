"""Delivery route definitions."""

from ..route import Route

DELIVERY_ROUTES: list[Route] = [
    Route(
        patterns=(
            "\\b(shepherd|babysit|monitor|poll|watch)\\b.*\\b(pr|prs|mr|mrs|pull requests?|merge requests?)\\b",
            "\\b(pr|prs|mr|mrs|pull requests?|merge requests?)\\b.*\\b(shepherd|babysit|monitor|poll|keep (it |them )?moving)\\b",
            "\\b(shepherd|babysit)\\b.*\\b(ci|review comments?|checks?)\\b",
        ),
        hint=(
            "PR babysit: load `shepherd` to poll open PRs/MRs, triage review comments, fix trivial CI, and keep "
            "the PR moving. Platform CLI ops stay on `github-cli` (`gh`/`glab`)."
        ),
        skills=("shepherd", "github-cli"),
        tools=("gh", "glab", "git"),
        priority=88,
    ),
    Route(
        patterns=(
            "\\b(implement|fix|resolve|work through)\\b.*\\b(issue|#\\d+|github issue|gitlab issue)\\b",
            "\\b(issue|#\\d+|github issue|gitlab issue)\\b.*\\b(implement|fix|resolve|work through)\\b",
            "\\b(implement[- ]?issue|/implement-issue)\\b",
            "\\b[\\w.-]+(?:/[\\w.-]+)+#\\d+\\b",
        ),
        hint=(
            "Issue workflow: load `implement-issue` for one GitHub/GitLab issue from read-only intake through "
            "branch completion (untrusted issue body). Pair with `github-cli` for forge ops and `issue-triage` "
            "only when categorizing a backlog, not a single actionable issue."
        ),
        skills=("implement-issue", "github-cli", "issue-triage"),
        tools=("gh", "glab", "git"),
        priority=88,
    ),
    Route(
        patterns=(
            "\\b(pull request|pr review|merge request|gh pr|gh issue|github cli|gh repo)\\b",
            "\\b(crea (un )?pr|abre (un )?pr|revisa el pr|cierra el issue)\\b",
            "\\b(triaj[ae]|triar|triage|categoriza(?:r)?)\\b.*\\b(issues?|backlog)\\b",
            "\\b(issues?|backlog)\\b.*\\b(triaj[ae]|triar|triage|categoriza(?:r)?)\\b",
        ),
        hint=(
            "GitHub: use `gh` CLI (skill `github-cli`) for PRs, issues, reviews, and repo ops. Prefer `gh` "
            "over manual git for platform actions. To triage/categorize the open-issue backlog with priority "
            "labels, load `issue-triage`. Single issue implementation → `implement-issue`; PR babysit loop → "
            "`shepherd`."
        ),
        skills=("github-cli", "issue-triage", "implement-issue", "shepherd"),
        tools=("gh", "glab", "git"),
    ),
    Route(
        patterns=(
            "\\b(git worktree|worktree|isolated branch|paralelo|historial de git|git history|git "
            "blame|arqueolog[ií]a|commit msg|mensaje de commit|git commit|atomic commit)\\b",
            "\\b(changelog|release notes|notas de (versi[oó]n|lanzamiento)|what changed since)\\b",
            "\\b(task done cleanup|antes de commitear|pre[- ]?commit cleanup|finaliza(r)? (la )?tarea)\\b",
            "\\b(crlf|lf|line endings|unix2dos|eol guard)\\b",
        ),
        hint=(
            "Skill: load `git-worktree` for parallel worktrees, `git-history-analyzer` to trace history/blame, "
            "`git-commit` to draft a conventional message, or `git-master` for atomic well-structured commits. "
            "Release notes/changelog from a commit range → `changelog-generator`; one-shot pre-commit cleanup "
            "(CRLF/LF noise, smart `git add -u`, summary-vs-diff) → `task-finalize`. Line endings CRLF/LF "
            "normalization → `git-eol-guard`."
        ),
        skills=(
            "git-worktree",
            "git-history-analyzer",
            "git-commit",
            "git-master",
            "changelog-generator",
            "task-finalize",
            "git-eol-guard",
        ),
        tools=("git",),
    ),
    Route(
        patterns=(
            "\\b(security audit|vulnerabilidades|vulnerability|vulnerabilidad|security "
            "check|owasp|auditor[ií]a de seguridad|seguridad de c[oó]digo|secret leak|leak secrets)\\b",
        ),
        hint=(
            "Skill: load `security-audit` for code/app security review, input validation, auth risks, and "
            "OWASP checks; load `security-multi-cli-audit` for cross-CLI/MCP/hooks surface. Pair with "
            "`codescan sec`/`codescan secrets` before shipping."
        ),
        skills=("security-audit", "security-multi-cli-audit"),
        tools=("codescan",),
        doc_namespaces=("owasp", "security"),
        priority=82,
    ),
    Route(
        patterns=("\\b(openai|codex|chatgpt|responses api|agents sdk)\\b",),
        hint=(
            "OpenAI docs: prefer `openaiDeveloperDocs` before web search; use the Codex `research` profile "
            "only when live web is needed."
        ),
        tools=("openaiDeveloperDocs",),
        doc_namespaces=("openai", "codex"),
        priority=82,
    ),
    Route(
        patterns=(
            "\\b(context7|mcp__context7|resolve-library-id|get-library-docs|library docs|current api "
            "docs|version-specific docs)\\b",
        ),
        hint=(
            "Skill: load `context7` when current library/framework docs, exact API signatures, or "
            "version-specific examples are needed. Use the Context7 MCP after resolving the library ID."
        ),
        skills=("context7",),
        tools=("context7",),
        doc_namespaces=("context7", "framework-docs"),
        priority=80,
    ),
    Route(
        patterns=(
            "\\b(next\\.?js|react|tailwind|payload|supabase|postgres|fastapi|spring boot)\\b.*\\b(documentacion|documentation|docs|api reference|best practices)\\b",
            "\\b(documentacion|documentation|docs|api reference|best practices)\\b.*\\b(next\\.?js|react|tailwind|payload|supabase|postgres|fastapi|spring boot)\\b",
        ),
        hint=(
            "Framework docs: use Context7 or official docs; avoid relying on stale model memory for current "
            "APIs."
        ),
        tools=("context7",),
        doc_namespaces=("framework-docs",),
        priority=78,
    ),
    Route(
        patterns=(
            "\\b(implement|create|build|scaffold|generate)\\b.*\\b(function|class|module|component|test|file|endpoint)\\b",
            "\\b(write|run|execute)\\b.*\\b(unit test|tests for|scaffold|boilerplate)\\b",
            "\\b(migrate|convert)\\b.*\\b(\\bmodule|codebase|across|throughout|files?)\\b",
        ),
        hint=(
            "Bridge: `@codex-coder` (GPT-5.6 Terra) handles bounded code work; passes task via `cworker --mode "
            'codex-coding --write --write-scope "path" "task"`. Scoped writes only.'
        ),
        workers=("codex-coder", "cworker"),
        priority=70,
    ),
    Route(
        patterns=(
            "\\b(analy[zs]e|lee|read|revis[ae]|examina)\\b.*\\b(entire|all of|whole|completo|todo "
            "el|repos?itorio)\\b",
            "\\b(these|estos|all)\\b.*\\b(files|archivos|logs?)\\b.*\\b(and|y|then)\\b.*\\b(summari[zs]e|resum[ei]|find|extrae)\\b",
            "\\b(1m|million|huge|gran|largo|completo)\\b.*\\b(context|token|file|repo)\\b",
        ),
        hint=(
            "Bridge: `@antigravity-longctx` (gemini-3.1-pro-preview, 1M context) handles whole-repo analysis; "
            "passes task via `cworker --mode agy3-pro`. Read-only."
        ),
        skills=("antigravity",),
        workers=("antigravity-longctx", "agy3-pro"),
        priority=70,
    ),
    Route(
        patterns=(
            "\\b(multi[- ]?file|cross[- "
            "]?file|several|many|varios)\\b.*\\b(refactor|edit|change|rewrite|migration)\\b",
            "\\b(worktree|isolated edit|opencode|multi[- ]?agent)\\b",
            "\\b(refactor|migrat|restructur)\\b.*\\b(across|throughout|module|system)\\b",
        ),
        hint=(
            "Bridge: `@opencode-multi` delegates multi-file refactors; passes task via `opencode run "
            "[message]`. Use when work spans 5+ files."
        ),
        workers=("opencode-multi", "opencode"),
        priority=70,
    ),
]
