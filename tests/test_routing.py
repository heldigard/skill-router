"""Tests for features/routing/command.py: hint matching + skip guards."""

from __future__ import annotations

from skill_router.features.routing.command import (
    collect_metadata,
    match_hints,
    match_routes,
    render_context,
    should_skip,
    skills_for_routes,
)
from skill_router.features.routing.routes import ROUTES


def test_match_hints_returns_skill_hint_for_angular_prompt() -> None:
    hints = match_hints("how do I write an Angular standalone component with signals?")
    assert any("angular" in h.lower() for h in hints)


def test_match_routes_caps_at_limit() -> None:
    # A prompt that triggers many routes still respects the limit.
    matches = match_routes("azure functions python spring boot angular", limit=2)
    assert len(matches) <= 2


def test_match_hints_no_match_returns_empty() -> None:
    assert match_hints("totally unrelated prompt about cooking pasta") == []


def test_should_skip_on_marker() -> None:
    assert should_skip("do thing [NO_DELEGATE]") is True


def test_should_skip_on_env() -> None:
    assert should_skip("anything", {"CODEX_WORKER": "1"}) is True


def test_should_skip_clean_prompt() -> None:
    assert should_skip("normal prompt", {}) is False


def test_render_context_wraps_hints() -> None:
    out = render_context(["hint A", "hint B"], {"doc_namespaces": ["angular", "spring"]})
    assert out.startswith("[Dynamic routing]")
    assert "- hint A" in out
    assert "- hint B" in out
    assert "angular, spring" in out
    assert len(out) < 220


def test_render_context_empty_returns_empty() -> None:
    assert render_context([]) == ""


def test_skills_for_routes_uses_structured_metadata() -> None:
    class FakeSkill:  # minimal stand-in
        def __init__(self, name: str) -> None:
            self.name = name

    catalog = [FakeSkill("angular"), FakeSkill("vue")]
    matches = match_routes("Angular signals standalone component")
    found = skills_for_routes(matches, catalog)  # type: ignore[arg-type]
    assert len(found) == 1
    assert found[0].name == "angular"


def test_collect_metadata_includes_docs_and_tools() -> None:
    matches = match_routes("Angular signals standalone component")
    meta = collect_metadata(matches)
    assert "angular" in meta["skills"]
    assert "context7" in meta["tools"]
    assert "angular" in meta["doc_namespaces"]


def test_brainstorming_routes_to_brain_skill_and_extra_hands() -> None:
    matches = match_routes("brainstorm design options and compare approaches")
    meta = collect_metadata(matches)
    assert "brainstorming" in meta["skills"]
    assert "fusion" in meta["tools"]
    assert "cworker" in meta["tools"]
    assert any("panel advises" in item.route.hint.lower() for item in matches)


def test_ecosystem_review_routes_to_fusion_and_codescan() -> None:
    matches = match_routes(
        "revisa este proyecto y mejora el ecosistema con segunda opinión de arquitectura; "
        "usa code facts antes de editar símbolos"
    )
    hints = [m.route.hint for m in matches]
    meta = collect_metadata(matches)

    assert any("Deliberation" in h for h in hints)
    assert any("Quality sensors" in h for h in hints)
    assert any("codescan capabilities" in h for h in hints)
    assert any("Code intelligence" in h for h in hints)
    assert "fusion-local" in meta["tools"]
    assert "codescan" in meta["tools"]
    assert "codeq" in meta["tools"]
    assert "code-intelligence" in meta["skills"]


def test_code_fact_prompt_routes_to_codeq_structured_payloads() -> None:
    matches = match_routes("find where this function is defined and inspect call sites")
    hints = [m.route.hint for m in matches]
    meta = collect_metadata(matches)

    assert any("--json capabilities" in h for h in hints)
    assert any("--json context" in h for h in hints)
    assert "codeq" in meta["tools"]
    assert "code-intelligence" in meta["skills"]


def test_natural_code_nav_prompts_route_to_codeq() -> None:
    """Intent-based patterns match natural code-nav prompts without literal category words."""
    prompts = [
        "where is authenticateUser defined",
        "what calls authenticateUser",
        "find all uses of processData",
        "show me the body of handleRequest",
        "definition of validateToken",
        "callers of parseInput",
    ]
    for prompt in prompts:
        matches = match_routes(prompt)
        meta = collect_metadata(matches)
        assert "codeq" in meta["tools"], f"prompt did not route to codeq: {prompt!r}"


