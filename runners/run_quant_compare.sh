#!/usr/bin/env bash
# Quant-Vergleich Ornith 1.5, offizielle Quelle: MLX-4bit (affine g64) vs MLX-6bit.
# Identische Sampling-Bedingungen wie die MXFP4-nothink-Matrix — nur der Quant variiert.
# (Die junafinity-MXFP4-Fassung ist ein uncensored-Finetune und daher NICHT quant-rein
#  vergleichbar; sauber ist nur 4bit gegen 6bit derselben Quelle.)
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ~/.config/omlx/.env; set +a
log() { echo "[$(date +%H:%M:%S)] $*"; }

log "warte auf Ende laufender Matrizen"
while pgrep -f "run_king_matrix.py" >/dev/null || pgrep -f "run_specprefill_ab.sh" >/dev/null; do sleep 30; done
log "frei"

# 6bit-Download abwarten (byte-genau gegen HF-API)
log "pruefe 6bit-Vollstaendigkeit"
until python3 - <<'PY'
import json,sys,urllib.request
from pathlib import Path
import glob
snaps=glob.glob(str(Path.home()/".cache/huggingface/hub/models--ornith-ai--Ornith-1.5-35B-A3B-MLX-6bit/snapshots/*/"))
if not snaps: sys.exit(1)
d=Path(snaps[0])
u="https://huggingface.co/api/models/ornith-ai/Ornith-1.5-35B-A3B-MLX-6bit/tree/main?recursive=true"
tree=json.loads(urllib.request.urlopen(u,timeout=30).read())
missing=[f["path"] for f in tree if f["type"]=="file"
         and (f.get("size") or (f.get("lfs") or {}).get("size") or 0)
             != ((d/f["path"]).stat().st_size if (d/f["path"]).exists() else -1)]
print("offen:",len(missing))
sys.exit(0 if not missing else 1)
PY
do sleep 60; done
log "6bit vollstaendig"

# omlx rescannen, damit beide Fassungen registriert sind
python3 - <<'PY'
import json,os,urllib.request,http.cookiejar
key=os.environ['OMLX_API_KEY']
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
print("reload:",op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/reload',
    data=b'{}',headers={'Content-Type':'application/json'},method='POST')).status)
PY

for MID in ornith-ai--Ornith-1.5-35B-A3B-MLX-4bit ornith-ai--Ornith-1.5-35B-A3B-MLX-6bit; do
  LABEL="ornith15-official-${MID##*-}-nothink"
  log "Bedingung setzen fuer $MID"
  python3 - "$MID" <<'PY'
import json,os,sys,urllib.request,http.cookiejar
key=os.environ['OMLX_API_KEY']; mid=sys.argv[1]
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
# identisch zur MXFP4-nothink-Matrix; SpecPrefill/MTP bewusst AUS (nur Quant soll variieren)
p={'enable_thinking':False,'max_tokens':16384,'max_context_window':65536,
   'temperature':0.6,'top_p':0.95,'top_k':20,'repetition_penalty':1.0,
   'specprefill_enabled':False,'mtp_enabled':False}
r=op.open(urllib.request.Request(f'http://127.0.0.1:1235/admin/api/models/{mid}/settings',
    data=json.dumps(p).encode(),headers={'Content-Type':'application/json'},method='PUT'))
s=json.loads(r.read()); s=s.get('settings',s)
print('  ->',json.dumps({k:s.get(k) for k in p},ensure_ascii=False))
PY
  log "Matrix $LABEL"
  python3 run_king_matrix.py --model "$MID" --label "$LABEL" --timeout 1800 --unload-after
done
log "QUANT-VERGLEICH FERTIG"
