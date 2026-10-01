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


def admin_post(path, payload=None):
    """Admin-Endpoint mit Cookie-Login (Bearer reicht dort nicht)."""
    import http.cookiejar
    key = os.environ["OMLX_API_KEY"]
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(urllib.request.Request(f"{API}/admin/api/login",
            data=json.dumps({"api_key": key}).encode(),
            headers={"Content-Type": "application/json"}, method="POST"))
    r = op.open(urllib.request.Request(f"{API}{path}", data=json.dumps(payload or {}).encode(),
                headers={"Content-Type": "application/json"}, method="POST"))
    return r.status, r.read()[:200].decode(errors="replace")


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
    ap.add_argument("--expect-settings", default="",
                    help='JSON-Objekt der Soll-Settings (z.B. \'{"enable_thinking":true,"mtp_enabled":true}\'). '
                         "Wird nach JEDER Fixture per Admin-API rueckgelesen; weicht ein Wert ab, gilt die "
                         "Fixture als SETTINGS-DRIFT. Anlass 01.10.: WebUI-Aenderung waehrend des Laufs "
                         "(Thinking aus, MTP an) — im omlx-Log unsichtbar, nur Datei-mtime.")
    ap.add_argument("--prompt-prefix-map", default="",
                    help="fx=TEXT,fx=TEXT — Text, der der prompt.md der Fixture vorangestellt wird. "
                         "Fuer In-Chat-Modus-Tags wie {REASON:artemis} (Solstice/DavidAU-Merges): "
                         "so laeuft ein Modell ueber opencode in SEINEM vorgesehenen Modus statt im "
                         "Raster des Basismodells (rwu, 01.10.2026).")
    args = ap.parse_args()

    fixtures = FIXTURES if args.fixtures == "all" else args.fixtures.split(",")
    prefix_map = {}
    for item in filter(None, args.prompt_prefix_map.split(",")):
        fx_name, _, text = item.partition("=")
        prefix_map[fx_name.strip()] = text.strip()
    expect = json.loads(args.expect_settings) if args.expect_settings else {}

    def settings_drift():
        """Liest die Modell-Settings per Admin-API und meldet Abweichungen vom Soll."""
        if not expect:
            return []
        try:
            key = os.environ["OMLX_API_KEY"]
            cj = __import__("http.cookiejar").cookiejar.CookieJar()
            op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
            op.open(urllib.request.Request(f"{API}/admin/api/login",
                    data=json.dumps({"api_key": key}).encode(),
                    headers={"Content-Type": "application/json"}, method="POST"))
            ms = json.loads(op.open(f"{API}/admin/api/models", timeout=30).read())
            ms = ms.get("models", ms)
            cur = next((m for m in ms if isinstance(m, dict) and m.get("id") == args.model), {})
            # Settings haengen je nach omlx-Version direkt am Modell oder unter 'settings'
            cur = cur.get("settings", cur)
            return [f"{k}: soll={v!r} ist={cur.get(k)!r}" for k, v in expect.items()
                    if cur.get(k) != v]
        except Exception as exc:  # Drift-Check darf den Lauf nie selbst stoppen
            return [f"(Drift-Check fehlgeschlagen: {exc})"]

    # Vorab-Gate: opencode bricht bei unbekanntem Modell pro Fixture in ~1s ab
    # ("Model not found") — ohne diesen Check verbrennt ein Tippfehler den ganzen Batch.
    cfg = json.loads((RUNNER.parent / "opencode.json").read_text())
    known = cfg.get("provider", {}).get("omlx", {}).get("models", {})
    if args.model not in known:
        print(f"FEHLER: '{args.model}' steht nicht im omlx-Provider von "
              f"{RUNNER.parent / 'opencode.json'} — Batch nicht gestartet.\n"
              f"Bekannt sind u.a.: {', '.join(list(known)[:5])} …", file=sys.stderr)
        return 1
    out_dir = OUT_BASE / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    short = args.model.split("/")[-1]

    with open(out_dir / "matrix.log", "a") as fh:
        log(fh, f"=== START {args.label} | model={args.model} | {len(fixtures)} fixtures ===")

        # Prefix-Cache leeren: ein zweiter Lauf derselben Fixtures ist sonst bis zu 3x
        # schneller als der erste, allein durch Cache-Treffer (Vorfall 30.09.:
        # v6-debug-unmarked 86s -> 29s bei identischen Settings). Ohne das sind
        # Zeitvergleiche zwischen Laeufen wertlos.
        for ep in ("/admin/api/hot-cache/clear", "/admin/api/ssd-cache/clear"):
            try:
                st, body = admin_post(ep)
                log(fh, f"Cache-Reset {ep}: HTTP {st} {str(body)[:80]}")
            except Exception as exc:
                log(fh, f"Cache-Reset {ep} fehlgeschlagen: {exc}")

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
            # Bis zu 2 Versuche: ein Lauf mit steps=0 ist kein Modellergebnis, sondern
            # ein abgewiesener Request (omlx 507 memory ceiling o.ä.) — Vorfall 30.09.
            for attempt in (1, 2):
                slug = f"king-{args.label}-{fx}-{int(time.time())}"
                log(fh, f"--> {fx} (slug={slug}, Versuch {attempt})")
                t = time.time()
                extra = []
                if fx in prefix_map:
                    # Praefix + Original-Prompt in eine Datei, die run_opencode_test.py per
                    # --prompt-file statt fixtures/<fx>/prompt.md liest. Original bleibt unberuehrt.
                    orig = (RUNNER.parent / "fixtures" / fx / "prompt.md").read_text()
                    pf = out_dir / f"{fx}.prompt.md"
                    pf.write_text(prefix_map[fx] + "\n\n" + orig)
                    extra = ["--prompt-file", str(pf)]
                    log(fh, f"    Prompt-Praefix: {prefix_map[fx]!r}")
                try:
                    proc = subprocess.run(
                        [sys.executable, str(RUNNER), "--model", f"omlx/{args.model}",
                         "--fixture", fx, "--job-slug", slug, *extra],
                        cwd=str(RUNNER.parent), capture_output=True, text=True,
                        timeout=args.timeout)
                    tail = (proc.stdout or "")[-600:]
                    rc = proc.returncode
                except subprocess.TimeoutExpired:
                    tail, rc = "TIMEOUT", -9
                dur = time.time() - t
                drift = settings_drift()
                if drift:
                    log(fh, f"    SETTINGS-DRIFT nach {fx}: {'; '.join(drift)} — Fixture nicht belastbar")

                src = RESULT_SRC / short / "results" / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-opencode-{fx}.json"
                probe = json.loads(src.read_text()) if src.exists() else {}
                po = probe.get("parser_output", {})
                if po.get("steps") or po.get("tool_calls"):
                    break
                if attempt == 1:
                    log(fh, "    steps=0 — kein Modellergebnis (507/Speicher, unbekanntes "
                            "Modell, oder Engine-Pool-Reset durch /admin/api/reload waehrend "
                            "des Laufs), Warmup + zweiter Versuch")
                    try:
                        api_call("/v1/chat/completions", {
                            "model": args.model,
                            "messages": [{"role": "user", "content": "READY"}],
                            "max_tokens": 4}, "POST")
                    except Exception as exc:
                        log(fh, f"    Warmup vor Retry fehlgeschlagen: {exc}")
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
            if rec.get("parser_output", {}).get("steps") == 0:
                status = "INVALID"
                rec_path = out_dir / f"{fx}.json"
                if rec_path.exists():
                    rec["status"] = "INVALID"
                    rec["invalid_reason"] = ("steps=0 nach 2 Versuchen — Request abgewiesen "
                                             "(omlx 507 memory ceiling o.ä.), kein Modellergebnis")
                    rec_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False))
                log(fh, f"    -> als INVALID markiert (kein Modellergebnis)")
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
