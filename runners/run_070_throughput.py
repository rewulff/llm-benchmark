#!/usr/bin/env python3
"""Durchsatz-Matrix auf omlx 0.7.0 — trennt Versions-, Quant- und MTP-Effekt.

Anlass: Die omlx-0.7.0-Release-Benchmarks melden gegenueber 0.7.0rc1 bis +50 % TG
bei Qwen3.8. Unsere gesamte King-Eval lief auf rc1, mit anderen Quants (nvfp4 /
MLX-6bit) als die Referenzmessungen (oQ4e). Drei Faktoren waren also gleichzeitig
anders — diese Matrix dreht sie einzeln.

Zellen:
  A  ThinkingCap nvfp4      MTP aus   -> Versionseffekt dense (rc1-Referenz: 10,0 tok/s)
  B  ThinkingCap nvfp4      MTP d3    -> Versionseffekt MTP   (rc1-Referenz: 15,3 tok/s)
  C  ThinkingCap oQ4e-mtp   MTP aus   -> Quanteffekt dense
  D  ThinkingCap oQ4e-mtp   MTP d3    -> beste dense-Kombination
  E  Ornith 6bit            MTP aus   -> Versionseffekt MoE   (rc1-Referenz: 46,9 tok/s)
  F  Ornith oQ4e-mtp        MTP aus   -> Quanteffekt MoE
  G  Ornith oQ4e-mtp        MTP d3    -> die offene MoE-MTP-Frage auf 0.7.0

Messgroesse ist reiner Decode-Durchsatz: Warmup laedt das Modell, danach n=3
Messlaeufe; tok/s = completion_tokens / Antwortzeit bei kurzem Prompt. Vor jeder
Zelle werden Hot- und SSD-Cache geleert (sonst verfaelscht der Prefix-Cache die
Zeiten, siehe Memory benchmark-einzellauf-varianz).

MTP wird nicht geglaubt, sondern belegt: nach jeder MTP-Zelle wird im Serverlog
nach der accept=-Zeile gesucht. Fehlt sie, lief kein MTP und die Zelle wird als
MTP-INAKTIV markiert statt als Messwert ausgegeben.
"""
import http.client
import http.cookiejar
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = "http://127.0.0.1:1235"
OUT = Path(__file__).resolve().parent.parent / "results" / "omlx-070-throughput"
REPS = 3

TC_NVFP4 = "ThinkingCap-Qwen3.8-27B-mlx-nvfp4"  # serverseitig OHNE Uploader-Praefix
TC_OQ4E = "chriswessels--ThinkingCap-Qwen3.8-27B-oQ4e-mtp"
OR_6BIT = "ornith-ai--Ornith-1.5-35B-A3B-MLX-6bit"
OR_OQ4E = "scottlowry--Ornith-1.5-35B-A3B-oQ4e-mtp"

SOLSTICE = ("Solstice-AI--Qwen3.8-27B-TURBO-Fable-Cold-Fusion-735-882-Heretic-Uncensored-"
            "NM-DAU-mlx-oQ4e-1M")
# TurboQuant-KV 4-bit = omlx-Pendant zu Solstices beworbenem `--type-k turbo4` (omlx kennt
# nur eine gemeinsame Bit-Tiefe fuer K und V; 4 ist das konservativere von turbo4/turbo3).
TQ4 = {"turboquant_kv_enabled": True, "turboquant_kv_bits": 4, "turboquant_skip_last": True}

