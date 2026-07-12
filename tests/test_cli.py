"""Tests for the unified CLI (cli.py).

Exercises each subcommand by invoking cli.main() with a patched argv and
capturing stdout. Uses the fake_claude_home fixture so catalog/audit run
against a controlled temp catalog. classify/depth stub their LLM/embedding
backends so no network is needed.
"""

from __future__ import annotations

import io
import json

import pytest

from skill_router import cli


def _run(argv: list[str], monkeypatch: pytest.MonkeyPatch) -> tuple[int, str]:
    """Invoke cli.main(argv); return (exit_code, stdout_text)."""
    monkeypatch.setattr("sys.argv", ["skill-router"] + argv)
    out = io.StringIO()
    err = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    monkeypatch.setattr("sys.stderr", err)
    rc = cli.main()
    return rc, out.getvalue()


def test_cli_no_subcommand_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    # argparse with required=True subparsers exits 2 on missing subcommand.
    with pytest.raises(SystemExit) as exc:
        _run([], monkeypatch)
    assert exc.value.code == 2


def test_cli_version(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit) as exc:
        _run(["--version"], monkeypatch)
    assert exc.value.code == 0


def test_cli_route_unmatched_prompt(fake_claude_home, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    # Prompt that matches no route -> "(no hints matched)".
    rc, out = _run(["route", "--prompt", "cooking pasta recipe"], monkeypatch)
    assert rc == 0
    assert "no hints matched" in out.lower() or out.strip() == ""


def test_cli_route_unmatched_explains_coverage_gap(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    rc, out = _run(["route", "--prompt", "cooking pasta recipe", "--explain"], monkeypatch)
    assert rc == 0
    assert "status=unmatched" in out
    assert "no route pattern matched" in out


def test_cli_route_json_shape(fake_claude_home, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    # Use a prompt that triggers a route; none of the fake skills are multi-level
    # and referenced in hints, so depth_decisions stays empty but the key exists.
    rc, out = _run(["route", "--prompt", "angular standalone component", "--json"], monkeypatch)
    assert rc == 0
    payload = json.loads(out)
    assert "hints" in payload
    assert "depth_decisions" in payload
    assert "context" in payload
    assert payload["decision"]["status"] == "matched"
    assert isinstance(payload["hints"], list)


def test_cli_route_json_distinguishes_skip_from_unmatched(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    _, skipped_out = _run(
        ["route", "--prompt", "review angular [NO_DELEGATE]", "--json"], monkeypatch
    )
    _, unmatched_out = _run(["route", "--prompt", "cooking pasta recipe", "--json"], monkeypatch)
    assert json.loads(skipped_out)["decision"]["status"] == "skipped"
    assert json.loads(unmatched_out)["decision"]["status"] == "unmatched"


def test_cli_route_empty_prompt_errors(fake_claude_home, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    rc, _ = _run(["route", "--prompt", "   "], monkeypatch)
    assert rc == 1


def test_cli_catalog_lists_skills(fake_claude_home, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    rc, out = _run(["catalog"], monkeypatch)
    assert rc == 0
    assert "Catalog: 3 skill(s)" in out
    assert "alpha" in out and "beta" in out and "gamma" in out


def test_cli_catalog_multilevel_filter(fake_claude_home, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    rc, out = _run(["catalog", "--multilevel"], monkeypatch)
    assert rc == 0
    assert "beta" in out
    assert "alpha" not in out


def test_cli_catalog_show_one(fake_claude_home, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    rc, out = _run(["catalog", "--skill", "beta"], monkeypatch)
    assert rc == 0
    assert "# beta" in out
    assert "multi-level: True" in out


def test_cli_catalog_oversized(fake_claude_home, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    rc, out = _run(["catalog", "--oversized", "30"], monkeypatch)
    assert rc == 0
    assert "gamma" in out
    assert "alpha" not in out


def test_cli_catalog_oversized_accepts_zero(
    fake_claude_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # type: ignore[no-untyped-def]
    rc, out = _run(["catalog", "--oversized", "0"], monkeypatch)
    assert rc == 0
    assert "Oversized skills (body > 0L): 3" in out
    assert "alpha" in out and "beta" in out and "gamma" in out


def test_cli_audit_structural(fake_claude_home, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    # Isolate HOME so drift targets don't see the live user config.
    monkeypatch.setenv("HOME", str(fake_claude_home))
    rc, out = _run(["audit", "structural"], monkeypatch)
    assert rc == 0
    assert "[structural]" in out


def test_cli_audit_check_passes(fake_claude_home, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    # check gates coverage against the live route table; under the fake catalog
    # the real routes would all be ghosts, so inject a consistent route table.
    from skill_router.features.routing.route import Route

    monkeypatch.setenv("HOME", str(fake_claude_home))
    monkeypatch.setattr(
        "skill_router.features.routing.routes.ROUTES",
        [Route(patterns=("alpha",), hint="Skill: load `alpha`.", skills=("alpha",))],
    )
    rc, out = _run(["audit", "check"], monkeypatch)
    assert rc == 0
    assert "OK" in out


def test_cli_audit_check_fails_on_route_catalog_drift(
    fake_claude_home, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    from skill_router.features.routing.route import Route

    monkeypatch.setenv("HOME", str(fake_claude_home))
    monkeypatch.setattr(
        "skill_router.features.routing.routes.ROUTES",
        [Route(patterns=("alpha",), hint="Skill: load `alpha`.", skills=())],
    )
    rc, out = _run(["audit", "check"], monkeypatch)
    assert rc == 1
    assert "FAIL" in out


def test_cli_audit_coverage_reports(fake_claude_home, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    from skill_router.features.routing.route import Route

    monkeypatch.setattr(
        "skill_router.features.routing.routes.ROUTES",
        [Route(patterns=("alpha",), hint="Skill: load `alpha`.", skills=("alpha",))],
    )
    rc, out = _run(["audit", "coverage"], monkeypatch)
    assert rc == 0
    assert "[coverage]" in out
    assert "hint_drift=0" in out
    assert "ghost_skills=0" in out


def test_cli_classify_stats(monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    # --stats reads the log; with isolated state dir there's no log yet.
    monkeypatch.setenv("CLAUDE_HOME", "/nonexistent-skill-router-test")
    rc, out = _run(["classify", "--stats"], monkeypatch)
    assert rc == 0


def test_cli_depth_unknown_skill_errors(fake_claude_home, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    rc, _ = _run(["depth", "--skill", "nope", "--prompt", "x"], monkeypatch)
    assert rc == 1


def test_cli_depth_legacy_skill_returns_body(
    fake_claude_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # type: ignore[no-untyped-def]
    rc, out = _run(["depth", "--skill", "alpha", "--prompt", "anything", "--json"], monkeypatch)
    assert rc == 0
    payload = json.loads(out)
    assert payload["level"] == "body"
    assert payload["skill"] == "alpha"


def test_cli_depth_multilevel_skill_summary_when_ollama_down(
    fake_claude_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # type: ignore[no-untyped-def]
    from skill_router.features.depth import command as depth_mod

    monkeypatch.setattr(depth_mod, "is_alive", lambda: False)
    rc, out = _run(
        ["depth", "--skill", "beta", "--prompt", "generic broad prompt", "--json"], monkeypatch
    )
    assert rc == 0
    payload = json.loads(out)
    assert payload["level"] == "summary"


def test_cli_invalid_subcommand_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit) as exc:
        _run(["bogus"], monkeypatch)
    assert exc.value.code == 2
