#!/usr/bin/env python3
"""Fährt die Oracles nach, parst Sub-Check-Quoten und wertet nach EVALUATION_CONTRACT_V2.

Der Oracle-Exit ist all-or-nothing; die Oracles drucken aber "X / Y checks".
V2-Contract: PASS >= 0.80, PARTIAL >= 0.50, sonst FAIL.
"""
import json, re, subprocess
from pathlib import Path

BASE = Path("/Users/rwu/Arbeitsverzeichnis/tools/llm-benchmark/results/king-eval-2026-09-30")
FIX = Path("/Users/rwu/Arbeitsverzeichnis/lib/local-llm/benchmark/opencode/fixtures")
PAT = re.compile(r"(\d+)\s*/\s*(\d+)\s+checks", re.I)

for f in sorted(BASE.glob("*/*.json")):
    if f.name == "summary.json":
        continue
    rec = json.loads(f.read_text())
    fx = rec.get("fixture")
    job = rec.get("job") or rec.get("scratch_path")
    oracle = FIX / fx / "oracle.sh"
    if not (fx and job and oracle.exists() and Path(job).exists()):
        continue
    r = subprocess.run(["bash", str(oracle)], cwd=job, capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    m = PAT.search(out)
    passed_lines = [ln.strip() for ln in out.splitlines() if ln.strip().startswith(("PASS ", "FAIL "))]
    failed = [ln for ln in passed_lines if ln.startswith("FAIL")]
    sub = None
    if m:
        sub = {"passed": int(m.group(1)), "total": int(m.group(2))}
    elif passed_lines:
        sub = {"passed": len(passed_lines) - len(failed), "total": len(passed_lines)}

    rec["oracle_rerun_exit"] = r.returncode
    rec["oracle_output"] = out[-2000:]
    if sub:
        q = sub["passed"] / sub["total"]
        rec["subchecks"] = sub
        rec["quality_score"] = round(q, 3)
        rec["verdict_v2"] = "PASS" if q >= 0.8 else ("PARTIAL" if q >= 0.5 else "FAIL")
    rec["failed_checks"] = failed
    f.write_text(json.dumps(rec, indent=2, ensure_ascii=False))
    lbl = f.parent.name
    if sub:
        print(f"{lbl:22s} {fx:26s} oracle={rec.get('oracle_exit')} "
              f"sub={sub['passed']}/{sub['total']} ({rec['quality_score']:.0%}) "
              f"-> v2={rec['verdict_v2']}" + (f"  [{'; '.join(failed)}]" if failed else ""))
    else:
        print(f"{lbl:22s} {fx:26s} oracle={rec.get('oracle_exit')} (keine Sub-Check-Ausgabe)")