# (Zelle, Modell-ID, MTP-Tiefe oder None, rc1-Referenzwert oder None, Zusatz-Settings)
CELLS = [
    ("A", TC_NVFP4, None, 10.0, {}),
    ("B", TC_NVFP4, 3, 15.3, {}),
    ("C", TC_OQ4E, None, None, {}),
    ("D", TC_OQ4E, 3, None, {}),
    ("E", OR_6BIT, None, 46.9, {}),
    ("F", OR_OQ4E, None, None, {}),
    ("G", OR_OQ4E, 3, None, {}),
    # Solstice-Pruefung 01.10. (rwu: "mit deren vorgeschlagenen Settings testen"):
    #   H  Solstice, deren Settings (temp 0.6, top_p 0.95, top_k 20, nothink, TQ-KV 4-bit)
    #   I  Solstice ohne TQ-KV  -> isoliert den KV-Effekt
    #   J  ThinkingCap oQ4e ohne MTP im SELBEN Lauf -> gleiche Architektur/Groesse, Referenz
    #      unter identischen Bedingungen statt gegen die Mittagszahl (14,6)
    ("H", SOLSTICE, None, None, TQ4),
    ("I", SOLSTICE, None, None, {}),
    ("J", TC_OQ4E, None, None, {}),
    # Herstellerempfehlung laut chat_template.jinja: enable_thinking=true, reasoning_effort
    # Default 'xhigh' (hyperion). omlx hat KEIN reasoning_effort-Setting — die Variable geht
    # nur per Request (chat_template_kwargs) ins Template. DavidAUs Kernbehauptung ist
    # "1/2 bis 1/20 der Thinking-Tokens": Messwert ist reasoning_tokens je Antwort.
    #   K  Solstice, Thinking AN, Effort low  (apollo)   — der "TURBO"-Kandidat
    #   L  Solstice, Thinking AN, Effort xhigh (hyperion) — deren Default
    #   M  ThinkingCap oQ4e, Thinking AN, Default-Effort  — Referenz derselben Architektur
    ("K", SOLSTICE, None, None, {**TQ4, "enable_thinking": True, "_effort": "low"}),
    ("L", SOLSTICE, None, None, {**TQ4, "enable_thinking": True, "_effort": "xhigh"}),
    ("M", TC_OQ4E, None, None, {"enable_thinking": True}),
    # 01.10. 16:27, rwu: "ich sehe sofort mehr t/s" — Solstice laeuft mit Lightning MTP, obwohl
    # das Repo keine mtp.*-Tensoren hat (omlx-Log: "model has mtp_forward", Acceptance 87-90 %).
    # Meine Annahme "kein Head -> kein MTP" war falsch. Fairer Tempo-Vergleich zu Zelle D
    # (ThinkingCap oQ4e + MTP d3 = 22,6): gleiche Tiefe, gleiches Regime, kein TQ-KV.
    ("N", SOLSTICE, 3, None, {}),
    # MTP-Tiefen-Sweep auf 0.7.0 (rwu 16:50: "haben wir noch ein setting uebersehen?"). Der
    # Sweep vom 30.09. (d3 Optimum, ab d4 kippt es) lief auf rc1; 0.7.0 hat "Exact Lightning
    # MTP". Befund im omlx-Code (utils/model_loading.py): fuer Qwen 27B (hidden 5120, 64 Layer)
    # setzt omlx ADAPTIV mindestens Ceiling 4 und waehlt je Sequenz 1..max aus der Acceptance;
    # unser festes d3 ueberstimmt genau diesen Pfad. Maximum MAX_LIGHTNING_MTP_DRAFT_TOKENS = 8.
    # Fixture-Lauf 16:39 zeigte bei d3: tok/cycle 3.4 von max 4, d3-Acceptance noch 82-90 %
    # -> die Tiefe ist der Deckel, nicht die Acceptance.
    # Pruefstein je Zelle: Logzeile depth[d1=..,d2=..,..] zeigt die wirklich genutzte Tiefe.
    ("O", SOLSTICE, 4, None, {}),
    ("P", SOLSTICE, 5, None, {}),
    ("Q", SOLSTICE, 6, None, {}),
    ("R", SOLSTICE, 8, None, {}),
    ("S", SOLSTICE, None, None, {"mtp_enabled": True, "mtp_fixed_depth": None, "mtp_adaptive_max_depth": None, "_mtp_label": "adaptiv omlx-Default (27B => Ceiling 4)"}),
    ("T", SOLSTICE, None, None, {"mtp_enabled": True, "mtp_fixed_depth": None, "mtp_adaptive_max_depth": 6, "_mtp_label": "adaptiv<=6"}),
    ("U", SOLSTICE, None, None, {"mtp_enabled": True, "mtp_fixed_depth": None, "mtp_adaptive_max_depth": 8, "_mtp_label": "adaptiv<=8"}),
]

PROMPT = ("Erklaere in zusammenhaengendem Fliesstext, wie ein Schichtwaermetauscher "
          "funktioniert. Schreibe mindestens 600 Woerter und hoere nicht vorher auf.")


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


