"""Tests for the UserPromptSubmit hook entry (command.py).

Uses stdin injection via monkeypatch so the hook runs under controlled input.
"""

from __future__ import annotations

import io
import json

import pytest

from skill_router import command


def _run_hook_with_prompt(prompt: str, monkeypatch: pytest.MonkeyPatch) -> dict:
    payload = json.dumps({"prompt": prompt})
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    out_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", out_buf)
    command.main()
    return json.loads(out_buf.getvalue())


def test_hook_emits_continue_true_on_empty_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"prompt": ""})))
    out_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", out_buf)
    command.main()
    assert json.loads(out_buf.getvalue()) == {"continue": True}


def test_hook_emits_continue_true_on_skip_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    out = _run_hook_with_prompt("do thing [NO_DELEGATE]", monkeypatch)
    assert out == {"continue": True}


def test_hook_emits_context_on_skill_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    out = _run_hook_with_prompt("how to write Angular standalone component", monkeypatch)
    assert out["continue"] is True
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "[Dynamic routing]" in ctx
    assert "angular" in ctx.lower()


def test_analyze_caps_composed_hints() -> None:
    """Route, hidden-skill, and depth hints share one global prompt budget."""
    from skill_router.shared.config import MAX_HINTS

    result = command.analyze(
        "build a React TypeScript component for a FastAPI backend with n8n, "
        "Tailwind CSS, security review, and git commit",
        lexical_only=True,
    )
    assert len(result["hints"]) <= MAX_HINTS


