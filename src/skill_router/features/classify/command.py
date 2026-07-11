"""Prompt classifier: category + model tier suggestion.

Migrated verbatim in spirit from ~/.claude/scripts/intent_route.py. Uses the
cheap_llm cascade (T1 local Ollama -> T2 cloud) so classification costs $0 on
subscription, never blocks prompt submission (returns 'meta' on failure).

The category -> tier map encodes the project rule: the cheap cascade only
PREPROCESSES; code-producing + reasoning tasks go to T3 (controller).
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from typing import Any

from ...shared.compat import ensure_ecosystem_imports
from ...shared.config import (
    CATEGORIES,
    CATEGORY_TIER,
    INTENT_LOG_DIR_NAME,
    INTENT_SYSTEM_PROMPT,
    INTENT_TIMEOUT_DEFAULT,
)
from ...shared.paths import state_dir

ensure_ecosystem_imports()  # makes `cheap_llm` importable from ~/.claude/scripts

CHEAP_LLM_MIN_VERSION = "1.2"
CLASSIFY_MAX_OUTPUT_TOKENS = 256


def _import_cheap_llm():
    try:
        import cheap_llm  # type: ignore

        cheap_llm.require(CHEAP_LLM_MIN_VERSION)
        return cheap_llm
    except Exception:
        return None


def classify(prompt: str, timeout_total: float = INTENT_TIMEOUT_DEFAULT) -> dict:
    """Classify one prompt. Always cheap (T1 local -> T2 cloud). Never raises."""
    cheap = _import_cheap_llm()
    if cheap is None:
        return _fallback(prompt, reason="cheap_llm unavailable")
    try:
        out = cheap.cheap_complete(
            system=INTENT_SYSTEM_PROMPT,
            prompt=f"PROMPT TO CLASSIFY:\n{prompt[:2000]}",
            schema_hint=["category", "confidence", "reason", "cheaper_alternative"],
            timeout_total=timeout_total,
            prefer_local=True,
            require_json=True,
            max_output_tokens=CLASSIFY_MAX_OUTPUT_TOKENS,
        )
    except Exception as exc:  # noqa: BLE001 — fail-open is the contract
        return _fallback(prompt, reason=f"cheap_complete raised: {type(exc).__name__}")
    if not isinstance(out, dict):
        # cheap_complete returned None or unexpected type — don't let .get() raise.
        return _fallback(prompt, reason="cheap_complete returned non-dict; treating as meta")
    parsed = _parse_json(out)
    if parsed is None:
        return _fallback(prompt, reason="classification failed; treating as meta", out=out)
    cat = str(parsed.get("category", "meta")).strip().lower()
    if cat not in CATEGORIES:
        cat = "meta"
    conf = _as_float(parsed.get("confidence"))
    return {
        "category": cat,
        "confidence": conf,
        "reason": str(parsed.get("reason", ""))[:200],
        "cheaper_alternative": str(parsed.get("cheaper_alternative", ""))[:200],
        "tier": CATEGORY_TIER[cat],
        "model": out.get("model"),
        "latency": _as_float(out.get("latency")),
        "cost": _as_float(out.get("cost")),
        "tier_used": out.get("tier"),
        "attempts": out.get("attempts"),
    }


def _as_float(value: Any, default: float = 0.0) -> float:
    """Best-effort float coercion for model-returned telemetry."""
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def _parse_json(out: dict) -> dict | None:
    if not out.get("json_valid"):
        return None
    text = out.get("text", "")
    if not isinstance(text, str):
        return None
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{[^{}]*\"category\"[^{}]*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def _fallback(_prompt: str, reason: str, out: dict | None = None) -> dict:
    """Conservative default when classification fails. Never leaks to T2 paid cloud."""
    out = out or {}
    return {
        "category": "meta",
        "confidence": 0.0,
        "reason": reason,
        "cheaper_alternative": "",
        "tier": CATEGORY_TIER["meta"],
        "model": out.get("model"),
        "latency": _as_float(out.get("latency")),
        "cost": _as_float(out.get("cost")),
        "tier_used": out.get("tier"),
        "attempts": out.get("attempts"),
        "error": out.get("error"),
    }


def log_record(prompt: str, result: dict) -> None:
    """Append one JSONL record to ~/.claude/state/intent-route/log.jsonl. Best-effort."""
    try:
        log_dir = state_dir() / INTENT_LOG_DIR_NAME
        log_dir.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": int(time.time()),
            "prompt_preview": prompt[:120],
            "prompt_len": len(prompt),
            **result,
        }
        with (log_dir / "log.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass


def show_stats() -> str:
    """Render usage stats from the log. Returns formatted text."""
    log_path = state_dir() / INTENT_LOG_DIR_NAME / "log.jsonl"
    if not log_path.exists():
        return "(no log yet)"
    cats: Counter = Counter()
    tiers: Counter = Counter()
    models: Counter = Counter()
    total_cost = 0.0
    total_lat = 0.0
    n = 0
    with log_path.open() as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            n += 1
            cats[rec.get("category", "?")] += 1
            tiers[rec.get("tier", "?")] += 1
            models[rec.get("model") or "?"] += 1
            total_cost += _as_float(rec.get("cost"))
            total_lat += _as_float(rec.get("latency"))
    lines = [
        f"Records: {n}",
        f"Total cost: ${total_cost:.6f}    Avg latency: {total_lat / max(n, 1):.2f}s",
        "",
        "By category:",
    ]
    for c, k in cats.most_common():
        lines.append(f"  {c:14} {k:4} {'█' * min(k, 40)}")
    lines.append("")
    lines.append("By tier:")
    for t, k in tiers.most_common():
        lines.append(f"  {t:4} {k:4}")
    lines.append("")
    lines.append("By model:")
    for m, k in models.most_common():
        lines.append(f"  {m or '(none)':32} {k:4}")
    return "\n".join(lines)
