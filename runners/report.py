#!/usr/bin/env python3
"""Baut den King-Eval-Report aus den Einzel-Ergebnis-JSONs (nicht aus summary.json —
die Batch-Summaries enthalten teils das alte, zu strenge Status-Kriterium)."""
import json
from pathlib import Path

BASE = Path("/Users/rwu/Arbeitsverzeichnis/tools/llm-benchmark/results/king-eval-2026-09-30")
ORDER = ["a2-bugfix", "v6-quick-nqueens", "v6-debug-unmarked", "c1-dependent-pipeline",
         "v6-custom-constraint", "v6-ambiguity-probe", "v6-produktiv-fqdn-bug",
         "r1-offline-research", "v6-architecture-choice", "a5-long-edit"]

data, labels = {}, []
for d in sorted(BASE.iterdir()):
    if not d.is_dir():
        continue
    recs = {}
    for f in d.glob("*.json"):
        if f.name == "summary.json":
            continue
        r = json.loads(f.read_text())
        recs[r["fixture"]] = r
    if recs:
        labels.append(d.name)
        data[d.name] = recs


def cell(r):
    if not r:
        return "—"
    if r.get("status") == "INVALID":
        return "INVALID (507)"
    oe = r.get("oracle_exit")
    sub = r.get("subchecks")
    q = f"{sub['passed']}/{sub['total']}" if sub else "—"
    v = "PASS" if oe == 0 else "FAIL"
    p = r.get("parser_output", {})
    extra = ""
    nv = (r.get("lint_delta") or {}).get("new_violations") or {}
    if nv:
        extra = " ⚠lint"
    return f"{v} · {q} · {p.get('duration_s', 0):.0f}s · {p.get('steps')}st/{p.get('tool_calls')}tc{extra}"


print("| Fixture | " + " | ".join(labels) + " |")
print("|---|" + "---|" * len(labels))
for fx in ORDER:
    print(f"| `{fx}` | " + " | ".join(cell(data[l].get(fx)) for l in labels) + " |")

print()
print("| Lauf | Oracle-PASS | V2-Verdict PASS | Gesamtzeit | Kosten (CLI-Angabe) | Anmerkung |")
print("|---|---|---|---|---|---|")
for l in labels:
    rs = [r for r in data[l].values() if r.get("status") != "INVALID"]
    inval = len(data[l]) - len(rs)
    op = sum(1 for r in rs if r.get("oracle_exit") == 0)
    v2 = sum(1 for r in rs if r.get("verdict_v2") == "PASS" or
             (r.get("verdict_v2") is None and r.get("oracle_exit") == 0))
    t = sum(r.get("parser_output", {}).get("duration_s", 0) for r in rs)
    c = sum(r.get("parser_output", {}).get("total_cost_usd") or 0 for r in rs)
    print(f"| {l} | {op}/{len(rs)} | {v2}/{len(rs)} | {t/60:.1f} min | "
          + (f"{c:.2f} USD" if c else "0 (lokal)")
          + (f" | {inval} ungültig (507)" if inval else " | —") + " |")