class Admin:
    """Admin-API spricht nur nach Cookie-Login (siehe Memory omlx-hf-cache-doppelalias)."""

    def __init__(self, key):
        self.op = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self._call("/admin/api/login", {"api_key": key})

    def _call(self, path, payload, method="POST"):
        req = urllib.request.Request(
            BASE + path, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method=method)
        return self.op.open(req, timeout=300)

    def reload(self):
        return self._call("/admin/api/reload", {}).status

    def clear_caches(self):
        for p in ("/admin/api/hot-cache/clear", "/admin/api/ssd-cache/clear"):
            try:
                self._call(p, {})
            except urllib.error.HTTPError as exc:
                log(f"  Cache-Clear {p}: HTTP {exc.code} (ignoriert)")

    def settings(self, mid, params):
        r = self._call(f"/admin/api/models/{mid}/settings", params, "PUT")
        s = json.loads(r.read())
        return s.get("settings", s)

    def unload(self, mid):
        try:
            self._call(f"/admin/api/models/{mid}/unload", {})
        except urllib.error.HTTPError as exc:
            log(f"  Unload {mid}: HTTP {exc.code} (ignoriert)")

    def settle(self, seconds=25):
        """Puffer nach dem Entladen.

        Das Entladen laeuft asynchron weiter, nachdem der Aufruf zurueckgekehrt ist.
        Setzt die naechste Zelle sofort neue Settings, kollidiert der dadurch
        ausgeloeste Reload mit dem noch laufenden Entladen -> HTTP 409 und die Zelle
        faellt aus (passiert am 01.10. bei Zelle B).

        Auf "loaded_count == 0" zu warten waere falsch: omlx haelt sein Default-Modell
        und laedt es nach, der Zaehler faellt also nie auf 0. Ein fester Puffer plus
        der 409-Retry im Warmup deckt den Fall vollstaendig ab.
        """
        time.sleep(seconds)
        try:
            h = json.loads(urllib.request.urlopen(BASE + "/health", timeout=10).read())
            e = h.get("engine_pool", {})
            log(f"  nach Entladen: {e.get('loaded_count')} geladen, "
                f"{e.get('current_model_memory', 0) / 2**30:.1f} GiB belegt")
        except Exception as exc:
            log(f"  Health nach Entladen nicht lesbar: {exc}")


