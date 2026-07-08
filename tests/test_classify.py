"""Tests for features/classify/command.py: classification + fallbacks.

Stubs cheap_llm so no network is needed. Exercises the cascade contract:
- success path (json_valid + parseable) -> tier from CATEGORY_TIER
- json_valid but unparseable -> fallback "meta"
- cheap_llm unavailable -> fallback "meta"
"""

from __future__ import annotations

import json

import pytest

from skill_router.features.classify import command as cls


class _FakeCheap:
    """Stand-in for the cheap_llm module. Returns a canned cascade result."""

    def __init__(
        self,
        *,
        json_valid: bool = True,
        text: str = "",
        model: str = "fake-model",
        latency: float = 0.1,
        cost: float = 0.0,
        tier: str = "T1",
        attempts: int = 1,
        error: str | None = None,
    ) -> None:
        self._payload = {
            "json_valid": json_valid,
            "text": text,
            "model": model,
            "latency": latency,
            "cost": cost,
            "tier": tier,
            "attempts": attempts,
            "error": error,
        }

    def cheap_complete(self, **_kw):  # noqa: ANN003, ANN202
        return self._payload


def test_classify_success_picks_correct_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeCheap(
        text=json.dumps(
            {
                "category": "architecture",
                "confidence": 0.9,
                "reason": "design decision",
                "cheaper_alternative": "",
            }
        )
    )
    monkeypatch.setattr(cls, "_import_cheap_llm", lambda: fake)
    result = cls.classify("design OAuth flow for multi-tenant SaaS")
    assert result["category"] == "architecture"
    assert result["tier"] == "T3"  # architecture -> T3 (controller)
    assert result["confidence"] == 0.9
    assert result["model"] == "fake-model"


def test_classify_unknown_category_falls_back_to_meta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeCheap(text=json.dumps({"category": "bogus", "confidence": 0.5}))
    monkeypatch.setattr(cls, "_import_cheap_llm", lambda: fake)
    result = cls.classify("x")
    assert result["category"] == "meta"
    assert result["tier"] == "T1"


def test_classify_non_numeric_telemetry_uses_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeCheap(
        text=json.dumps({"category": "debug", "confidence": "high"}),
        latency="slow",  # type: ignore[arg-type]
        cost="free",  # type: ignore[arg-type]
    )
    monkeypatch.setattr(cls, "_import_cheap_llm", lambda: fake)
    result = cls.classify("debug this")
    assert result["category"] == "debug"
    assert result["confidence"] == 0.0
    assert result["latency"] == 0.0
    assert result["cost"] == 0.0


def test_classify_unparseable_json_falls_back_to_meta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # json_valid True but the text is garbage -> parser fails -> fallback.
    fake = _FakeCheap(json_valid=True, text="not json at all {")
    monkeypatch.setattr(cls, "_import_cheap_llm", lambda: fake)
    result = cls.classify("x")
    assert result["category"] == "meta"
    assert result["confidence"] == 0.0
    assert "failed" in result["reason"]


def test_classify_json_with_embedded_object_extracts_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # text contains a {..."category"...} block embedded in prose.
    payload = 'noise {"category": "debug", "confidence": 0.7} more noise'
    fake = _FakeCheap(json_valid=True, text=payload)
    monkeypatch.setattr(cls, "_import_cheap_llm", lambda: fake)
    result = cls.classify("why does this fail")
    assert result["category"] == "debug"
    assert result["tier"] == "T3"


def test_classify_cheap_llm_unavailable_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cls, "_import_cheap_llm", lambda: None)
    result = cls.classify("anything")
    assert result["category"] == "meta"
    assert result["tier"] == "T1"
    assert "unavailable" in result["reason"]


class _RaisingCheap:
    """cheap_llm whose cheap_complete raises — must NOT escape classify()."""

    def cheap_complete(self, **_kw):  # noqa: ANN003, ANN202
        raise RuntimeError("boom")


class _NoneCheap:
    """cheap_llm whose cheap_complete returns None (unexpected contract)."""

    def cheap_complete(self, **_kw):  # noqa: ANN003, ANN202
        return None


def test_classify_cheap_complete_raising_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cls, "_import_cheap_llm", lambda: _RaisingCheap())
    result = cls.classify("anything")
    assert result["category"] == "meta"
    assert result["tier"] == "T1"
    assert "RuntimeError" in result["reason"]


def test_classify_cheap_complete_returns_none_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cls, "_import_cheap_llm", lambda: _NoneCheap())
    result = cls.classify("anything")
    assert result["category"] == "meta"
    assert result["tier"] == "T1"
    assert "non-dict" in result["reason"]


def test_log_record_writes_jsonl(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_dir = tmp_path / "state" / "intent-route"
    monkeypatch.setattr(cls, "state_dir", lambda: tmp_path / "state")
    cls.log_record("a prompt", {"category": "trivial", "tier": "T0"})
    log_file = log_dir / "log.jsonl"
    assert log_file.exists()
    rec = json.loads(log_file.read_text().strip())
    assert rec["prompt_preview"] == "a prompt"
    assert rec["category"] == "trivial"


def test_show_stats_empty_when_no_log(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cls, "state_dir", lambda: tmp_path / "state")
    assert cls.show_stats() == "(no log yet)"


def test_show_stats_aggregates_records(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    log_dir = tmp_path / "state" / "intent-route"
    log_dir.mkdir(parents=True)
    (log_dir / "log.jsonl").write_text(
        json.dumps(
            {"category": "trivial", "tier": "T0", "model": "m1", "cost": 0.0, "latency": 1.0}
        )
        + "\n"
        + json.dumps(
            {"category": "architecture", "tier": "T3", "model": "m2", "cost": 0.001, "latency": 2.0}
        )
        + "\n"
    )
    monkeypatch.setattr(cls, "state_dir", lambda: tmp_path / "state")
    out = cls.show_stats()
    assert "Records: 2" in out
    assert "trivial" in out
    assert "architecture" in out