def test_codex_hidden_foundry_skill_path_survives_hint_budget(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:  # type: ignore[no-untyped-def]
    from skill_router.shared.skill_io import clear_catalog_cache

    foundry_dir = fake_claude_home / "skills" / "azure-foundry-agents"
    foundry_dir.mkdir()
    foundry_skill = foundry_dir / "SKILL.md"
    foundry_skill.write_text(
        "---\nname: azure-foundry-agents\n"
        'description: "Microsoft Foundry agents, Responses API, reasoning summaries, and traces."\n'
        "---\n# Foundry\n",
        encoding="utf-8",
    )
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    (codex_home / "config.toml").write_text(
        f'[[skills.config]]\npath = "{foundry_skill}"\nenabled = false\n'
        "[mcp_servers.context7]\nurl = 'https://example.invalid'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CLI_ORCHESTRATION_CALLER", "codex")
    clear_catalog_cache()

    result = command.analyze(
        "Microsoft Foundry Responses API reasoning summaries, traces, and RAG",
        lexical_only=True,
    )
    assert str(foundry_skill) in result["hints"][0]
    assert "microsoft-foundry" not in result["context"]
    assert "azure-mcp" not in result["metadata"]["tools"]


def test_cosmos_rag_skill_path_survives_hint_budget(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:  # type: ignore[no-untyped-def]
    from skill_router.shared.skill_io import clear_catalog_cache

    cosmos_dir = fake_claude_home / "skills" / "azure-cosmos-rag"
    cosmos_dir.mkdir()
    cosmos_skill = cosmos_dir / "SKILL.md"
    cosmos_skill.write_text(
        "---\nname: azure-cosmos-rag\n"
        'description: "Azure Cosmos DB vector RAG knowledge bases for Foundry agents."\n'
        "---\n# Cosmos RAG\n",
        encoding="utf-8",
    )
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    (codex_home / "config.toml").write_text(
        f'[[skills.config]]\npath = "{cosmos_skill}"\nenabled = false\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CLI_ORCHESTRATION_CALLER", "codex")
    clear_catalog_cache()

    result = command.analyze(
        "ground a Foundry chatbot knowledge base with Cosmos DB vector search",
        lexical_only=True,
    )
    assert str(cosmos_skill) in result["hints"][0]
    assert "azure-cosmos-rag" in result["metadata"]["skills"]


def test_hidden_semantic_recommendations_are_codex_only(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:  # type: ignore[no-untyped-def]
    from skill_router.features.recommend.command import Recommendation

    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    hidden = fake_claude_home / "skills" / "alpha" / "SKILL.md"
    (codex_home / "config.toml").write_text(
        f'[[skills.config]]\npath = "{hidden}"\nenabled = false\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CLI_ORCHESTRATION_CALLER", "codex")
    monkeypatch.setattr(
        "skill_router.features.recommend.command.recommend",
        lambda *_args, **_kwargs: [
            Recommendation("alpha", 0.8, "semantic match cos=0.80", "semantic")
        ],
    )
    hints = command._codex_hidden_recommendation_hints("review code", set())
    assert len(hints) == 1
    assert "alpha" in hints[0]
    assert str(hidden) in hints[0]


def test_hidden_recommendations_drop_weak_lexical_overlap(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:  # type: ignore[no-untyped-def]
    from skill_router.features.recommend.command import Recommendation

    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    hidden = fake_claude_home / "skills" / "alpha" / "SKILL.md"
    (codex_home / "config.toml").write_text(
        f'[[skills.config]]\npath = "{hidden}"\nenabled = false\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CLI_ORCHESTRATION_CALLER", "codex")
    monkeypatch.setattr(
        "skill_router.features.recommend.command.recommend",
        lambda *_args, **_kwargs: [
            Recommendation("alpha", 0.14, "lexical match jaccard=0.14", "lexical")
        ],
    )

    assert command._codex_hidden_recommendation_hints("generic API query", set()) == []


def test_hook_emits_continue_true_on_unmatched(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A prompt with no regex route and no semantic/lexical skill match stays clean."""
    from skill_router.shared import embed as embed_mod
    from skill_router.shared.skill_io import clear_catalog_cache

    clear_catalog_cache()
    # Ollama down → recommender uses lexical fallback; "cooking pasta" shares no
    # tokens with alpha/beta/gamma in the isolated catalog → stays unmatched.
    monkeypatch.setattr(embed_mod, "is_alive", lambda: False)
    out = _run_hook_with_prompt("cooking pasta recipe", monkeypatch)
    assert out == {"continue": True}


def test_hook_emits_recommendation_when_regex_misses_but_semantic_hits(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No regex route matches, but the semantic recommender surfaces a skill."""
    from skill_router.shared import embed as embed_mod
    from skill_router.shared.skill_io import clear_catalog_cache

    clear_catalog_cache()
    monkeypatch.setattr(embed_mod, "is_alive", lambda: True)

    def fake_embed(text: str, **_kwargs: object) -> list[float]:
        # "acme widgets" prompt collides with the alpha description by design.
        import re

        def bow(t: str) -> list[float]:
            vec = [0.0] * 64
            for w in re.findall(r"[a-z0-9]{3,}", t.lower()):
                vec[sum(ord(c) for c in w) % 64] = 1.0
            return vec

        return bow(text)

    monkeypatch.setattr(embed_mod, "embed", fake_embed)
    out = _run_hook_with_prompt("acme widgets gadget", monkeypatch)
    assert out["continue"] is True
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "[Dynamic routing]" in ctx
    assert "alpha" in ctx.lower()


def test_concrete_file_prompt_skips_semantic_rescue(monkeypatch: pytest.MonkeyPatch) -> None:
    """Precise file edits should not pay for weak catalog-wide embeddings."""
    monkeypatch.setattr(
        "skill_router.features.recommend.command.recommend",
        lambda *_args, **_kwargs: pytest.fail("semantic recommender must stay cold"),
    )
    assert command._recommendation_hints("fix parser.py and run tests", []) == []


def test_hook_fails_open_on_internal_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the catalog import breaks, the hook must still return continue:true."""
    import skill_router.features.routing.command as routing

    def boom(*_a, **_k):  # noqa: ANN002
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(routing, "match_routes", boom)
    out = _run_hook_with_prompt("Angular components", monkeypatch)
    # Should fail open — either continue:true (caught in main) or via stderr.
    assert out.get("continue") is True or "hookSpecificOutput" in out


def test_load_prompt_handles_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert command.load_prompt() == ""


def test_hook_includes_lexical_depth_selection_by_default(
    fake_claude_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from skill_router.shared.skill_io import clear_catalog_cache

    # Write jpa-patterns skill with sections
    sk_dir = fake_claude_home / "skills" / "jpa-patterns"
    sk_dir.mkdir(parents=True, exist_ok=True)
    fm = (
        "---\n"
        "name: jpa-patterns\n"
        'description: "JPA Patterns skill."\n'
        "sections:\n"
        "  - lazy-loading: Lazy Loading\n"
        "  - transactions: Transactions\n"
        "---\n\n"
        "# JPA Patterns\n"
    )
    (sk_dir / "SKILL.md").write_text(fm)
    secs = sk_dir / "sections"
    secs.mkdir(exist_ok=True)
    (secs / "lazy-loading.md").write_text("# lazy-loading\n\nSection body for lazy-loading.\n")
    (secs / "transactions.md").write_text("# transactions\n\nSection body for transactions.\n")
    clear_catalog_cache()

    # Prompt matches jpa-patterns route and "lazy loading" section
    out = _run_hook_with_prompt("how to optimize lazy loading in jpa-patterns", monkeypatch)
    assert out["continue"] is True
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "Depth: `jpa-patterns`" in ctx
    assert "sections/lazy-loading.md" in ctx


def test_assemble_hints_dedupes_exact_duplicates() -> None:
    """Same hint text from multiple matches should consume one budget slot."""
    from skill_router.command import HintInputs, _assemble_hints
    from skill_router.features.routing.command import MatchedRoute
    from skill_router.features.routing.route import Route

    shared_hint = "Use codeq to find references before editing."
    route = Route(patterns=(r"\\bcache\\b",), hint=shared_hint)
    matches = [MatchedRoute(index=0, route=route), MatchedRoute(index=1, route=route)]
    out = _assemble_hints(
        prompt="cache helper",
        inputs=HintInputs(
            matches=matches,
            availability_hints=[],
            exclude_skills=set(),
        ),
        depth_decisions=[],
        limit=5,
    )
    assert out.count(shared_hint) == 1
    assert len(out) == 1


def test_assemble_hints_preserves_distinct_phrasings() -> None:
    """Distinct hint strings must not collapse; only exact duplicates dedupe."""
    from skill_router.command import HintInputs, _assemble_hints
    from skill_router.features.routing.command import MatchedRoute
    from skill_router.features.routing.route import Route

    r1 = Route(patterns=(r"\\bangular\\b",), hint="Use Angular signals.")
    r2 = Route(
        patterns=(r"\\bangular standalone\\b",), hint="Use Angular signals + standalone bootstrap."
    )
    matches = [MatchedRoute(0, r1), MatchedRoute(1, r2)]
    out = _assemble_hints(
        prompt="angular standalone",
        inputs=HintInputs(matches=matches, availability_hints=[], exclude_skills=set()),
        depth_decisions=[],
        limit=5,
    )
    assert len(out) == 2


def test_max_hints_default_is_five() -> None:
    import os

    os.environ.pop("SKILL_ROUTER_MAX_HINTS", None)
    os.environ.pop("CLI_ORCHESTRATION_CALLER", None)
    from skill_router.shared.config import max_hints

    assert max_hints() == 5


def test_max_hints_codex_default_is_four() -> None:
    import os

    os.environ["CLI_ORCHESTRATION_CALLER"] = "codex"
    os.environ.pop("SKILL_ROUTER_MAX_HINTS_CODEX", None)
    from skill_router.shared.config import max_hints

    assert max_hints() == 4
    del os.environ["CLI_ORCHESTRATION_CALLER"]


def test_max_hints_env_override_wins() -> None:
    import os

    os.environ["SKILL_ROUTER_MAX_HINTS"] = "7"
    from skill_router.shared.config import max_hints

    assert max_hints() == 7
    del os.environ["SKILL_ROUTER_MAX_HINTS"]


def test_paths_claude_home_ignores_codex_home(monkeypatch) -> None:
    """claude_home() must NOT fall back to CODEX_HOME — both may be set
    simultaneously (Codex hooks inherit both); falling back would redirect
    skills_root() to ~/.codex/skills instead of the canonical ~/.claude/skills.
    """
    monkeypatch.delenv("CLAUDE_HOME", raising=False)
    monkeypatch.setenv("CODEX_HOME", "/tmp/fake-codex")
    monkeypatch.setenv("HOME", "/tmp/fake-home")
    from skill_router.shared.paths import claude_home

    assert str(claude_home()) == "/tmp/fake-home/.claude"


def test_paths_codex_home_default(monkeypatch) -> None:
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setenv("HOME", "/tmp/fake-home")
    from skill_router.shared.paths import codex_home

    assert str(codex_home()) == "/tmp/fake-home/.codex"
