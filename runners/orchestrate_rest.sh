#!/usr/bin/env bash
# Wartet auf das Ende des ThinkingCap-Downloads, fährt dann die offenen Batches:
#   1) Ornith-1.5 nothink — die sieben nach dem 507-Vorfall offenen Fixtures
#   2) ThinkingCap-Qwen3.8-27B — alle zehn Fixtures
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ~/.config/omlx/.env; set +a
MODEL_DIR="$HOME/omlx-test-models/airagrp/ThinkingCap-Qwen3.8-27B-mlx-nvfp4"
API="http://127.0.0.1:1235"

log() { echo "[$(date +%H:%M:%S)] $*"; }

# --- 1. Auf Download-Ende warten: Größe 3x stabil + alle Shards aus dem Index da ---
log "Warte auf Download-Ende: $MODEL_DIR"
stable=0; last=0
while [ $stable -lt 3 ]; do
  cur=$(du -sk "$MODEL_DIR" 2>/dev/null | cut -f1 || echo 0)
  if [ "$cur" = "$last" ] && [ "$cur" -gt 1000000 ]; then stable=$((stable+1)); else stable=0; fi
  last=$cur
  sleep 60
done
log "Größe stabil bei $((last/1048576)) GB"

missing=$(python3 - "$MODEL_DIR" <<'PY'
import json,sys
from pathlib import Path
d=Path(sys.argv[1]); idx=d/"model.safetensors.index.json"
if not idx.exists(): print("INDEX_FEHLT"); raise SystemExit
need={v for v in json.loads(idx.read_text())["weight_map"].values()}
print(",".join(sorted(f for f in need if not (d/f).exists())) or "OK")
PY
)
log "Shard-Vollständigkeit: $missing"
if [ "$missing" != "OK" ]; then
  log "ABBRUCH: Download unvollständig ($missing) — kein Lauf gestartet"
  exit 1
fi

# --- 2. omlx zum Rescan bringen, damit das Modell registriert wird ---
python3 - <<'PY'
import json,os,urllib.request,http.cookiejar
key=os.environ['OMLX_API_KEY']
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
r=op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/models/reload',
    data=b'{}',headers={'Content-Type':'application/json'},method='POST'))
print("reload_models:", r.status, r.read()[:200].decode(errors="replace"))
PY

TC_ID=$(curl -s -H "Authorization: Bearer $OMLX_API_KEY" "$API/v1/models" \
  | python3 -c "import json,sys;print(next((m['id'] for m in json.load(sys.stdin)['data'] if 'ThinkingCap' in m['id'] and '3.8' in m['id']),''))")
log "ThinkingCap-ID in omlx: '${TC_ID:-<nicht registriert>}'"

# --- 3. Ornith nothink: die offenen sieben Fixtures ---
log "Starte Ornith nothink (7 offene Fixtures)"
python3 run_king_matrix.py --model Ornith-1.5-35B-A3B-uncensored-MLX-MXFP4 \
  --label ornith15-mxfp4-nothink \
  --fixtures c1-dependent-pipeline,v6-custom-constraint,v6-ambiguity-probe,v6-produktiv-fqdn-bug,r1-offline-research,v6-architecture-choice,a5-long-edit \
  --unload-after
log "Ornith nothink fertig"

# --- 4. ThinkingCap-Matrix ---
if [ -n "$TC_ID" ]; then
  log "Starte ThinkingCap-Matrix ($TC_ID)"
  python3 run_king_matrix.py --model "$TC_ID" --label thinkingcap-qwen38-27b --unload-after
  log "ThinkingCap fertig"
else
  log "ThinkingCap nicht in omlx registriert — Matrix nicht gestartet (manuell prüfen)"
fi

log "ALLE BATCHES DURCH"
