"""Unified CLI for skill-router.

Subcommands:
  discover  — compact capability map + deterministic routing for a prompt.
  route     — given a prompt, print routing hints; --depth adds section hints.
  classify  — classify a prompt: category + tier (subsumes the retired intent_route.py).
  depth     — for a skill + prompt, recommend a load level.
  recommend — semantic skill recommender (Ollama embeddings + on-disk index).
  catalog   — list skills (multi-level flag, body size, sections).
  audit     — run catalog health probes (subsumes the retired skills-audit.py).

Invoked via the PATH wrapper at ~/.local/bin/skill-router (mirrors codeq/codescan),
~/.claude/scripts/skill-router, or python3 -m skill_router. Old script names
intent_route / skills-audit are retired; callers use the subcommand form above.
"""
# vs-soft-allow: main() — single-responsibility argparse wiring (~75 lines is the
# declarative cost of exposing 7 subcommands; cohesion intact, no logic beyond dispatch).

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import __version__

if TYPE_CHECKING:
    from .features.budget.command import BudgetReport


def _cmd_discover(args: argparse.Namespace) -> int:
    from .features.discover.command import discover, render

    payload = discover(args.prompt or "", include_examples=args.examples)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render(payload))
    return 0


def _cmd_route(args: argparse.Namespace) -> int:
    from .command import analyze

    prompt = args.prompt or sys.stdin.read()
    if not prompt.strip():
        print("(empty prompt)", file=sys.stderr)
        return 1
    result = analyze(prompt, include_depth=args.depth)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        ctx = result["context"]
        print(ctx if ctx else "(no hints matched)")
        if args.explain:
            print("\n# Route explain")
            decision = result.get("decision") or {}
            print(
                f"  status={decision.get('status', 'unknown')} "
                f"routes={decision.get('route_count', len(result.get('routes', [])))}"
            )
            if decision.get("reason"):
                print(f"  reason: {decision['reason']}")
            for r in result["routes"]:
                print(f"  [{r['index']:02d}] priority={r['priority']} {r['hint'][:96]}")
                for key in ("skills", "tools", "workers", "doc_namespaces"):
                    values = r.get(key) or []
                    if values:
                        print(f"       {key}: {', '.join(values)}")
        if result["depth_decisions"]:
            print("\n# Depth decisions")
            for d in result["depth_decisions"]:
                marker = "📄" if d["level"] == "section" else "📑"
                sec = f" → {d['section']} (cos={d['score']:.2f})" if d["section"] else ""
                print(f"  {marker} {d['skill']:24} {d['level']}{sec}")
    return 0


def _cmd_classify(args: argparse.Namespace) -> int:
    from .features.classify.command import classify, log_record, show_stats

    if args.stats:
        print(show_stats())
        return 0
    prompt = args.prompt or sys.stdin.read()
    if not prompt.strip():
        print("(empty prompt)", file=sys.stderr)
        return 1
    result = classify(prompt, timeout_total=args.timeout)
    if not args.no_log:
        log_record(prompt, result)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        icon = {"T0": "📚", "T1": "🏠", "T2": "☁️ ", "T3": "🧠"}.get(result["tier"], "•")
        print(f"{icon} category : {result['category']}")
        print(
            f"   tier     : {result['tier']}  (T0=grep/docs, T1=local, T2=cheap-cloud, T3=controller)"
        )
        print(f"   confidence: {result['confidence']:.2f}")
        print(f"   reason   : {result['reason']}")
        alt = result.get("cheaper_alternative")
        if alt:
            print(f"   alt      : {alt}")
        model = result.get("model") or "(cascade failed)"
        print(
            f"   model    : {model}  lat={result.get('latency', 0):.2f}s cost=${result.get('cost', 0):.6f}"
        )
        if result.get("error"):
            print(f"   ⚠️  {result['error']}")
    return 0


