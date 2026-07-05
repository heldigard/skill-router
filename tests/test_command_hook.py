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


def test_hook_emits_continue_true_on_unmatched(monkeypatch: pytest.MonkeyPatch) -> None:
    out = _run_hook_with_prompt("cooking pasta recipe", monkeypatch)
    assert out == {"continue": True}


def test_hook_fails_open_on_internal_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the catalog import breaks, the hook must still return continue:true."""
    import skill_router.features.routing.command as routing

    def boom(*_a, **_k):  # noqa: ANN002
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(routing, "match_hints", boom)
    out = _run_hook_with_prompt("Angular components", monkeypatch)
    # Should fail open — either continue:true (caught in main) or via stderr.
    assert out.get("continue") is True or "hookSpecificOutput" in out


def test_load_prompt_handles_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert command.load_prompt() == ""
