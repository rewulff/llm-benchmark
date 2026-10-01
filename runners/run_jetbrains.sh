#!/usr/bin/env bash
# JetBrains Qwen3.8-3.6-27B-blend (Junie-Local-Modell) mit offiziellem externem MTP-Drafter.
# Kein Frankenstein noetig: JetBrains liefert Hauptmodell + passenden Drafter als Paar
# ("native MTP drafter extracted from the original BF16 checkpoint").
# omlx-Weg dafuer ist vlm_mtp_enabled + vlm_mtp_draft_model (externer Drafter),
# NICHT mtp_enabled (das verlangt mtp.*-Gewichte IM Checkpoint).
# Sampling bewusst wie bei den anderen Kandidaten (temp 0.6) statt der Kartenempfehlung
# temp 1.0 — Vergleichbarkeit innerhalb der Matrix; Herstellerwert im Report ausgewiesen.
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ~/.config/omlx/.env; set +a
MID='JetBrains--Qwen3.8-3.6-27B-blend-MLX-4bit'
DRAFT='/Users/rwu/.cache/huggingface/hub/models--JetBrains--Qwen3.8-3.6-27B-blend-MTP-MLX-4bit/snapshots/dd5868aceb4fa5fbdee36d517cfaa03c21fa4689'
log() { echo "[$(date +%H:%M:%S)] $*"; }

log "warte auf freie Maschine"
while pgrep -f "run_king_matrix.py" >/dev/null || pgrep -f "run_quant_compare.sh" >/dev/null    || pgrep -f "run_effort_compare.sh" >/dev/null; do sleep 30; done
log "frei"

python3 - "$MID" "$DRAFT" <<'PY'
import json,os,sys,urllib.request,http.cookiejar
key=os.environ['OMLX_API_KEY']; mid,draft=sys.argv[1],sys.argv[2]
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
p={'vlm_mtp_enabled':True,'vlm_mtp_draft_model':draft,
   'enable_thinking':True,'max_tokens':16384,'max_context_window':65536,
   'temperature':0.6,'top_p':0.95,'top_k':20,
   'repetition_penalty':1.0,   # !=1.0 wuerde den MTP-Pfad still abschalten
   'specprefill_enabled':False,'mtp_enabled':False}
r=op.open(urllib.request.Request(f'http://127.0.0.1:1235/admin/api/models/{mid}/settings',
    data=json.dumps(p).encode(),headers={'Content-Type':'application/json'},method='PUT'))
s=json.loads(r.read()); s=s.get('settings',s)
print('Bedingung:',json.dumps({k:s.get(k) for k in p},ensure_ascii=False))
PY

log "Matrix JetBrains-Blend + externer MTP-Drafter"
python3 run_king_matrix.py --model "$MID" --label jetbrains-blend-27b-vlmmtp --timeout 2400 --unload-after

log "Gegenprobe ohne Drafter (misst, was der Drafter wirklich bringt)"
python3 - "$MID" <<'PY'
import json,os,sys,urllib.request,http.cookiejar
key=os.environ['OMLX_API_KEY']; mid=sys.argv[1]
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
op.open(urllib.request.Request(f'http://127.0.0.1:1235/admin/api/models/{mid}/settings',
    data=json.dumps({'vlm_mtp_enabled':False}).encode(),
    headers={'Content-Type':'application/json'},method='PUT'))
print('vlm_mtp aus')
PY
python3 run_king_matrix.py --model "$MID" --label jetbrains-blend-27b-plain --timeout 2400 --unload-after
log "JETBRAINS FERTIG"