def _cmd_depth(args: argparse.Namespace) -> int:
    from .features.depth.command import decide
    from .shared.skill_io import find_skill

    skill = find_skill(args.skill)
    if skill is None:
        print(f"(skill not found: {args.skill})", file=sys.stderr)
        return 1
    prompt = args.prompt or sys.stdin.read()
    if not prompt.strip():
        print("(empty prompt)", file=sys.stderr)
        return 1
    dec = decide(prompt, skill)
    if args.json:
        print(
            json.dumps(
                {
                    "skill": dec.skill,
                    "level": dec.level,
                    "section": dec.section,
                    "section_path": dec.section_path,
                    "score": dec.score,
                    "reason": dec.reason,
                    "doc_namespaces": list(dec.doc_namespaces),
                    "tools": list(dec.tools),
                },
                indent=2,
            )
        )
    else:
        print(f"level : {dec.level}")
        if dec.section:
            print(f"section: {dec.section}  (cos={dec.score:.2f})")
            print(f"path  : {dec.section_path}")
        if dec.doc_namespaces:
            print(f"docs  : {', '.join(dec.doc_namespaces)}")
        if dec.tools:
            print(f"tools : {', '.join(dec.tools)}")
        print(f"reason: {dec.reason}")
        print()
        print(dec.as_hint())
    return 0


def _cmd_recommend(args: argparse.Namespace) -> int:
    from .features.recommend.command import (
        RECOMMEND_COSINE_FLOOR,
        as_payload,
        index_status,
        recommend,
    )

    if args.status:
        print(json.dumps(index_status(), indent=2))
        return 0
    prompt = args.prompt or sys.stdin.read()
    if not prompt.strip():
        print("(empty prompt)", file=sys.stderr)
        return 1
    recs = recommend(
        prompt,
        top_k=args.top_k,
        floor=RECOMMEND_COSINE_FLOOR if args.floor is None else args.floor,
        force_rebuild=args.rebuild,
    )
    if args.json:
        print(json.dumps(as_payload(recs), indent=2, ensure_ascii=False))
        return 0
    if not recs:
        print("(no relevant skills above threshold)")
        return 0
    print(f"Top-{args.top_k} skills for this prompt:")
    for r in recs:
        tag = "🧬" if r.mode == "semantic" else "📝"
        print(f"  {tag} {r.score:.3f}  {r.skill:28} {r.reason}")
    return 0


def _cmd_catalog(args: argparse.Namespace) -> int:
    from .features.catalog.command import list_all, oversized, show

    if args.skill:
        print(show(args.skill))
        return 0
    if args.oversized is not None:
        threshold = args.oversized
        skills = oversized(threshold)
        print(f"Oversized skills (body > {threshold}L): {len(skills)}")
        for sk in skills:
            print(f"  {sk.name:32} {sk.body_lines:>4}L  sections={len(sk.sections)}")
        return 0
    print(list_all(only_multilevel=args.multilevel, min_lines=args.min_lines))
    return 0


def _print_budget_report(report: BudgetReport) -> int:
    """Format a Codex model-visible skills budget report; return the gate rc.

    Separates actionable source debt (``over_cap``: source > HARD_CAP) from
    factual model-visible truncation (``shortened``), which also covers entries
    Codex squeezes via its dynamic budget despite being rule-compliant (<=185).
    """
    print(
        f"[budget] entries={report.entries} listing={report.listing_chars}ch "
        f"descriptions={report.displayed_description_chars}/"
        f"{report.full_description_chars}ch shortened={report.shortened} "
        f"over_cap={len(report.over_hard_cap_names)} "
        f"(local={len(report.over_hard_cap_local_names)} "
        f"managed={len(report.over_hard_cap_managed_names)}) "
        f"effective=~{report.effective_budget}ch "
        f"missing_sources={report.missing_sources}"
    )
    # Locally-editable over-cap = actionable debt (the gate fails on this).
    if report.over_hard_cap_local_names:
        print(
            f"  over_cap local (source>{185}, actionable): {', '.join(report.over_hard_cap_local_names)}"
        )
    # Upstream-owned over-cap (Codex .system, plugins, skills-sources packs) —
    # reported honestly, but not first-party local debt.
    if report.over_hard_cap_managed_names:
        print(
            f"  over_cap managed (plugin/system/skills-sources): "
            f"{', '.join(report.over_hard_cap_managed_names)}"
        )
    if report.shortened_names:
        over = set(report.over_hard_cap_names)
        squeezed = sorted(set(report.shortened_names) - over)
        print(f"  shortened: {', '.join(report.shortened_names[:12])}")
        if squeezed:
            print(
                f"  ({len(squeezed)} are rule-compliant <=185 but squeezed by "
                "Codex's dynamic budget — informational, not source debt)"
            )
    return 0 if report.healthy else 1


