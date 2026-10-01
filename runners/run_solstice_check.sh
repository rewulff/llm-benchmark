#!/usr/bin/env bash
# Solstice-Pruefung (rwu, 01.10.2026): "mit deren vorgeschlagenen Settings testen" —
# Kandidat fuer einen kuenftigen M6-Mini 24/32 GB. Zwei Stufen, sequenziell (RAM):
#   1. Durchsatz-Zellen H/I/J in run_070_throughput.py (deren Settings mit/ohne TQ-KV,
#      ThinkingCap oQ4e als Referenz im selben Lauf)
#   2. Fixture-Minimum a2 / v6-custom / a5 — dieselben drei wie bei ThinkingCap oQ4e
#      (thinkingcap-oq4e-mtp-d3-min: 2/3, a5 7/8), temp 0.6, nothink, TQ-KV 4-bit
# Vorab geprueft: oQ4e = echtes affine-4bit+Overrides; KEIN MTP-Head; Benchmarks der
# Modellkarte sind aus Alibabas Qwen3.8-27B-Karte kopiert; Anvil (deren Engine) ist ein
# llama.cpp-Build und kann dieses MLX-Modell nicht laden -> Test ausschliesslich in omlx.
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ~/.config/omlx/.env; set +a
log() { echo "[$(date +%H:%M:%S)] $*"; }
MID="Solstice-AI--Qwen3.8-27B-TURBO-Fable-Cold-Fusion-735-882-Heretic-Uncensored-NM-DAU-mlx-oQ4e-1M"

# Vorabchecks (alle drei am 01.10. aus Fehlern gelernt):
# (a) Port statt `pgrep -f`: Agenten-Prompts enthalten den String "llama-server" -> Fehlalarm.
lsof -nP -iTCP:1236 -sTCP:LISTEN >/dev/null 2>&1 && { log "ABBRUCH: llama-server lauscht auf :1236 (Speicher)"; exit 1; }
# (b) Benchmark-Prozesse: Muster OHNE ^python3-Anker (Runner laeuft als voller Interpreter-Pfad),
#     dafuer Claude-Sessions per comm ausgeschlossen — sonst matcht pgrep deren Prompts.
if ps -eo comm=,args= | grep -E "run_king_matrix|run_070_throughput|opencode run" | grep -vqE "^claude|grep"; then
  log "ABBRUCH: anderer Benchmark-/opencode-Prozess aktiv"; exit 1
fi
# (c) omlx-Pool: fremde Modelle geladen oder Ceiling eingebrochen (Metal-Buffer nach Entladen,
#     loest nur ein Dienst-Neustart) -> nicht messen, sonst Prefill-Drosselung und 507 statt Zahlen.
python3 - <<'PY' || exit 1
import json,os,sys,urllib.request,http.cookiejar
key=os.environ['OMLX_API_KEY']
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
ms=json.loads(op.open('http://127.0.0.1:1235/admin/api/models',timeout=30).read()); ms=ms.get('models',ms)
loaded=[m['id'] for m in ms if isinstance(m,dict) and m.get('loaded') and 'TTS' not in m['id']]
h=json.loads(urllib.request.urlopen('http://127.0.0.1:1235/health',timeout=10).read()); ceil=h['engine_pool']['final_ceiling']/2**30
if loaded: sys.exit(f"ABBRUCH: fremde Modelle geladen (andere Session?): {loaded} — Lastfenster abstimmen")
if ceil < 25: sys.exit(f"ABBRUCH: omlx-Ceiling nur {ceil:.1f} GiB (<25) — Metal-Buffer haengen, Dienst neu starten: brew services restart jundot/omlx/omlx")
print(f"  Pool frei: Ceiling {ceil:.1f} GiB, keine fremden Modelle")
PY

log "=== Stufe 1: Durchsatz H/I/J ==="
# Exit-Code pruefen: am 01.10. starb Stufe 1 im omlx-Shutdown (Connection refused) und
# der Wrapper meldete trotzdem "fertig" und fuhr Stufe 2 — ohne Mediane, unter Speicherdruck.
if ! python3 run_070_throughput.py H I J; then
  log "ABBRUCH: Stufe 1 ist gescheitert (Exit != 0) — keine Stufe 2 ohne Durchsatzwerte"; exit 1
fi
log "Stufe 1 fertig — 30 s Puffer (Entladen asynchron)"; sleep 30

log "=== Stufe 2: Fixture-Minimum (deren Settings + TQ-KV 4-bit) ==="
python3 - "$MID" <<'PY'
import json,os,sys,urllib.request,http.cookiejar
mid=sys.argv[1]; key=os.environ['OMLX_API_KEY']
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
p={'enable_thinking':False,'max_tokens':16384,'max_context_window':65536,
   'temperature':0.6,'top_p':0.95,'top_k':20,'repetition_penalty':1.0,
   'specprefill_enabled':False,'mtp_enabled':False,
   'turboquant_kv_enabled':True,'turboquant_kv_bits':4,'turboquant_skip_last':True}
r=op.open(urllib.request.Request(f'http://127.0.0.1:1235/admin/api/models/{mid}/settings',
    data=json.dumps(p).encode(),headers={'Content-Type':'application/json'},method='PUT'))
s=json.loads(r.read()); s=s.get('settings',s)
got={k:s.get(k) for k in ('temperature','enable_thinking','turboquant_kv_enabled','turboquant_kv_bits','mtp_enabled')}
print('  Settings:',json.dumps(got))
if got.get('turboquant_kv_enabled') is not True or got.get('temperature')!=0.6:
    sys.exit('  ABBRUCH: Settings nicht uebernommen')
PY
[ $? -ne 0 ] && exit 1
python3 run_king_matrix.py --model "$MID" --label solstice-oq4e-tq4-min \
  --fixtures a2-bugfix,v6-custom-constraint,a5-long-edit --timeout 1800 --unload-after
log "SOLSTICE-CHECK FERTIG"
