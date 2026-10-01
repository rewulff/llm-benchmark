#!/usr/bin/env bash
# TurboQuant-KV-Kosten bei Ornith 6-bit, sauber isoliert:
# identisch zu ornith15-official-6bit-nothink (10/10, 8,1 min), EINZIGE Aenderung ist
# turboquant_kv_enabled + bits. Beantwortet: lohnt KV-Quantisierung bei begrenztem RAM?
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ~/.config/omlx/.env; set +a
MID='ornith-ai--Ornith-1.5-35B-A3B-MLX-6bit'
log() { echo "[$(date +%H:%M:%S)] $*"; }
while pgrep -f "run_king_matrix.py" >/dev/null; do sleep 30; done

for BITS in 3 4; do
python3 - "$MID" "$BITS" <<'PY'
import json,os,sys,urllib.request,http.cookiejar
key=os.environ['OMLX_API_KEY']; mid,bits=sys.argv[1],float(sys.argv[2])
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
p={'enable_thinking':False,'turboquant_kv_enabled':True,'turboquant_kv_bits':bits,
   'turboquant_skip_last':True,'max_tokens':16384,'max_context_window':65536,
   'temperature':0.0,'top_p':1.0,'top_k':0,'repetition_penalty':1.0,'force_sampling':True,
   'specprefill_enabled':False,'mtp_enabled':False}
r=op.open(urllib.request.Request(f'http://127.0.0.1:1235/admin/api/models/{mid}/settings',
    data=json.dumps(p).encode(),headers={'Content-Type':'application/json'},method='PUT'))
s=json.loads(r.read()); s=s.get('settings',s)
print(f'TurboQuant {bits}bit:',json.dumps({k:s.get(k) for k in ('turboquant_kv_enabled','turboquant_kv_bits','temperature','enable_thinking')},ensure_ascii=False))
PY
  log "Matrix TurboQuant ${BITS}bit"
  python3 run_king_matrix.py --model "$MID" --label "ornith15-6bit-tq${BITS}bit-temp0" --timeout 1800 --unload-after
done

# Referenzbedingung wiederherstellen (TurboQuant aus) — sonst bleibt der Knecht quantisiert
python3 - "$MID" <<'PY'
import json,os,sys,urllib.request,http.cookiejar
key=os.environ['OMLX_API_KEY']; mid=sys.argv[1]
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
op.open(urllib.request.Request(f'http://127.0.0.1:1235/admin/api/models/{mid}/settings',
    data=json.dumps({'turboquant_kv_enabled':False,'temperature':0.6,'top_p':0.95,'top_k':20,
                     'force_sampling':False}).encode(),
    headers={'Content-Type':'application/json'},method='PUT'))
print('Referenzbedingung wiederhergestellt (TurboQuant aus, temp 0.6)')
PY
log "TQ-VERGLEICH FERTIG"