def test_natural_review_prompts_route_to_codescan() -> None:
    """Intent-based patterns match natural review/ship prompts without sensor names."""
    prompts = [
        "review this diff before commit",
        "is there any dead code in src",
        "is this safe to ship",
    ]
    for prompt in prompts:
        matches = match_routes(prompt)
        meta = collect_metadata(matches)
        assert "codescan" in meta["tools"], f"prompt did not route to codescan: {prompt!r}"


def test_route_table_split_preserves_route_count() -> None:
    assert len(ROUTES) == 68


def test_route_table_uses_agent_memory_name_only() -> None:
    retired_name = "project" + "-memory"
    route_parts: list[str] = []
    for route in ROUTES:
        route_parts.extend(
            [
                route.hint,
                *route.skills,
                *route.tools,
                *route.workers,
                *route.doc_namespaces,
                *route.patterns,
            ]
        )
    route_text = "\n".join(route_parts)
    assert retired_name not in route_text
    assert "agent-memory" in route_text


def test_antigravity_prompt_routes_to_skill_and_worker() -> None:
    matches = match_routes(
        "usa Antigravity CLI para analizar todo el repositorio con contexto largo"
    )
    meta = collect_metadata(matches)

    assert "antigravity" in meta["skills"]
    assert "antigravity-longctx" in meta["workers"]


def test_context7_prompt_routes_to_skill_and_tool() -> None:
    matches = match_routes("usa Context7 para current API docs de Angular")
    meta = collect_metadata(matches)

    assert "context7" in meta["skills"]
    assert "context7" in meta["tools"]


def test_framework_docs_route_requires_framework_context() -> None:
    matches = match_routes("consulta docs y api reference")
    hints = [m.route.hint for m in matches]

    assert not any("Framework docs" in hint for hint in hints)

    matches = match_routes("consulta docs y api reference de FastAPI")
    hints = [m.route.hint for m in matches]

    assert any("Framework docs" in hint for hint in hints)


def _skills(prompt: str) -> set[str]:
    return set(collect_metadata(match_routes(prompt))["skills"])


def test_python_route_does_not_add_javascript_without_node_evidence() -> None:
    skills = _skills("debug this FastAPI endpoint with pytest")
    assert "python-backend" in skills
    assert "python-pro" in skills
    assert "javascript-pro" not in skills


def test_n8n_code_node_surfaces_code_specialists() -> None:
    """A matched n8n prompt surfaces the code-node family, not just n8n-api.

    Regression: the recommender does NOT run on matched prompts, so the route
    must declare the full n8n family or code-node authoring skills stay hidden.
    """
    skills = _skills("escribir codigo javascript en un code node de n8n")
    assert "n8n-api" in skills
    assert "n8n-code-javascript" in skills
    assert "n8n-expression-syntax" in skills
    assert "n8n-workflow-patterns" in skills


def test_spring_concurrency_surfaces_patterns_and_concurrency_review() -> None:
    """Matched spring-boot + concurrency prompt surfaces the review specialists."""
    skills = _skills("revisar transactional boundaries y thread safety en spring boot")
    assert "spring-boot-patterns" in skills
    assert "concurrency-review" in skills
    assert "spring-boot" in skills


def test_rabbitmq_prompt_surfaces_rabbitmq_skill() -> None:
    skills = _skills("configurar @RabbitListener con dead letter exchange en spring amqp")
    assert "rabbitmq" in skills


def test_angular_subskill_family_surfaces_on_angular_prompt() -> None:
    skills = _skills("configurar angular ssr con provideClientHydration e incremental hydration")
    assert "angular-ssr" in skills
    assert "angular-performance" in skills
    assert "angular-state-management" in skills


def test_browser_test_prompt_surfaces_test_browser() -> None:
    skills = _skills("escribir un test e2e con playwright para el login")
    assert "test-browser" in skills


def test_git_commit_prompt_surfaces_git_master() -> None:
    skills = _skills("haz un git commit atomico con mensaje convencional")
    assert "git-master" in skills


