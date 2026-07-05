"""Unified CLI for skill-router.

Subcommands:
  route     — given a prompt, print routing hints (and depth suggestions).
  classify  — classify a prompt: category + tier (subsumes the retired intent_route.py).
  depth     — for a skill + prompt, recommend a load level.
  catalog   — list skills (multi-level flag, body size, sections).
  audit     — run catalog health probes (subsumes the retired skills-audit.py).

Invoked via the PATH wrapper at ~/.local/bin/skill-router (mirrors codeq/codescan)
or the backward-compat launcher at ~/.claude/scripts/skill-router. Legacy script
names intent_route / skills-audit were RETIRED (no shims) — callers must use the
subcommand form above.
"""

from __future__ import annotations

import argparse
import json
import sys


def _cmd_route(args: argparse.Namespace) -> int:
    from .command import analyze

    prompt = args.prompt or sys.stdin.read()
    if not prompt.strip():
        print("(empty prompt)", file=sys.stderr)
        return 1
    result = analyze(prompt)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        ctx = result["context"]
        print(ctx if ctx else "(no hints matched)")
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
                },
                indent=2,
            )
        )
    else:
        print(f"level : {dec.level}")
        if dec.section:
            print(f"section: {dec.section}  (cos={dec.score:.2f})")
            print(f"path  : {dec.section_path}")
        print(f"reason: {dec.reason}")
        print()
        print(dec.as_hint())
    return 0


def _cmd_catalog(args: argparse.Namespace) -> int:
    from .features.catalog.command import list_all, oversized, show

    if args.skill:
        print(show(args.skill))
        return 0
    if args.oversized:
        threshold = args.oversized
        skills = oversized(threshold)
        print(f"Oversized skills (body > {threshold}L): {len(skills)}")
        for sk in skills:
            print(f"  {sk.name:32} {sk.body_lines:>4}L  sections={len(sk.sections)}")
        return 0
    print(list_all(only_multilevel=args.multilevel, min_lines=args.min_lines))
    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
    from .features.audit.command import (
        DESC_WARN_VERBOSE,
        bench,
        check,
        discrim,
        drift,
        structural,
    )

    if args.submode == "check":
        rc = check()
        print("OK skills-audit gate" if rc == 0 else "FAIL skills-audit gate")
        return rc
    if args.submode in ("structural", "all"):
        s = structural()
        print(
            f"[structural] missing_fm={s['missing_fm'] or 'none'} "
            f"missing_desc={s['missing_desc'] or 'none'} "
            f"name_mismatch={s['name_mismatch'] or 'none'} "
            f"orphans={s['orphans'] or 'none'} "
            f"verbose(>= {DESC_WARN_VERBOSE}ch)={len(s['verbose'])}"
        )
    if args.submode in ("drift", "all"):
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
    if args.submode in ("discrim", "all"):
        r = discrim()
        if r is None:
            print("[discrim] ollama down — skipped")
        else:
            print(f"[discrim] near-dups (sim>=0.80): {len(r['near_dups'])}")
            for sc, a, b in r["near_dups"][:10]:
                print(f"  {sc:.3f}  {a} <-> {b}")
    if args.submode in ("bench", "all"):
        b = bench()
        if b is None:
            print("[bench] ollama down — skipped")
        else:
            print(f"[bench] hit@1={b['hit1']}/{b['n']}  hit@3={b['hit3']}/{b['n']}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        prog="skill-router", description="Unified skill routing for cross-CLI agents."
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("route", help="routing hints for a prompt")
    pr.add_argument("--prompt", help="prompt (else stdin)")
    pr.add_argument("--json", action="store_true")
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

    pcat = sub.add_parser("catalog", help="list skills / show one / find oversized")
    pcat.add_argument("--multilevel", action="store_true", help="only multi-level skills")
    pcat.add_argument("--min-lines", type=int, default=0)
    pcat.add_argument(
        "--oversized", type=int, nargs="?", const=400, help="list skills over N lines (default 400)"
    )
    pcat.add_argument("--skill", help="show one skill in detail")
    pcat.set_defaults(func=_cmd_catalog)

    pa = sub.add_parser("audit", help="catalog health gate")
    pa.add_argument("submode", choices=["structural", "drift", "discrim", "bench", "all", "check"])
    pa.set_defaults(func=_cmd_audit)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
