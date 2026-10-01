#!/usr/bin/env python3
"""Belegt, OB SpecPrefill je Lauf tatsächlich gegriffen hat — aus den omlx-Logzeilen.

Hintergrund (Quelle: omlx 0.7.0rc1):
- engine/vlm.py: "SpecPrefill: draft model loaded (<pfad>)" bzw. "... load failed" —
  ein Fehlschlag bricht den Modell-Load NICHT ab, das Scoring kehrt dann still zurück.
- specprefill/draft.py: pro Request "SpecPrefill: scored N tokens ... selected K/N (keep=P%)"
  Fehlt diese Zeile, hat es NICHT gegriffen.
- Stille Ausstiege ohne Log: Request mit Bild; Prompt nach Abzug des gecachten
  System-Prefix unter dem Threshold.
"""
import re, subprocess, sys
from pathlib import Path
from datetime import datetime

LOG = Path.home() / ".omlx/logs/server.log"
SCORED = re.compile(r"SpecPrefill: scored (\d+) tokens in ([\d.]+)s, selected (\d+)/(\d+) \(keep=([\d.]+)%")
LOADED = re.compile(r"SpecPrefill: draft model loaded \((.+?)\)")
FAILED = re.compile(r"SpecPrefill: draft model load failed: (.+)")
FALLBACK = re.compile(r"SpecPrefill scoring failed, falling back")
TS = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")


def main(since=None):
    raw = subprocess.run(["tail", "-40000", str(LOG)], capture_output=True, text=True,
                         errors="replace").stdout.splitlines()
    if since:
        cut = datetime.strptime(since, "%Y-%m-%d %H:%M:%S")
        keep = []
        for ln in raw:
            m = TS.match(ln)
            if m and datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S") >= cut:
                keep.append(ln)
            elif keep:
                keep.append(ln)
        raw = keep

    loads = [LOADED.search(l).group(1) for l in raw if LOADED.search(l)]
    fails = [FAILED.search(l).group(1) for l in raw if FAILED.search(l)]
    scored = [SCORED.search(l).groups() for l in raw if SCORED.search(l)]
    fallbacks = sum(1 for l in raw if FALLBACK.search(l))

    print(f"Draft-Load erfolgreich : {len(loads)}" + (f"  -> {loads[-1]}" if loads else ""))
    print(f"Draft-Load fehlgeschlagen: {len(fails)}" + (f"  -> {fails[-1]}" if fails else ""))
    print(f"Scoring-Ereignisse     : {len(scored)}")
    print(f"Fallbacks auf dichten Prefill: {fallbacks}")
    if not scored:
        print("\nURTEIL: SpecPrefill hat NICHT gegriffen — die Messung zeigt keinen "
              "SpecPrefill-Effekt, egal was die Zeiten sagen.")
        return 1
    tot_scored = sum(int(s[0]) for s in scored)
    tot_sel = sum(int(s[2]) for s in scored)
    times = [float(s[1]) for s in scored]
    keeps = [float(s[4]) for s in scored]
    print(f"\ngescorte Tokens gesamt : {tot_scored}")
    print(f"ausgewählt gesamt      : {tot_sel} ({tot_sel/tot_scored:.1%} effektive Keep-Rate)")
    print(f"Keep je Request        : min {min(keeps):.1f}% / median "
          f"{sorted(keeps)[len(keeps)//2]:.1f}% / max {max(keeps):.1f}%")
    print(f"Scoring-Zeit gesamt    : {sum(times):.1f}s (median {sorted(times)[len(times)//2]:.2f}s)")
    print("\nURTEIL: SpecPrefill hat gegriffen.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
