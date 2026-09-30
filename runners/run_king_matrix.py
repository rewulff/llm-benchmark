#!/usr/bin/env python3
"""King-Eval-Matrix: fährt alle opencode-Fixtures seriell gegen EIN omlx-Modell.

Ausgabe: results/king-eval-2026-09-30/<label>/<fixture>.json + matrix.log
Betriebsregeln (MODELLWAHL.md): Warmup vor Batch, serieller Betrieb, Unload am Ende.
"""
import argparse, json, os, shutil, subprocess, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

RUNNER = Path("/Users/rwu/Arbeitsverzeichnis/lib/local-llm/benchmark/opencode/run_opencode_test.py")
RESULT_SRC = Path("/Users/rwu/Arbeitsverzeichnis/lib/local-llm/benchmark/opencode/models")
OUT_BASE = Path("/Users/rwu/Arbeitsverzeichnis/tools/llm-benchmark/results/king-eval-2026-09-30")
FIXTURES = ["a2-bugfix", "v6-quick-nqueens", "v6-debug-unmarked", "c1-dependent-pipeline",
            "v6-custom-constraint", "v6-ambiguity-probe", "v6-produktiv-fqdn-bug",
            "r1-offline-research", "v6-architecture-choice", "a5-long-edit"]
API = "http://127.0.0.1:1235"


def api_call(path, payload=None, method="GET"):
    key = os.environ["OMLX_API_KEY"]
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{API}{path}", data=data, method=method,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return r.status, json.loads(r.read() or b"{}")


def log(fh, msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    fh.write(line + "\n")
    fh.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="omlx-Modell-ID (ohne Provider-Präfix)")
    ap.add_argument("--label", required=True, help="Ordnername, z.B. ornith15-mxfp4-think")
    ap.add_argument("--fixtures", default="all")
    ap.add_argument("--timeout", type=int, default=1800, help="Sekunden pro Fixture")
    ap.add_argument("--unload-after", action="store_true")
    args = ap.parse_args()

    fixtures = FIXTURES if args.fixtures == "all" else args.fixtures.split(",")
    out_dir = OUT_BASE / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    short = args.model.split("/")[-1]

    with open(out_dir / "matrix.log", "a") as fh:
        log(fh, f"=== START {args.label} | model={args.model} | {len(fixtures)} fixtures ===")

        # Warmup (Cold-Load raus aus der ersten Messung)
        t0 = time.time()
        try:
            st, body = api_call("/v1/chat/completions", {
                "model": args.model,
                "messages": [{"role": "user", "content": "Reply with: READY"}],
                "max_tokens": 8}, "POST")
            log(fh, f"Warmup: HTTP {st} | load={body.get('usage', {}).get('model_load_duration')}s "
                    f"| wall={time.time() - t0:.1f}s")
        except Exception as exc:
            log(fh, f"Warmup FEHLER: {exc} — Abbruch")
            return 1

        summary = []
        for fx in fixtures:
            slug = f"king-{args.label}-{fx}-{int(time.time())}"
            log(fh, f"--> {fx} (slug={slug})")
            t = time.time()
            try:
                proc = subprocess.run(
                    [sys.executable, str(RUNNER), "--model", f"omlx/{args.model}",
                     "--fixture", fx, "--job-slug", slug],
                    cwd=str(RUNNER.parent), capture_output=True, text=True,
                    timeout=args.timeout)
                tail = (proc.stdout or "")[-600:]
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                tail, rc = "TIMEOUT", -9
            dur = time.time() - t

            src = RESULT_SRC / short / "results" / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-opencode-{fx}.json"
            status = "NO_RESULT"
            rec = {}
            if src.exists():
                rec = json.loads(src.read_text())
                status = rec.get("status", "?")
                shutil.copy2(src, out_dir / f"{fx}.json")
            log(fh, f"<-- {fx}: {status} | rc={rc} | {dur:.0f}s | "
                    f"steps={rec.get('parser_output', {}).get('steps')} "
                    f"tools={rec.get('parser_output', {}).get('tool_calls')} "
                    f"oracle={rec.get('oracle_exit')}")
            if status == "NO_RESULT":
                log(fh, f"    stdout-tail: {tail[-300:]}")
            summary.append({"fixture": fx, "status": status, "rc": rc,
                            "duration_s": round(dur, 1),
                            "steps": rec.get("parser_output", {}).get("steps"),
                            "tool_calls": rec.get("parser_output", {}).get("tool_calls"),
                            "oracle_exit": rec.get("oracle_exit"),
                            "reasoning_tokens": rec.get("parser_output", {}).get("tokens", {}).get("reasoning_sum")})

        (out_dir / "summary.json").write_text(json.dumps(
            {"label": args.label, "model": args.model,
             "finished_utc": datetime.now(timezone.utc).isoformat(),
             "runs": summary}, indent=2))
        passed = sum(1 for s in summary if s["status"] == "PASS")
        log(fh, f"=== ENDE {args.label}: {passed}/{len(summary)} PASS ===")

        if args.unload_after:
            try:
                st, _ = api_call(f"/v1/models/{args.model}/unload", {}, "POST")
                log(fh, f"Unload: HTTP {st}")
            except Exception as exc:
                log(fh, f"Unload FEHLER: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
