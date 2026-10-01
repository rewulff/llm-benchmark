#!/usr/bin/env python3
"""Cloud-Messlatte: fährt die opencode-Fixtures mit der Claude-Code-CLI als Agent.

Gleiche Fixtures, gleiche Oracles, gleiches ruff-Gate wie der opencode-Harness.
Abweichung (im Report auszuweisen): anderer Agent-Loop (CC-CLI statt opencode).
"""
import argparse, json, shutil, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

FIXTURES_DIR = Path("/Users/rwu/Arbeitsverzeichnis/lib/local-llm/benchmark/opencode/fixtures")
OUT_BASE = Path("/Users/rwu/Arbeitsverzeichnis/tools/llm-benchmark/results/king-eval-2026-09-30")
JOBS = Path.home() / "cc-bench-jobs"
FIXTURES = ["a2-bugfix", "v6-quick-nqueens", "v6-debug-unmarked", "c1-dependent-pipeline",
            "v6-custom-constraint", "v6-ambiguity-probe", "v6-produktiv-fqdn-bug",
            "r1-offline-research", "v6-architecture-choice", "a5-long-edit"]


def parse_stream(lines):
    """Zählt Steps/Tool-Calls aus stream-json, holt Kosten/Tokens aus dem result-Event."""
    steps = tools = 0
    breakdown, final, usage, cost, model_used = {}, None, {}, None, None
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            ev = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            steps += 1
            for blk in ev.get("message", {}).get("content", []):
                if blk.get("type") == "tool_use":
                    tools += 1
                    n = blk.get("name", "?").lower()
                    breakdown[n] = breakdown.get(n, 0) + 1
        elif ev.get("type") == "result":
            final = (ev.get("result") or "")[-200:]
            usage = ev.get("usage", {}) or {}
            cost = ev.get("total_cost_usd")
            mu = ev.get("modelUsage") or {}
            model_used = ",".join(mu.keys()) if mu else None
    return {"steps": steps, "tool_calls": tools, "tools_breakdown": breakdown,
            "final_text": final, "usage": usage, "total_cost_usd": cost,
            "model_used": model_used}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="CC-Modell, z.B. sonnet oder opus")
    ap.add_argument("--label", required=True)
    ap.add_argument("--fixtures", default="all")
    ap.add_argument("--timeout", type=int, default=1200)
    args = ap.parse_args()

    fixtures = FIXTURES if args.fixtures == "all" else args.fixtures.split(",")
    out_dir = OUT_BASE / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    logf = open(out_dir / "matrix.log", "a")

    def log(m):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {m}"
        print(line, flush=True); logf.write(line + "\n"); logf.flush()

    log(f"=== START {args.label} | cc-model={args.model} | {len(fixtures)} fixtures ===")
    summary = []
    for fx in fixtures:
        fdir = FIXTURES_DIR / fx
        job = JOBS / f"{args.label}-{fx}-{int(time.time())}"
        work, outp = job / "work", job / "output"
        for d in (job / "input", work, outp):
            d.mkdir(parents=True, exist_ok=True)
        src_in = fdir / "input"
        if src_in.exists():
            for f in src_in.iterdir():
                if f.is_file():
                    shutil.copy2(f, work / f.name)
                    shutil.copy2(f, job / "input" / f.name)
        prompt = (fdir / "prompt.md").read_text()

        log(f"--> {fx} (job={job.name})")
        t = time.time()
        try:
            proc = subprocess.run(
                ["claude", "-p", prompt, "--model", args.model,
                 "--output-format", "stream-json", "--verbose",
                 "--dangerously-skip-permissions"],
                cwd=str(work), capture_output=True, text=True, timeout=args.timeout)
            raw, rc = proc.stdout, proc.returncode
            if proc.stderr:
                (outp / "stderr.txt").write_text(proc.stderr)
        except subprocess.TimeoutExpired as exc:
            raw, rc = (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""), -9
        dur = time.time() - t
        (outp / "run.jsonl").write_text(raw or "")
        parsed = parse_stream((raw or "").splitlines())

        oracle = fdir / "oracle.sh"
        oexit = None
        if oracle.exists():
            oexit = subprocess.run(["bash", str(oracle)], cwd=str(job),
                                   capture_output=True, text=True).returncode
        pys = list(work.glob("*.py"))
        lint = {"checked": len(pys), "passed": True, "ruff_exit": None}
        if pys:
            r = subprocess.run(["ruff", "check", *[str(p) for p in pys]],
                               capture_output=True, text=True)
            lint = {"checked": len(pys), "passed": r.returncode == 0, "ruff_exit": r.returncode}

        # Status wie im opencode-Runner: NUR Oracle entscheidet (Lint wird protokolliert,
        # nicht gewertet — DTZ003 u.a. stecken teils schon im Fixture-Input).
        status = "PASS" if oexit == 0 else ("FAIL" if oexit is not None else "NO_ORACLE")
        rec = {"model": f"cc-cli/{args.model}", "fixture": fx, "job": str(job),
               "timestamp": datetime.now(timezone.utc).isoformat(), "status": status,
               "parser_output": {"duration_s": round(dur, 2), **parsed},
               "python_lint": lint, "oracle_exit": oexit, "cli_rc": rc}
        (out_dir / f"{fx}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False))
        u = parsed["usage"]
        log(f"<-- {fx}: {status} | rc={rc} | {dur:.0f}s | steps={parsed['steps']} "
            f"tools={parsed['tool_calls']} oracle={oexit} lint={lint['ruff_exit']} "
            f"cost={parsed['total_cost_usd']} in={u.get('input_tokens')} "
            f"cache_r={u.get('cache_read_input_tokens')} out={u.get('output_tokens')}")
        summary.append({"fixture": fx, "status": status, "duration_s": round(dur, 1),
                        "steps": parsed["steps"], "tool_calls": parsed["tool_calls"],
                        "oracle_exit": oexit, "total_cost_usd": parsed["total_cost_usd"],
                        "model_used": parsed["model_used"]})

    (out_dir / "summary.json").write_text(json.dumps(
        {"label": args.label, "model": f"cc-cli/{args.model}",
         "harness": "claude-code-cli (nicht opencode — Vergleichseinschränkung)",
         "finished_utc": datetime.now(timezone.utc).isoformat(), "runs": summary}, indent=2))
    p = sum(1 for s in summary if s["status"] == "PASS")
    costs = [s["total_cost_usd"] for s in summary if s["total_cost_usd"]]
    log(f"=== ENDE {args.label}: {p}/{len(summary)} PASS | Kosten-Summe {sum(costs):.4f} USD ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
