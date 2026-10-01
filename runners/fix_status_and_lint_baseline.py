#!/usr/bin/env python3
"""Zieht Status (oracle-only) nach und berechnet Lint-Delta gegen die Fixture-Baseline."""
import json, subprocess
from pathlib import Path

BASE = Path("/Users/rwu/Arbeitsverzeichnis/tools/llm-benchmark/results/king-eval-2026-09-30")
FIX = Path("/Users/rwu/Arbeitsverzeichnis/lib/local-llm/benchmark/opencode/fixtures")


def lint_codes(paths):
    if not paths:
        return {}
    r = subprocess.run(["ruff", "check", "--output-format", "json", *map(str, paths)],
                       capture_output=True, text=True)
    out = {}
    try:
        for v in json.loads(r.stdout or "[]"):
            out[v["code"]] = out.get(v["code"], 0) + 1
    except json.JSONDecodeError:
        pass
    return out


baseline = {d.name: lint_codes(sorted((d / "input").glob("*.py")))
            for d in FIX.iterdir() if d.is_dir()}
print("Fixture-Baselines mit Verstößen:",
      {k: v for k, v in baseline.items() if v})

for f in sorted(BASE.glob("*/*.json")):
    if f.name in ("summary.json",):
        continue
    rec = json.loads(f.read_text())
    fx, job = rec.get("fixture"), rec.get("job") or rec.get("scratch_path")
    if not fx or not job:
        continue
    work = Path(job) / "work"
    got = lint_codes(sorted(work.glob("*.py"))) if work.exists() else {}
    base = baseline.get(fx, {})
    new_v = {c: n - base.get(c, 0) for c, n in got.items() if n - base.get(c, 0) > 0}
    old_status = rec.get("status")
    oe = rec.get("oracle_exit")
    rec["status"] = "PASS" if oe == 0 else ("FAIL" if oe is not None else "NO_ORACLE")

    # Infrastruktur-Abweisungen sind keine Modellergebnisse: der omlx-Prefill-Guard und
    # 507-Ablehnungen brechen den Agent-Loop ab, oft nach 1-2 Steps (entgeht dem
    # steps=0-Filter). Erkannt am Fehlerobjekt im run.jsonl. Vorfall 30.09.
    jsonl = Path(job) / "output" / "run.jsonl"
    if rec["status"] != "PASS" and jsonl.exists():
        blob = jsonl.read_text(errors="replace")
        for marker, why in (("memory guard rejected", "omlx Prefill-Memory-Guard hat den Prompt "
                             "abgewiesen (iogpu.wired_limit_mb zu klein) — kein Modellergebnis"),
                            ("Insufficient Storage", "omlx 507: Modell nicht ladbar — kein Modellergebnis"),
                            ("memory ceiling", "omlx Memory-Ceiling erreicht — kein Modellergebnis"),
                            ("Model not found", "Modell fehlt im omlx-Provider der opencode.json — kein Modellergebnis")):
            if marker in blob:
                rec["status"] = "INVALID"
                rec["invalid_reason"] = why
                break
    rec["lint_delta"] = {"baseline": base, "after_run": got, "new_violations": new_v}
    f.write_text(json.dumps(rec, indent=2, ensure_ascii=False))
    if old_status != rec["status"] or new_v:
        print(f"{f.parent.name}/{fx}: {old_status} -> {rec['status']}"
              + (f" | NEUE Lint-Verstöße: {new_v}" if new_v else " | keine neuen Lint-Verstöße"))
