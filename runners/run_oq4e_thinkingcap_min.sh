#!/usr/bin/env bash
# ThinkingCap oQ4e-mtp + MTP d3 — Minimalpruefung (rwu, 01.10.: "thinkcap nur minimum
# testen, ornith voll"). Drei Fixtures statt zehn: zwei schnelle Typen plus der
# einzige FAIL der Referenz (a5-long-edit in thinkingcap-qwen38-mtp-d3, 9/10).
# Referenz-Sampling: temp 0.6. Laeuft erst an, wenn der Ornith-Lauf durch ist.
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ~/.config/omlx/.env; set +a
log() { echo "[$(date +%H:%M:%S)] $*"; }

MID=chriswessels--ThinkingCap-Qwen3.8-27B-oQ4e-mtp
LABEL=thinkingcap-oq4e-mtp-d3-min
FIX=a2-bugfix,v6-custom-constraint,a5-long-edit

log "warte auf Ende des Ornith-Laufs"
while pgrep -f "run_king_matrix.py" >/dev/null 2>&1; do sleep 20; done
log "Ornith durch — 30s Puffer (Entladen laeuft asynchron, sonst HTTP 409)"
sleep 30

if pgrep -f "llama-server" >/dev/null; then
  log "ABBRUCH: llama-server laeuft und blockiert den Speicher"
  exit 1
fi

log "=== $LABEL (temp 0.6, MTP d3, Fixtures: $FIX) ==="
python3 - "$MID" <<'PY'
import json,os,sys,urllib.request,http.cookiejar
mid=sys.argv[1]; key=os.environ['OMLX_API_KEY']
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
p={'enable_thinking':False,'max_tokens':16384,'max_context_window':65536,
   'temperature':0.6,'top_p':0.95,'top_k':20,'repetition_penalty':1.0,
   'specprefill_enabled':False,'mtp_enabled':True,'mtp_fixed_depth':3}
r=op.open(urllib.request.Request(f'http://127.0.0.1:1235/admin/api/models/{mid}/settings',
    data=json.dumps(p).encode(),headers={'Content-Type':'application/json'},method='PUT'))
s=json.loads(r.read()); s=s.get('settings',s)
got={k:s.get(k) for k in ('temperature','mtp_enabled','mtp_fixed_depth','enable_thinking')}
print('  Settings:',json.dumps(got))
if got.get('mtp_enabled') is not True or got.get('temperature')!=0.6:
    sys.exit('  ABBRUCH: Settings nicht uebernommen')
PY
[ $? -ne 0 ] && exit 1
python3 run_king_matrix.py --model "$MID" --label "$LABEL" --fixtures "$FIX" --timeout 1800 --unload-after
log "THINKINGCAP-MIN FERTIG"
