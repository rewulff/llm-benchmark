#!/usr/bin/env bash
# Draft = Qwen3.5-0.8B MLX 8bit (affine g64): bei 0.8B kostet der hoehere Quant fast
# nichts, aber das Prefill-Scoring entscheidet genauer welche Prompt-Tokens behalten
# werden — verworfene Tokens holt SpecPrefill nicht zurueck.
# A/B-Test SpecPrefill fuer Ornith (MoE): identische Fixtures, identische Sampling-Settings,
# einziger Unterschied ist specprefill_enabled + keep_pct. Wartet auf das Ende der
# laufenden MTP-Matrix, damit sich die Laeufe nicht um den Speicher streiten.
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ~/.config/omlx/.env; set +a
ORNITH='Ornith-1.5-35B-A3B-uncensored-MLX-MXFP4'
DRAFT='/Users/rwu/.cache/huggingface/hub/models--mlx-community--Qwen3.5-0.8B-8bit/snapshots/87e768fbfa03994095f3d14527c80c5ae70c5758'
log() { echo "[$(date +%H:%M:%S)] $*"; }

log "warte auf Ende der ThinkingCap-MTP-Matrix"
while pgrep -f "run_king_matrix.py --model ThinkingCap" >/dev/null; do sleep 30; done
log "Matrix beendet"

python3 - "$ORNITH" "$DRAFT" <<'PY'
import json,os,sys,urllib.request,http.cookiejar
key=os.environ['OMLX_API_KEY']; mid,draft=sys.argv[1],sys.argv[2]
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
payload={'specprefill_enabled':True,'specprefill_draft_model':draft,
         'specprefill_keep_pct':0.3,'specprefill_threshold':4096,
         'enable_thinking':False,'max_tokens':16384,'temperature':0.6,
         'top_p':0.95,'top_k':20,'repetition_penalty':1.0}
r=op.open(urllib.request.Request(f'http://127.0.0.1:1235/admin/api/models/{mid}/settings',
    data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='PUT'))
s=json.loads(r.read()); s=s.get('settings',s)
print('SpecPrefill-Bedingung:',json.dumps({k:s.get(k) for k in payload},ensure_ascii=False))
PY

log "Ornith nothink + SpecPrefill keep=0.3 ueber alle 10 Fixtures"
python3 run_king_matrix.py --model "$ORNITH" --label ornith15-nothink-specprefill03 --timeout 1800 --unload-after
log "FERTIG"