def chat(mid, max_tokens, timeout=1800, effort=None):
    """Ein Completion-Request. Gibt (Sekunden, usage-Dict) zurueck.

    Der Bearer-Token ist Pflicht — ohne ihn antwortet 0.7.0 mit 401, und zwar
    erst beim Completion, nicht schon beim Setzen der Settings.
    `effort` geht als chat_template_kwargs.reasoning_effort ins Template (omlx-direkt
    funktioniert das, Bifrost verschluckt es — Memory bifrost-drops-chat-template-kwargs).
    usage wird um reasoning_tokens/reasoning_chars ergaenzt, damit die Thinking-Menge
    als Messwert erscheint und nicht nur die Zeit.
    """
    body = {"model": mid, "messages": [{"role": "user", "content": PROMPT}],
            "max_tokens": max_tokens, "temperature": 0.6, "top_p": 0.95, "top_k": 20}
    if effort:
        body["chat_template_kwargs"] = {"reasoning_effort": effort}
    req = urllib.request.Request(
        BASE + "/v1/chat/completions", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {os.environ['OMLX_API_KEY']}"}, method="POST")
    t0 = time.monotonic()
    d = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    usage = d.get("usage", {}) or {}
    msg = (d.get("choices") or [{}])[0].get("message", {}) or {}
    rc = msg.get("reasoning_content") or ""
    usage["reasoning_chars"] = len(rc)
    usage.setdefault("reasoning_tokens",
                     (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"))
    usage["content_chars"] = len(msg.get("content") or "")
    return time.monotonic() - t0, usage


def server_log_path():
    """Logdatei des brew-Dienstes; ohne sie kann MTP nicht belegt werden."""
    for p in (Path.home() / "Library/Logs/omlx/omlx.log",
              Path("/opt/homebrew/var/log/omlx.log"),
              Path.home() / ".omlx/logs/omlx.log"):
        if p.exists():
            return p
    return None


def mtp_evidence(logp, since_bytes):
    """Sucht ab Offset nach der MTP-accept-Zeile. Liefert (aktiv, Quote, Zeile)."""
    if not logp or not logp.exists():
        return None, None, "kein Serverlog gefunden"
    with logp.open("rb") as fh:
        fh.seek(since_bytes)
        tail = fh.read().decode("utf-8", "replace")
    hits = re.findall(r"accept=(\d+)/(\d+)\s*\(([\d.]+)%\)", tail)
    if not hits:
        return False, None, "keine accept=-Zeile im Log"
    acc = sum(int(a) for a, _, _ in hits)
    gen = sum(int(b) for _, b, _ in hits)
    return True, (100.0 * acc / gen if gen else 0.0), f"{len(hits)} MTP-Zyklen, {acc}/{gen}"


def logsize(logp):
    return logp.stat().st_size if logp and logp.exists() else 0


def pressure_evidence(logp, since_bytes):
    """Hat omlx waehrend der Zelle den Memory-Guard hochgeschaltet?

    Logzeile `Memory pressure level: ok -> soft (… ceiling=21.1GB)` (01.10., 15:47:59) —
    danach drosselt omlx den Prefill und der Durchsatz bricht ein (Zelle J: 14,4 -> 10,9 ->
    9,9 tok/s). Eine Zelle mit dieser Zeile misst die Drosselung, nicht das Modell.
    """
    if not logp or not logp.exists():
        return None
    with logp.open("rb") as fh:
        fh.seek(since_bytes)
        tail = fh.read().decode("utf-8", "replace")
    m = re.findall(r"Memory pressure level: \w+ -> (soft|hard|critical)[^\n]*", tail)
    return m[-1] if m else None


def ceiling_gib():
    h = json.loads(urllib.request.urlopen(BASE + "/health", timeout=10).read())
    return h.get("engine_pool", {}).get("final_ceiling", 0) / 2**30


def ensure_headroom(adm, min_gib=25.0):
    """Vor jeder Zelle: Ceiling pruefen, bei Einbruch omlx neu starten.

    Der omlx-Prozess akkumuliert Metal-Buffer ueber Modellwechsel (phys_footprint_peak
    26 GB bei 16-GB-Modell); nach 2 Wechseln fiel das Ceiling am 01.10. von 28 auf 21 GiB.
    Das loest nur ein Dienst-Neustart (launchd, ppid 1). Kostet ~15 s und einen TTS-Blip —
    billiger als eine gedrosselte, wertlose Zelle.
    """
    c = ceiling_gib()
    if c >= min_gib:
        log(f"  Ceiling {c:.1f} GiB — ok")
        return
    log(f"  Ceiling {c:.1f} GiB < {min_gib} — Buffer-Reste, omlx wird neu gestartet")
    subprocess.run(["brew", "services", "restart", "jundot/omlx/omlx"],
                   capture_output=True, text=True)
    for _ in range(40):
        time.sleep(5)
        try:
            c = ceiling_gib()
            if c >= min_gib:
                log(f"  omlx neu: Ceiling {c:.1f} GiB")
                adm.__init__(os.environ["OMLX_API_KEY"])   # neues Cookie nach Neustart
                return
        except Exception:
            pass
    log("  WARNUNG: Ceiling nach Neustart weiter niedrig — Zelle wird als DROSSELUNG-RISIKO markiert")


def main():
    # Zellen gezielt nachholen: run_070_throughput.py E F G
    # (Zellen koennen am Memory-Ceiling scheitern, wenn ein vorheriges Modell den
    #  Speicher noch haelt — dann Server neu starten und nur die Ausfaelle fahren.)
    wanted = {a.upper() for a in sys.argv[1:]} or None
    cells = [c for c in CELLS if not wanted or c[0] in wanted]
    if wanted:
        missing = wanted - {c[0] for c in CELLS}
        if missing:
            sys.exit(f"Unbekannte Zellen: {', '.join(sorted(missing))}")
    OUT.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("OMLX_API_KEY")
    if not key:
        sys.exit("OMLX_API_KEY fehlt — ~/.config/omlx/.env sourcen")

    ver = subprocess.run(["brew", "list", "--versions", "omlx"],
                         capture_output=True, text=True).stdout.strip()
    log(f"omlx: {ver}")
    if "0.7.0 " not in ver + " " and not ver.endswith("0.7.0"):
        log("WARNUNG: 0.7.0 nicht als installierte Version erkannt — Messung trotzdem,"
            " aber Zuordnung im Report pruefen")

    adm = Admin(key)
    log(f"Modell-Rescan: HTTP {adm.reload()}")

    # Vorabcheck: eine falsch geschriebene Modell-ID laesst omlx jeden Request mit
    # "Model not found" quittieren — die Matrix rast dann in Sekunden durch und
    # produziert lauter Nullzeilen, die wie ein Messergebnis aussehen.
    req = urllib.request.Request(BASE + "/v1/models",
                                 headers={"Authorization": f"Bearer {key}"})
    known = {m["id"] for m in json.loads(urllib.request.urlopen(req, timeout=30).read())["data"]}
    unknown = sorted({c[1] for c in cells} - known)
    if unknown:
        sys.exit("ABBRUCH: unbekannte Modell-IDs: " + ", ".join(unknown)
                 + "\nRegistriert sind: " + ", ".join(sorted(known)))
    log(f"Zellen: {', '.join(c[0] for c in cells)} | Modell-IDs geprueft: alle {len({c[1] for c in cells})} registriert")

    logp = server_log_path()
    log(f"Serverlog: {logp or 'NICHT GEFUNDEN — MTP-Belege entfallen'}")

    results = []
    for cell, mid, depth, ref, extra in cells:
        mtp_label = extra.get("_mtp_label") or (f"fixed {depth}" if depth else "aus")
        label = f"{cell}: {mid.split('--')[-1][:48]} MTP={mtp_label}" + (f" +{[k for k in extra if not k.startswith('_')]}" if extra else "") + (f" effort={extra.get('_effort')}" if extra.get("_effort") else "")
        log(f"=== {label} ===")
        params = {"enable_thinking": False, "max_tokens": 2048,
                  "max_context_window": 32768, "temperature": 0.6, "top_p": 0.95,
                  "top_k": 20, "repetition_penalty": 1.0,  # != 1.0 wuerde MTP still abschalten
                  "specprefill_enabled": False,
                  "turboquant_kv_enabled": False,  # explizit aus, sonst bleibt der Vorlauf-Wert haengen
                  "mtp_enabled": bool(depth)}
        if depth:
            params["mtp_fixed_depth"] = depth
        extra = dict(extra)
        effort = extra.pop("_effort", None)   # kein omlx-Setting, geht per Request
        extra.pop("_mtp_label", None)         # nur Beschriftung
        params.update(extra)
        mtp_on = bool(params.get("mtp_enabled"))   # auch adaptiv (ohne fixed depth)
        try:
            applied = adm.settings(mid, params)
        except urllib.error.HTTPError as exc:
            log(f"  Settings fehlgeschlagen: HTTP {exc.code} — Zelle uebersprungen")
            results.append({"cell": cell, "model": mid, "mtp": depth,
                            "status": f"SETTINGS-HTTP-{exc.code}"})
            continue
        got = {k: applied.get(k) for k in ("mtp_enabled", "mtp_fixed_depth",
                                           "enable_thinking", "repetition_penalty",
                                           "turboquant_kv_enabled", "turboquant_kv_bits")}
        # Pruefstein statt Glauben: was gefordert war, muss zurueckgelesen so dastehen
        bad = [k for k, v in params.items() if k in applied and applied.get(k) != v
               and k in ("mtp_enabled", "turboquant_kv_enabled", "turboquant_kv_bits", "temperature")]
        if bad:
            log(f"  SETTINGS NICHT UEBERNOMMEN {bad} — Zelle uebersprungen")
            results.append({"cell": cell, "model": mid, "mtp": depth, "status": "SETTINGS-MISMATCH"})
            continue
        log(f"  Settings angewandt: {got}")

        ensure_headroom(adm)
        adm.clear_caches()
        # Warmup laedt das Modell. 409/507 sind transient (Reload laeuft noch bzw.
        # ein anderes Modell haelt noch Speicher) — erst retryen, dann aufgeben.
        usage = None
        for attempt in range(1, 4):
            try:
                dur, usage = chat(mid, 64, effort=effort)
                break
            except (urllib.error.HTTPError, urllib.error.URLError,
                    http.client.HTTPException, ConnectionError) as exc:
                code = getattr(exc, "code", None)
                transient = code in (409, 429, 503, 507) or code is None
                if transient and attempt < 3:
                    log(f"  Warmup {type(exc).__name__} {code or ''} "
                        f"(Versuch {attempt}/3) — 30s warten")
                    time.sleep(30)
                    continue
                log(f"  Warmup {type(exc).__name__} {code or ''} — Zelle uebersprungen")
                results.append({"cell": cell, "model": mid, "mtp": depth,
                                "status": f"WARMUP-{code or type(exc).__name__}"})
                break
        if usage is None:
            continue
        log(f"  Warmup ok ({dur:.1f}s, load={usage.get('model_load_duration')}s)")

        mark = logsize(logp)
        runs = []
        for i in range(REPS):
            adm.clear_caches()
            try:
                dur, usage = chat(mid, 4096 if params.get("enable_thinking") else 2048, effort=effort)
            except (urllib.error.HTTPError, urllib.error.URLError,
                    http.client.HTTPException, ConnectionError) as exc:
                log(f"  Lauf {i+1}/{REPS} abgebrochen ({type(exc).__name__}) — verworfen")
                continue
            ct = usage.get("completion_tokens") or 0
            # omlx rechnet Prefill und Ladezeit selbst heraus — das ist die Groesse,
            # auf der auch die rc1-Referenzwerte beruhen. Die Wanduhr bleibt als
            # Gegenprobe daneben stehen, damit ein Ausreisser auffaellt.
            tps = usage.get("generation_tokens_per_second") or 0.0
            wall = ct / dur if dur > 0 else 0.0
            runs.append({"s": round(dur, 2), "completion_tokens": ct,
                         "tok_s": round(tps, 2), "wall_tok_s": round(wall, 2),
                         "generation_duration": usage.get("generation_duration"),
                         "ttft": usage.get("time_to_first_token"),
                         "prompt_tok_s": usage.get("prompt_tokens_per_second"),
                         "reasoning_tokens": usage.get("reasoning_tokens"),
                         "reasoning_chars": usage.get("reasoning_chars"),
                         "content_chars": usage.get("content_chars"),
                         "effort": effort,
                         "prompt_tokens": usage.get("prompt_tokens")})
            log(f"  Lauf {i+1}/{REPS}: {ct} tok | {tps:.1f} tok/s (gen) "
                f"| {wall:.1f} tok/s (wall) | ttft {usage.get('time_to_first_token')}s"
                f" | think {usage.get('reasoning_tokens') or '-'} tok/{usage.get('reasoning_chars',0)} ch, answer {usage.get('content_chars',0)} ch")

        vals = [r["tok_s"] for r in runs if r["completion_tokens"] > 0 and r["tok_s"]]
        median = sorted(vals)[len(vals) // 2] if vals else 0.0
        active, quote, note = mtp_evidence(logp, mark) if mtp_on else (None, None, "")
        if mtp_on and active is False:
            log(f"  MTP-PRUEFSTEIN NEGATIV: {note} -> Zelle gilt als MTP-INAKTIV")
        pressure = pressure_evidence(logp, mark)
        if pressure:
            log(f"  DROSSELUNG: omlx meldete '{pressure[:90]}' — Median ungueltig, "
                f"Einzellaeufe {vals} bleiben zur Einsicht")

        row = {"cell": cell, "model": mid, "mtp": depth, "mtp_mode": mtp_label,
               "median_tok_s": median, "runs": runs, "rc1_reference": ref,
               "mtp_active": active, "mtp_acceptance_pct": quote, "mtp_note": note,
               "pressure": pressure, "prompt_tokens": runs[0].get("prompt_tokens") if runs else None,
               "status": ("DROSSELUNG" if pressure else
                          "MTP-INAKTIV" if (mtp_on and active is False) else "OK")}
        if ref:
            row["gain_vs_rc1"] = round(100 * (median - ref) / ref, 1)
            log(f"  Median {median:.1f} tok/s | rc1 war {ref} -> {row['gain_vs_rc1']:+.1f} %")
        else:
            log(f"  Median {median:.1f} tok/s")
        results.append(row)
        adm.unload(mid)
        adm.settle()
        (OUT / (f"throughput-{''.join(c[0] for c in cells)}.json")).write_text(
            json.dumps({"omlx": ver, "measured": datetime.now().isoformat(),
                        "cells": results}, indent=2, ensure_ascii=False))

    log("=== MATRIX FERTIG ===")
    for r in results:
        ref = f" (rc1: {r['rc1_reference']}, {r.get('gain_vs_rc1'):+}%)" if r.get("rc1_reference") else ""
        log(f"  {r['cell']}  {r.get('median_tok_s', 0):6.1f} tok/s  {r['status']}{ref}")
    log(f"Ergebnis: {OUT}/throughput-{''.join(c[0] for c in cells)}.json")


if __name__ == "__main__":
    main()
