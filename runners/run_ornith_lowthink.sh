#!/usr/bin/env bash
# Ornith 1.5 offiziell 6-bit, THINK mit Denkbremse im Chat-Template (Variante 1: sanft,
# kein hartes Abschneiden) + TurboQuant-KV 3-bit fuer KV-Spielraum.
# Vergleichsbasis: ornith15-official-6bit-nothink (10/10, 8,1 min, TQ aus).
# Enthaelt r1-offline-research = Distract-Test.
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ~/.config/omlx/.env; set +a
MID='ornith15-6bit-lowthink'
log() { echo "[$(date +%H:%M:%S)] $*"; }

log "warte auf freie Maschine"
while pgrep -f "run_king_matrix.py" >/dev/null || pgrep -f "run_effort_compare.sh" >/dev/null \
   || pgrep -f "run_jetbrains.sh" >/dev/null || pgrep -f "run_confirm_6bit.sh" >/dev/null; do sleep 30; done
log "frei — Reload jetzt gefahrlos (kein Batch aktiv)"

python3 - <<'PY'
import json,os,urllib.request,http.cookiejar
key=os.environ['OMLX_API_KEY']
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
r=op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/reload',
    data=b'{}',headers={'Content-Type':'application/json'},method='POST'))
print('reload:',r.status,r.read()[:90].decode(errors='replace'))
PY

python3 - "$MID" <<'PY'
import json,os,sys,urllib.request,http.cookiejar
key=os.environ['OMLX_API_KEY']; mid=sys.argv[1]
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
p={'enable_thinking':True,                       # Bremse steckt im Template, nicht im Schalter
   'turboquant_kv_enabled':True,'turboquant_kv_bits':3.0,'turboquant_skip_last':True,
   'max_tokens':16384,'max_context_window':65536,
   'temperature':0.6,'top_p':0.95,'top_k':20,'repetition_penalty':1.0,
   'specprefill_enabled':False,'mtp_enabled':False}
r=op.open(urllib.request.Request(f'http://127.0.0.1:1235/admin/api/models/{mid}/settings',
    data=json.dumps(p).encode(),headers={'Content-Type':'application/json'},method='PUT'))
s=json.loads(r.read()); s=s.get('settings',s)
print('Bedingung:',json.dumps({k:s.get(k) for k in p},ensure_ascii=False))
PY

log "Matrix ornith15-6bit-lowthink-tq3 (inkl. Distract-Test r1)"
python3 run_king_matrix.py --model "$MID" --label ornith15-6bit-lowthink-tq3 --timeout 1800 --unload-after
log "LOWTHINK FERTIG"
