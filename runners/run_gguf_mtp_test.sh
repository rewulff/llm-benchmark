#!/usr/bin/env bash
# Ornith-1.5 als GGUF mit nativem MTP-Head (blk.40) gegen unsere MLX-Referenz.
# Hintergrund: MaxToken misst fuer Ornith mit nativem MTP 109-111 tok/s auf M1 Max,
# wir messen in MLX (ohne MTP, da alle MLX-Konvertierungen den Head verwerfen) 46,9 tok/s.
# llama.cpp kann den Head: --spec-type draft-mtp.
# Fair: Balanced-Quant (26,17 GB) ~ MLX-6bit (26,3 GiB), greedy, gleicher Prompt.
set -uo pipefail
PORT=1236
GGUF=$(ls ~/.cache/huggingface/hub/models--mudler--Ornith-1.5-35B-A3B-APEX-MTP-GGUF/snapshots/*/Ornith-1.5-35B-A3B-APEX-MTP-Balanced.gguf 2>/dev/null | head -1)
log(){ echo "[$(date +%H:%M:%S)] $*"; }

log "warte auf vollstaendigen Download"
until [ -n "$GGUF" ] && [ -f "$GGUF" ]; do
  sleep 60
  GGUF=$(ls ~/.cache/huggingface/hub/models--mudler--Ornith-1.5-35B-A3B-APEX-MTP-GGUF/snapshots/*/Ornith-1.5-35B-A3B-APEX-MTP-Balanced.gguf 2>/dev/null | head -1)
done
log "Datei da: $(du -h "$GGUF" | cut -f1)"

bench() {  # $1=label  $2...=extra flags
  local label="$1"; shift
  pkill -f "llama-server.*--port $PORT" 2>/dev/null; sleep 2
  log "starte llama-server: $label"
  llama-server -m "$GGUF" --port $PORT --host 127.0.0.1 -ngl 99 -c 16384 --jinja "$@" \
    > /tmp/llama-gguf-$label.log 2>&1 &
  for i in $(seq 1 180); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:$PORT/health 2>/dev/null)" = "200" ] && break
    sleep 2
  done
  if [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:$PORT/health 2>/dev/null)" != "200" ]; then
    log "  FEHLER: Server nicht bereit — siehe /tmp/llama-gguf-$label.log"; tail -5 /tmp/llama-gguf-$label.log; return 1
  fi
  python3 - "$label" "$PORT" <<'PY'
import json,sys,time,urllib.request
label,port=sys.argv[1],sys.argv[2]
P=f"[{time.time()}] Write a Python function that merges two sorted lists. Code only."
t=time.time()
req=urllib.request.Request(f'http://127.0.0.1:{port}/v1/chat/completions',method='POST',
    data=json.dumps({'messages':[{'role':'user','content':P}],'max_tokens':200,'temperature':0.0}).encode(),
    headers={'Content-Type':'application/json'})
d=json.loads(urllib.request.urlopen(req,timeout=900).read())
u=d.get('usage',{}); dur=time.time()-t; ct=u.get('completion_tokens') or 0
print(f"  {label:26s}: {ct/dur:6.1f} tok/s  ({ct} tok in {dur:.1f}s)")
PY
  grep -aiE "accept|draft|spec" /tmp/llama-gguf-$label.log | tail -3 | sed 's/^/     /'
}

echo "Ornith-1.5-35B-A3B GGUF (Balanced 26,17 GB) — MLX-Referenz: 46,9 tok/s"
bench "ohne-MTP" --spec-type none
bench "mit-MTP"  --spec-type draft-mtp
pkill -f "llama-server.*--port $PORT" 2>/dev/null
log "GGUF-MTP-TEST FERTIG"
