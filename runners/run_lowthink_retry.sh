#!/usr/bin/env bash
# Wiederholung ornith15-6bit-lowthink-tq3. Der erste Versuch (01.10. 04:06) ist unbrauchbar:
#  - Akku ging nachts leer -> v6-architecture-choice 15726s statt ~80s (Throttling),
#    a5-long-edit brach danach nach 39s mit 2 Steps ab (Artefakt, kein Modellergebnis)
#  - Thinking war NICHT nachweisbar (reasoning_tokens 0, reasoning_parser null)
# Diesmal mit reasoning_parser + Prüfstein VOR dem Batch: ohne messbares Thinking kein Lauf.
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ~/.config/omlx/.env; set +a
MID='ornith15-6bit-lowthink'
log() { echo "[$(date +%H:%M:%S)] $*"; }

log "warte auf freie Maschine"
while pgrep -f "run_king_matrix.py" >/dev/null; do sleep 30; done

python3 - "$MID" <<'PY'
import json,os,sys,time,urllib.request,http.cookiejar
key=os.environ['OMLX_API_KEY']; mid=sys.argv[1]
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
p={'enable_thinking':True,'reasoning_parser':'qwen_3_5',
   'turboquant_kv_enabled':True,'turboquant_kv_bits':3.0,'turboquant_skip_last':True,
   'max_tokens':16384,'max_context_window':65536,
   'temperature':0.6,'top_p':0.95,'top_k':20,'repetition_penalty':1.0,
   'specprefill_enabled':False,'mtp_enabled':False}
r=op.open(urllib.request.Request(f'http://127.0.0.1:1235/admin/api/models/{mid}/settings',
    data=json.dumps(p).encode(),headers={'Content-Type':'application/json'},method='PUT'))
s=json.loads(r.read()); s=s.get('settings',s)
print('Bedingung:',json.dumps({k:s.get(k) for k in p},ensure_ascii=False))

# Modell neu laden, damit reasoning_parser greift
try:
    urllib.request.urlopen(urllib.request.Request(
        f'http://127.0.0.1:1235/v1/models/{mid}/unload',data=b'{}',
        headers={'Content-Type':'application/json','Authorization':f'Bearer {key}'},method='POST'),timeout=300)
except Exception: pass

# PRUEFSTEIN: denkt es wirklich? Sonst Abbruch statt stundenlang Falsches messen.
req=urllib.request.Request('http://127.0.0.1:1235/v1/chat/completions',method='POST',
    data=json.dumps({'model':mid,'max_tokens':400,
        'messages':[{'role':'user','content':'Eine Kiste wiegt 3 kg, eine zweite doppelt so viel. Wie viel wiegen beide zusammen?'}]}).encode(),
    headers={'Content-Type':'application/json','Authorization':f'Bearer {key}'})
d=json.loads(urllib.request.urlopen(req,timeout=900).read())
m=d['choices'][0]['message']; rc=m.get('reasoning_content') or ''
print(f'Pruefstein: reasoning_content={len(rc)} Zeichen | content={ (m.get("content") or "")[:60]!r}')
if rc[:200]: print('  Denk-Anfang:', rc[:200].replace(chr(10),' '))
if not rc:
    print('ABBRUCH: kein messbares Thinking — Lauf nicht gestartet', file=sys.stderr); sys.exit(1)
if 'brief' not in rc.lower() and 'low' not in rc.lower():
    print('  HINWEIS: Bremstext nicht im Denkblock sichtbar (Template-Vorspann wird evtl. verworfen)')
PY
[ $? -ne 0 ] && { log "ABBRUCH — Thinking nicht nachweisbar"; exit 1; }

log "Matrix ornith15-6bit-lowthink-tq3-v2"
python3 run_king_matrix.py --model "$MID" --label ornith15-6bit-lowthink-tq3-v2 --timeout 1800 --unload-after
log "LOWTHINK-V2 FERTIG"
