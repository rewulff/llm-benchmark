#!/usr/bin/env bash
# Fixture-Matrix auf dem omlx-eigenen Quantformat oQ4e — Qualitaetspruefung zu den
# Durchsatzgewinnen vom 01.10. (results/omlx-070-throughput/REPORT.md).
#
# Gefahren wird je Kandidat nur die SCHNELLSTE Konfiguration:
#   Ornith oQ4e-mtp      MTP AUS  (78,9 tok/s; MTP kostet dort 35 %)
#   ThinkingCap oQ4e-mtp MTP d3   (22,6 tok/s; MTP bringt dort +55 %)
#
# Jeder Kandidat laeuft gegen SEINE Referenz vom 30.09., mit deren Sampling:
#   Ornith      -> temp 0, Referenz ornith15-6bit-temp0-run1 (10/10) + run2 (9/10)
#   ThinkingCap -> temp 0.6, Referenz thinkingcap-qwen38-mtp-d3 (9/10)
# Unterschiedliche Temperaturen zwischen den beiden sind Absicht: ein A/B gegen die
# eigene Referenz ist aussagekraeftiger als Gleichmacherei zwischen zwei Modellen,
# die ohnehin nicht gegeneinander antreten.
#
# Vorbedingung: kein llama-server aktiv — er haelt sein Modell in Metal-Buffern
# (nicht im RSS sichtbar) und laesst omlx am Memory Guard scheitern.
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ~/.config/omlx/.env; set +a
log() { echo "[$(date +%H:%M:%S)] $*"; }

if pgrep -f "llama-server" >/dev/null; then
  log "ABBRUCH: llama-server laeuft und blockiert den Speicher — erst stoppen"
  exit 1
fi

run_one() {
  local MID="$1" LABEL="$2" TEMP="$3" MTP="$4" DEPTH="${5:-3}"
  log "=== $LABEL (temp=$TEMP, MTP=$MTP) ==="
  python3 - "$MID" "$TEMP" "$MTP" "$DEPTH" <<'PY'
import json,os,sys,urllib.request,http.cookiejar
mid,temp,mtp,depth=sys.argv[1],float(sys.argv[2]),sys.argv[3]=="an",int(sys.argv[4])
key=os.environ['OMLX_API_KEY']
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
p={'enable_thinking':False,'max_tokens':16384,'max_context_window':65536,
   'temperature':temp,'top_p':0.95,'top_k':20,
   'repetition_penalty':1.0,              # != 1.0 schaltet MTP still ab
   'specprefill_enabled':False,'mtp_enabled':mtp}
if mtp: p['mtp_fixed_depth']=depth
r=op.open(urllib.request.Request(f'http://127.0.0.1:1235/admin/api/models/{mid}/settings',
    data=json.dumps(p).encode(),headers={'Content-Type':'application/json'},method='PUT'))
s=json.loads(r.read()); s=s.get('settings',s)
got={k:s.get(k) for k in ('temperature','mtp_enabled','mtp_fixed_depth','enable_thinking','repetition_penalty')}
print('  Settings:',json.dumps(got,ensure_ascii=False))
# Pruefstein: wurde wirklich gesetzt, was gefordert war?
bad=[k for k,v in (('temperature',temp),('mtp_enabled',mtp)) if got.get(k)!=v]
if bad: sys.exit(f"  ABBRUCH: Settings nicht uebernommen: {bad}")
PY
  [ $? -ne 0 ] && { log "Settings fehlgeschlagen — $LABEL uebersprungen"; return 1; }
  python3 run_king_matrix.py --model "$MID" --label "$LABEL" --timeout 1800 --unload-after
  log "fertig: $LABEL"
  sleep 30   # Entladen laeuft asynchron weiter -> sonst HTTP 409 beim naechsten Setzen
}

# Ornith zuerst: schnell (Referenz 7,9 min), liefert frueh ein Ergebnis
run_one scottlowry--Ornith-1.5-35B-A3B-oQ4e-mtp ornith15-oq4e-nomtp-temp0 0 aus
run_one chriswessels--ThinkingCap-Qwen3.8-27B-oQ4e-mtp thinkingcap-oq4e-mtp-d3 0.6 an 3

log "OQ4E-FIXTURES FERTIG"
