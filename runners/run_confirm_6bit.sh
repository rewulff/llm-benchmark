#!/usr/bin/env bash
# Bestaetigungslauf fuer den Knecht-Kandidaten: Ornith 1.5 offiziell 6-bit, nothink.
# Grund: 10/10 stammt aus EINEM Lauf, und wir haben am 30.09. ±1-2 Fixtures Streuung
# bei temperature 0.6 gemessen. Hier temperature 0 (deterministisch) + zwei Wiederholungen,
# damit die Knecht-Entscheidung nicht auf einer Momentaufnahme steht.
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ~/.config/omlx/.env; set +a
MID='ornith-ai--Ornith-1.5-35B-A3B-MLX-6bit'
log() { echo "[$(date +%H:%M:%S)] $*"; }

log "warte auf freie Maschine"
while pgrep -f "run_king_matrix.py" >/dev/null || pgrep -f "run_effort_compare.sh" >/dev/null \
   || pgrep -f "run_jetbrains.sh" >/dev/null || pgrep -f "run_quant_compare.sh" >/dev/null; do sleep 30; done
log "frei"

python3 - "$MID" <<'PY'
import json,os,sys,urllib.request,http.cookiejar
key=os.environ['OMLX_API_KEY']; mid=sys.argv[1]
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
p={'enable_thinking':False,'max_tokens':16384,'max_context_window':65536,
   'temperature':0.0,'top_p':1.0,'top_k':0,'repetition_penalty':1.0,
   'specprefill_enabled':False,'mtp_enabled':False,'force_sampling':True}
r=op.open(urllib.request.Request(f'http://127.0.0.1:1235/admin/api/models/{mid}/settings',
    data=json.dumps(p).encode(),headers={'Content-Type':'application/json'},method='PUT'))
s=json.loads(r.read()); s=s.get('settings',s)
print('Bedingung (deterministisch):',json.dumps({k:s.get(k) for k in p},ensure_ascii=False))
PY

for i in 1 2; do
  log "Bestaetigungslauf $i/2 (temperature 0)"
  python3 run_king_matrix.py --model "$MID" --label "ornith15-6bit-temp0-run$i" --timeout 1800 --unload-after
done
log "BESTAETIGUNG FERTIG"
