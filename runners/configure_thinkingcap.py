#!/usr/bin/env python3
"""Wartet auf die omlx-Registrierung von ThinkingCap-Qwen3.8-27B und stellt es ein.

Warum nötig (aus den mitgelieferten Modelldateien belegt):
- chat_template kennt reasoning_effort mit Default 'xhigh' und wirft bei unbekanntem
  Wert eine Template-Exception. Ohne Vorgabe läuft jede Aufgabe im teuersten Denkmodus.
  Gesetzt wird 'medium' über chat_template_kwargs + forced_ct_kwargs, weil opencode
  selbst keine Template-kwargs sendet.
- generation_config.json des Repos: temperature 1.0, top_p 0.95, top_k 20. Für die
  Coding-Matrix wird temperature 0.6 gefahren (Vergleichbarkeit zur Ornith-Matrix);
  der Herstellerwert ist im Report ausgewiesen.
- repetition_penalty MUSS 1.0 bleiben: ein Penalty != 1.0 deaktiviert in omlx die
  MTP-Beschleunigung still (bekannte Falle). MTP ist hier in den Checkpoint gemergt.
- max_tokens 16384 (Thinking-Budget), max_context_window 65536 (Agent-Kontext;
  262144 wäre auf 48 GB ein Speicherrisiko).
"""
import json, os, sys, time, urllib.request, http.cookiejar

API = "http://127.0.0.1:1235"
KEY = os.environ["OMLX_API_KEY"]
SETTINGS = {
    "enable_thinking": True,
    "chat_template_kwargs": {"reasoning_effort": "medium"},
    "forced_ct_kwargs": ["reasoning_effort"],
    "max_tokens": 16384,
    "max_context_window": 65536,
    "temperature": 0.6,
    "top_p": 0.95,
    "top_k": 20,
    "repetition_penalty": 1.0,
}


def models():
    req = urllib.request.Request(f"{API}/v1/models", headers={"Authorization": f"Bearer {KEY}"})
    return [m["id"] for m in json.loads(urllib.request.urlopen(req, timeout=30).read())["data"]]


def find():
    return next((m for m in models() if "ThinkingCap" in m and "3.8" in m), None)


deadline = time.time() + 3 * 3600
mid = find()
while not mid and time.time() < deadline:
    time.sleep(30)
    mid = find()
if not mid:
    print("ThinkingCap nicht registriert — Timeout", file=sys.stderr)
    sys.exit(1)
print(f"registriert als: {mid}", flush=True)

cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request(f"{API}/admin/api/login",
        data=json.dumps({"api_key": KEY}).encode(),
        headers={"Content-Type": "application/json"}, method="POST"))
r = op.open(urllib.request.Request(f"{API}/admin/api/models/{mid}/settings",
            data=json.dumps(SETTINGS).encode(),
            headers={"Content-Type": "application/json"}, method="PUT"))
s = json.loads(r.read())
s = s.get("settings", s)
print("gesetzt:", json.dumps({k: s.get(k) for k in SETTINGS}, ensure_ascii=False), flush=True)

# Beleg, dass die Einstellung im Generierungspfad ankommt (nicht nur im Settings-Objekt).
# Erst wenn alle Shards da sind — omlx listet ein Modell schon während des Downloads —
# und mit Retry, weil 507 (memory ceiling) auftritt solange ein anderes Modell geladen ist.
from pathlib import Path

MODEL_DIR = Path.home() / "omlx-test-models/airagrp/ThinkingCap-Qwen3.8-27B-mlx-nvfp4"


def shards_missing():
    idx = MODEL_DIR / "model.safetensors.index.json"
    if not idx.exists():
        return ["<index fehlt>"]
    need = set(json.loads(idx.read_text())["weight_map"].values())
    return sorted(f for f in need if not (MODEL_DIR / f).exists())


deadline = time.time() + 3 * 3600
while (miss := shards_missing()) and time.time() < deadline:
    print(f"warte auf {len(miss)} Shard(s): {miss[:3]}", flush=True)
    time.sleep(60)
if miss:
    print(f"ABBRUCH: Shards fehlen weiterhin: {miss}", file=sys.stderr)
    sys.exit(1)
print("alle Shards vorhanden", flush=True)

while time.time() < deadline:
    req = urllib.request.Request(f"{API}/v1/chat/completions", method="POST",
        data=json.dumps({"model": mid, "max_tokens": 400,
                         "messages": [{"role": "user", "content": "Was ist 17*3? Antworte knapp."}]}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=1800).read())
    except urllib.error.HTTPError as exc:
        if exc.code == 507:
            print("507 memory ceiling — anderes Modell hält den Speicher, "
                  "neuer Versuch in 120s", flush=True)
            time.sleep(120)
            continue
        raise
    m = d["choices"][0]["message"]
    u = d.get("usage", {})
    rl = len(m.get("reasoning_content") or "")
    print("smoke: content=%r | reasoning_len=%d | completion_tokens=%s | load=%ss"
          % ((m.get("content") or "")[:80], rl, u.get("completion_tokens"),
             u.get("model_load_duration")), flush=True)
    ok_answer = "51" in (m.get("content") or "")
    print("Antwort korrekt:", ok_answer, "| Thinking aktiv (reasoning_content):", rl > 0, flush=True)
    sys.exit(0 if ok_answer else 2)
print("ABBRUCH: Smoke nie erfolgreich (dauerhaft 507)", file=sys.stderr)
sys.exit(1)
