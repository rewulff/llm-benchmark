#!/usr/bin/env bash
# Fährt die beiden offenen Batches seriell. Download ist fertig (byte-genau geprüft),
# Settings sind gesetzt — dieses Skript wartet auf nichts mehr.
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ~/.config/omlx/.env; set +a
log() { echo "[$(date +%H:%M:%S)] $*"; }

ORNITH='Ornith-1.5-35B-A3B-uncensored-MLX-MXFP4'
TC='ThinkingCap-Qwen3.8-27B-mlx-nvfp4'

# --- Ornith nothink: Bedingung idempotent setzen, dann die 7 offenen Fixtures ---
python3 - "$ORNITH" <<'PY'
import json,os,sys,urllib.request,http.cookiejar
key=os.environ['OMLX_API_KEY']; mid=sys.argv[1]
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
r=op.open(urllib.request.Request(f'http://127.0.0.1:1235/admin/api/models/{mid}/settings',
    data=json.dumps({'enable_thinking':False,'max_tokens':16384,'temperature':0.6,
                     'top_p':0.95,'top_k':20,'repetition_penalty':1.0}).encode(),
    headers={'Content-Type':'application/json'},method='PUT'))
s=json.loads(r.read()); s=s.get('settings',s)
print('Ornith nothink-Bedingung:',{k:s.get(k) for k in ('enable_thinking','max_tokens','temperature')})
PY

log "Ornith nothink — 7 offene Fixtures"
python3 run_king_matrix.py --model "$ORNITH" --label ornith15-mxfp4-nothink \
  --fixtures c1-dependent-pipeline,v6-custom-constraint,v6-ambiguity-probe,v6-produktiv-fqdn-bug,r1-offline-research,v6-architecture-choice,a5-long-edit \
  --unload-after
log "Ornith nothink fertig"

# --- Beleg, dass reasoning_effort bei ThinkingCap im Generierungspfad ankommt ---
log "ThinkingCap Settings-Beleg"
python3 - "$TC" <<'PY'
import json,os,sys,time,urllib.request,urllib.error
key=os.environ['OMLX_API_KEY']; mid=sys.argv[1]
for attempt in range(10):
    req=urllib.request.Request('http://127.0.0.1:1235/v1/chat/completions',method='POST',
        data=json.dumps({'model':mid,'max_tokens':400,
            'messages':[{'role':'user','content':'Was ist 17*3? Antworte knapp.'}]}).encode(),
        headers={'Content-Type':'application/json','Authorization':f'Bearer {key}'})
    try:
        d=json.loads(urllib.request.urlopen(req,timeout=1800).read())
    except urllib.error.HTTPError as e:
        print(f'  Versuch {attempt+1}: HTTP {e.code} — 120s warten'); time.sleep(120); continue
    m=d['choices'][0]['message']; u=d.get('usage',{})
    print('  content=%r | reasoning_len=%d | completion=%s | load=%ss'
          % ((m.get('content') or '')[:60], len(m.get('reasoning_content') or ''),
             u.get('completion_tokens'), u.get('model_load_duration')))
    print('  Antwort korrekt:', '51' in (m.get('content') or ''),
          '| Thinking aktiv:', bool(m.get('reasoning_content')))
    break
PY

log "ThinkingCap-Matrix — 10 Fixtures"
python3 run_king_matrix.py --model "$TC" --label thinkingcap-qwen38-27b --timeout 2400 --unload-after
log "ALLE BATCHES DURCH"