def _cmd_audit(args: argparse.Namespace) -> int:
    from .features.audit.command import check
    from .features.routing.routes import ROUTES

    if args.submode == "budget":
        from .features.budget.command import inspect_codex

        report = inspect_codex()
        if report is None:
            print("[budget] Codex prompt input unavailable")
            return 1
        return _print_budget_report(report)

    if args.submode == "check":
        rc = check(routes=ROUTES)
        print("OK skills-audit gate" if rc == 0 else "FAIL skills-audit gate")
        return rc
    for handler in _AUDIT_HANDLERS:
        if args.submode in (handler.key, "all"):
            handler.run()
    return 0


def _audit_structural() -> None:
    from .features.audit.command import DESC_WARN_VERBOSE, structural

    s = structural()
    print(
        f"[structural] missing_fm={s['missing_fm'] or 'none'} "
        f"missing_desc={s['missing_desc'] or 'none'} "
        f"name_mismatch={s['name_mismatch'] or 'none'} "
        f"orphans={s['orphans'] or 'none'} "
        f"verbose(>= {DESC_WARN_VERBOSE}ch)={len(s['verbose'])}"
    )


def _audit_drift() -> None:
    from .features.audit.command import drift

    d = drift()
    print("[drift] canonical skills missing per target:")
    for label, info in d.items():
        if info.get("absent_target"):
            print(f"  {label:8} (target dir absent)")
            continue
        miss = info.get("missing", [])
        print(
            f"  {label:8} count={info.get('count')} missing={len(miss)}"
            + (f" -> {miss[:6]}" if miss else "")
        )


def _audit_coverage() -> None:
    from .features.audit.command import coverage
    from .features.routing.routes import ROUTES

    cov = coverage(ROUTES)
    print(
        f"[coverage] routes declare {cov['routed_count']}/{cov['catalog_count']} catalog "
        f"skills; hint_drift={len(cov['hint_drift'])} ghost_skills={len(cov['ghost_skills'])} "
        f"unrouted={len(cov['unrouted'])}"
    )
    for item in cov["hint_drift"]:
        print(f"  drift  route[{item['index']}] undeclared={item['undeclared']}")
    for item in cov["ghost_skills"]:
        print(f"  ghost  route[{item['index']}] skills={item['skills']}")


def _audit_overlap() -> None:
    from .features.audit.command import overlap
    from .features.routing.routes import ROUTES

    ov = overlap(ROUTES)
    print(f"[overlap] {ov['route_count']} routes vs {ov['corpus_size']}-prompt corpus; top pairs:")
    for pair in ov["top"][:8]:
        print(f"  j={pair['jaccard']:.2f}  [{pair['a']:02d}]<->[{pair['b']:02d}]")


def _audit_discrim() -> None:
    from .features.audit.command import discrim

    r = discrim()
    if r is None:
        print("[discrim] embedding backend unavailable — skipped")
        return
    print(f"[discrim] near-dups (sim>=0.80): {len(r['near_dups'])}")
    for sc, a, b in r["near_dups"][:10]:
        print(f"  {sc:.3f}  {a} <-> {b}")


