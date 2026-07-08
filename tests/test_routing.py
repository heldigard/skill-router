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


def test_route_table_split_preserves_route_count() -> None:
    assert len(ROUTES) == 59


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
    matches = match_routes("usa Antigravity CLI para analizar todo el repositorio con contexto largo")
    meta = collect_metadata(matches)

    assert "antigravity" in meta["skills"]
    assert "antigravity-longctx" in meta["workers"]


def test_wsl_prompt_routes_to_skill_and_docs() -> None:
    matches = match_routes("debug WSL2 WSLg Playwright systemd y .wslconfig")
    meta = collect_metadata(matches)

    assert "wsl" in meta["skills"]
    assert "microsoft-learn" in meta["doc_namespaces"]


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
