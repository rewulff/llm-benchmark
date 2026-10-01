#!/usr/bin/env bash
# Denkaufwand-Vergleich ThinkingCap-Qwen3.8 — Ziel: Knecht-Tauglichkeit.
# Basis ist der Lauf thinkingcap-qwen38-mtp-d3 (reasoning_effort=medium, ohne Budget).
# Variiert wird NUR der Denkaufwand; MTP d3, TurboQuant, Sampling bleiben identisch.
#   A) reasoning_effort = low
#   B) reasoning_effort = medium + hartes Thinking-Budget 2048 Token
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ~/.config/omlx/.env; set +a
MID='ThinkingCap-Qwen3.8-27B-mlx-nvfp4'
log() { echo "[$(date +%H:%M:%S)] $*"; }

log "warte auf freie Maschine (laufende Matrizen/Queues)"
while pgrep -f "run_king_matrix.py" >/dev/null \
   || pgrep -f "run_specprefill_ab.sh" >/dev/null \
   || pgrep -f "run_quant_compare.sh" >/dev/null; do sleep 30; done
log "frei"

setup() {  # $1=json-payload  $2=beschreibung
  python3 - "$MID" "$1" "$2" <<'PY'
import json,os,sys,urllib.request,http.cookiejar
key=os.environ['OMLX_API_KEY']; mid,payload,desc=sys.argv[1],json.loads(sys.argv[2]),sys.argv[3]
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
r=op.open(urllib.request.Request(f'http://127.0.0.1:1235/admin/api/models/{mid}/settings',
    data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='PUT'))
s=json.loads(r.read()); s=s.get('settings',s)
print(f'  {desc}:',json.dumps({k:s.get(k) for k in payload},ensure_ascii=False))
PY
}

BASE='"mtp_enabled":true,"mtp_fixed_depth":3,"enable_thinking":true,"max_tokens":16384,
"max_context_window":65536,"temperature":0.6,"top_p":0.95,"top_k":20,"repetition_penalty":1.0,
"turboquant_kv_enabled":true,"turboquant_kv_bits":3.0'

log "A) reasoning_effort=low"
setup "{$BASE,\"chat_template_kwargs\":{\"reasoning_effort\":\"low\"},\"forced_ct_kwargs\":[\"reasoning_effort\"],\"thinking_budget_enabled\":false}" "effort-low"
python3 run_king_matrix.py --model "$MID" --label thinkingcap-mtp-effort-low --timeout 2400 --unload-after

log "B) reasoning_effort=medium + thinking_budget 2048"
setup "{$BASE,\"chat_template_kwargs\":{\"reasoning_effort\":\"medium\"},\"forced_ct_kwargs\":[\"reasoning_effort\"],\"thinking_budget_enabled\":true,\"thinking_budget_tokens\":2048}" "budget-2048"
python3 run_king_matrix.py --model "$MID" --label thinkingcap-mtp-budget2048 --timeout 2400 --unload-after

log "zuruecksetzen auf die Referenzbedingung (medium, kein Budget)"
setup "{$BASE,\"chat_template_kwargs\":{\"reasoning_effort\":\"medium\"},\"forced_ct_kwargs\":[\"reasoning_effort\"],\"thinking_budget_enabled\":false}" "referenz"
log "DENKAUFWAND-VERGLEICH FERTIG"