def _audit_bench() -> None:
    from .features.audit.command import bench

    b = bench()
    if b is None:
        print("[bench] embedding backend unavailable — skipped")
        return
    print(f"[bench] hit@1={b['hit1']}/{b['n']}  hit@3={b['hit3']}/{b['n']}")


@dataclass(frozen=True)
class _AuditHandler:
    key: str
    run: Callable[[], None]


_AUDIT_HANDLERS = (
    _AuditHandler("structural", _audit_structural),
    _AuditHandler("drift", _audit_drift),
    _AuditHandler("coverage", _audit_coverage),
    _AuditHandler("overlap", _audit_overlap),
    _AuditHandler("discrim", _audit_discrim),
    _AuditHandler("bench", _audit_bench),
)


def main() -> int:
    p = argparse.ArgumentParser(
        prog="skill-router", description="Unified skill routing for cross-CLI agents."
    )
    p.add_argument("--version", action="version", version=f"skill-router {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    pdiscover = sub.add_parser(
        "discover", help="map ecosystem capabilities and route a prompt without model calls"
    )
    pdiscover.add_argument("--prompt", help="optional task prompt to route")
    pdiscover.add_argument(
        "--examples", action="store_true", help="include compact starter intents"
    )
    pdiscover.add_argument("--json", action="store_true", help="emit the stable discovery schema")
    pdiscover.set_defaults(func=_cmd_discover)

    pr = sub.add_parser("route", help="routing hints for a prompt")
    pr.add_argument("--prompt", help="prompt (else stdin)")
    pr.add_argument("--json", action="store_true")
    pr.add_argument("--explain", action="store_true", help="show matched route metadata")
    pr.add_argument(
        "--depth",
        action="store_true",
        help="also run Ollama-backed multi-level skill section selection",
    )
    pr.set_defaults(func=_cmd_route)

    pc = sub.add_parser("classify", help="classify prompt -> category + tier")
    pc.add_argument("--prompt", help="prompt (else stdin)")
    pc.add_argument("--timeout", type=float, default=12.0)
    pc.add_argument("--json", action="store_true")
    pc.add_argument("--no-log", action="store_true")
    pc.add_argument("--stats", action="store_true")
    pc.set_defaults(func=_cmd_classify)

    pd = sub.add_parser("depth", help="recommend load level for a skill + prompt")
    pd.add_argument("--skill", required=True)
    pd.add_argument("--prompt", help="prompt (else stdin)")
    pd.add_argument("--json", action="store_true")
    pd.set_defaults(func=_cmd_depth)

    pm = sub.add_parser(
        "recommend", help="semantic skill recommender (Ollama embeddings + disk index)"
    )
    pm.add_argument("--prompt", help="prompt (else stdin)")
    pm.add_argument("--top-k", type=int, default=3, help="max skills to return (1-6)")
    pm.add_argument(
        "--floor",
        type=float,
        default=None,
        help="min cosine to recommend a skill (default: calibrated live floor)",
    )
    pm.add_argument("--json", action="store_true")
    pm.add_argument(
        "--rebuild", action="store_true", help="ignore mtime cache and re-embed all skills"
    )
    pm.add_argument("--status", action="store_true", help="report on-disk index health and exit")
    pm.set_defaults(func=_cmd_recommend)

    pcat = sub.add_parser("catalog", help="list skills / show one / find oversized")
    pcat.add_argument("--multilevel", action="store_true", help="only multi-level skills")
    pcat.add_argument("--min-lines", type=int, default=0)
    pcat.add_argument(
        "--oversized", type=int, nargs="?", const=400, help="list skills over N lines (default 400)"
    )
    pcat.add_argument("--skill", help="show one skill in detail")
    pcat.set_defaults(func=_cmd_catalog)

    pa = sub.add_parser("audit", help="catalog health gate")
    pa.add_argument(
        "submode",
        choices=[
            "structural",
            "drift",
            "coverage",
            "overlap",
            "discrim",
            "bench",
            "budget",
            "all",
            "check",
        ],
    )
    pa.set_defaults(func=_cmd_audit)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