def test_vertical_slice_route_matches_split_file_intent() -> None:
    """New route: split-file/oversized-file intent lands on vertical-slice-architect."""
    skills = _skills("divide este archivo enorme en vertical slices por feature")
    assert "vertical-slice-architect" in skills


def test_worker_route_declares_delegation_guardrails() -> None:
    """subagent-cost-guard + orchestrator-supervisor ride the worker/delegation route."""
    skills = _skills("delegar una tarea acotada a un worker antes de correr codex-coder")
    assert "subagent-cost-guard" in skills
    assert "orchestrator-supervisor" in skills


def test_release_notes_prompt_surfaces_changelog_generator() -> None:
    skills = _skills("genera el changelog de los ultimos commits para la release")
    assert "changelog-generator" in skills


def test_issue_triage_prompt_surfaces_issue_triage() -> None:
    skills = _skills("triaja y categoriza los issues abiertos del backlog con prioridades")
    assert "issue-triage" in skills


def test_pdf_structured_extraction_surfaces_specialist() -> None:
    skills = _skills("extraer campos estructurados de facturas en pdf a json validado")
    assert "pdf-extract-structured" in skills


def test_azure_route_declares_azure_cli_fallback() -> None:
    skills = _skills("despliega y diagnostica azure functions con func")
    assert "azure-cli" in skills


def test_azure_route_accepts_singular_product_name() -> None:
    assert "azure-functions" in _skills("build an Azure Function in Python")


def test_foundry_route_uses_resolvable_canonical_skill_not_marketplace_tree() -> None:
    prompt = "Microsoft Foundry Responses API reasoning summaries and agent tracing"
    matches = match_routes(prompt)
    skills = _skills(prompt)
    assert "azure-foundry-agents" in skills
    assert "azure-cli" in skills
    assert "microsoft-foundry" not in skills
    assert "azure-foundry-agents" in matches[0].route.skills


def test_route_count_after_broadening_and_split_route() -> None:
    """Prior 67 + android-kotlin domain route = 68 (wsl retired 2026-07-18)."""
    assert len(ROUTES) == 68


def test_git_eol_guard_prompt_surfaces_git_eol_guard() -> None:
    skills = _skills("git commit failed due to CRLF LF mismatch")
    assert "git-eol-guard" in skills


def test_n8n_mcp_agents_prompt_surfaces_n8n_mcp_agents() -> None:
    skills = _skills("building an n8n agent with mcp tools")
    assert "n8n-mcp-agents" in skills


def test_b2b_prospecting_prompt_surfaces_apollo_and_zoominfo() -> None:
    skills = _skills("lead generation using apollo.io and zoominfo reverse-ip visitor id")
    assert "apollo-io" in skills
    assert "zoominfo" in skills


def test_minimax_media_prompt_routes_to_mmx_tool() -> None:
    metadata = collect_metadata(match_routes("generate speech or video using minimax mmx-cli"))
    assert "mmx" in metadata["tools"]
    assert "mmx-cli" not in metadata["skills"]


def test_new_tier1_skills_route() -> None:
    """docker-compose, agent-evals, ms-graph, azure-bicep, plan-grill, react-performance."""
    assert "docker-compose" in set(
        collect_metadata(match_routes("docker compose up healthcheck"))["skills"]
    )
    assert "agent-evals" in set(
        collect_metadata(match_routes("golden set agent eval harness"))["skills"]
    )
    assert "ms-graph" in set(
        collect_metadata(match_routes("microsoft graph /me/messages api"))["skills"]
    )
    assert "azure-bicep" in set(
        collect_metadata(match_routes("az deployment group what-if bicep"))["skills"]
    )
    assert "plan-grill" in set(
        collect_metadata(match_routes("grill me on this plan before coding"))["skills"]
    )
    assert "react-performance" in set(
        collect_metadata(match_routes("react request waterfall bundle size"))["skills"]
    )
    assert "browser-ollama-subagent" in set(
        collect_metadata(match_routes("playwright browser automation snapshot"))["skills"]
    )


def test_android_kotlin_routes() -> None:
    skills = set(
        collect_metadata(match_routes("Jetpack Compose @Composable Android Kotlin app"))["skills"]
    )
    assert "android-kotlin" in skills
    skills2 = set(collect_metadata(match_routes("migrate to Navigation 3 edge-to-edge"))["skills"])
    assert "android-kotlin" in skills2 or "navigation-3" in skills2
