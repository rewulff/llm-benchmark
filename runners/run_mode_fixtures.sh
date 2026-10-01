#!/usr/bin/env bash
# Fixture-Vergleich "jedes Modell in SEINEM vorgesehenen Modus" (rwu, 01.10.2026: "du
# versuchst das Verhalten des Basismodells zu erzwingen, statt es so zu nutzen, wie es
# vorgesehen ist"). Bisher liefen ALLE Fixtures nothink — auch ThinkingCap, dessen Template
# Thinking + reasoning_effort 'xhigh' vorsieht. Dieser Lauf korrigiert das fuer beide:
#
#   Solstice   Thinking AN, MTP d3 (nativer Head, 29 mtp.*-Tensoren), TQ-KV AUS (kostet 8 %,
#              in der Karte nur fuer 16/24-GB-Geraete gedacht), aufgabengerechte Profile per
#              In-Chat-Tag (Profiltexte des Templates geben die Zuordnung vor):
#                a2-bugfix            {REASON:artemis}  "Edge-Case Scan, Vulnerability Audit"
#                v6-custom-constraint {REASON:apollo}   "Constraint Mapping, lineare Deduktion"
#                a5-long-edit         {REASON:artemis}
#   ThinkingCap Thinking AN, Default-Effort xhigh (einziger Weg ueber opencode: keine Tags),
#              MTP d3 (sein Beschleuniger, Teil des Checkpoints)
#
# Messwerte je Fixture: PASS/FAIL (Oracle), duration_s (Ende-zu-Ende). reasoning_tokens ist
# ueber opencode IMMER 0 (kennt omlx' reasoning_content-Delta nicht) — Thinking-Beleg nur im
# omlx-Log. Settings-Drift (WebUI) wird nach jeder Fixture per --expect-settings geprueft.
# Thinking-Budget AUS (sonst nicht "deren Modus"); Timeout 1800 s wie ueberall.
set -euo pipefail
cd "$(dirname "$0")"
set -a; . ~/.config/omlx/.env; set +a
log() { echo "[$(date +%H:%M:%S)] $*"; }
SOL="Solstice-AI--Qwen3.8-27B-TURBO-Fable-Cold-Fusion-735-882-Heretic-Uncensored-NM-DAU-mlx-oQ4e-1M"
TC="chriswessels--ThinkingCap-Qwen3.8-27B-oQ4e-mtp"
FIX="a2-bugfix,v6-custom-constraint,a5-long-edit"

lsof -nP -iTCP:1236 -sTCP:LISTEN >/dev/null 2>&1 && { log "ABBRUCH: llama-server lauscht auf :1236"; exit 1; }
if ps -eo comm=,args= | grep -E "run_king_matrix|run_070_throughput|opencode run" | grep -vqE "^claude|grep"; then
  log "ABBRUCH: anderer Benchmark-/opencode-Prozess aktiv"; exit 1
fi

# Settings setzen + Pool pruefen + Pruefstein (zurueckgelesen muss stehen, was gefordert war)
set_mode() {  # $1 model-id  $2 tq on|off  $3 mtp depth|0
python3 - "$1" "$2" "$3" <<'PY'
import json,os,sys,urllib.request,http.cookiejar
mid,tq,mtp=sys.argv[1],sys.argv[2]=="on",int(sys.argv[3]); key=os.environ['OMLX_API_KEY']
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request('http://127.0.0.1:1235/admin/api/login',
    data=json.dumps({'api_key':key}).encode(),headers={'Content-Type':'application/json'},method='POST'))
ms=json.loads(op.open('http://127.0.0.1:1235/admin/api/models',timeout=30).read()); ms=ms.get('models',ms)
loaded=[m['id'] for m in ms if isinstance(m,dict) and m.get('loaded') and 'TTS' not in m['id'] and m['id']!=mid]
if loaded: sys.exit(f"ABBRUCH: fremde Modelle geladen: {loaded}")
h=json.loads(urllib.request.urlopen('http://127.0.0.1:1235/health',timeout=10).read()); ceil=h['engine_pool']['final_ceiling']/2**30
if ceil<25: sys.exit(f"ABBRUCH: Ceiling {ceil:.1f} GiB — Buffer-Reste, omlx neu starten")
p={'enable_thinking':True,'thinking_budget_enabled':False,
   'max_tokens':16384,'max_context_window':65536,
   'temperature':0.6,'top_p':0.95,'top_k':20,'repetition_penalty':1.0,
   'specprefill_enabled':False,'mtp_enabled':mtp>0,
   'turboquant_kv_enabled':tq,'turboquant_kv_bits':4,'turboquant_skip_last':True}
if mtp: p['mtp_fixed_depth']=mtp
r=op.open(urllib.request.Request(f'http://127.0.0.1:1235/admin/api/models/{mid}/settings',
    data=json.dumps(p).encode(),headers={'Content-Type':'application/json'},method='PUT'))
s=json.loads(r.read()); s=s.get('settings',s)
got={k:s.get(k) for k in ('enable_thinking','thinking_budget_enabled','mtp_enabled','turboquant_kv_enabled','temperature')}
print('  Settings:',json.dumps(got),f'| Ceiling {ceil:.1f} GiB')
bad=[k for k in ('enable_thinking','mtp_enabled','turboquant_kv_enabled','temperature') if got.get(k)!=p[k]]
if bad: sys.exit(f'  ABBRUCH: Settings nicht uebernommen: {bad}')
PY
}

log "=== 1/2 Solstice — Thinking AN, MTP d3, TQ aus, Profile artemis/apollo/artemis ==="
set_mode "$SOL" off 3   # MTP d3: nativer Head (29 mtp.*-Tensoren); TQ aus (kostet 8 %)
python3 run_king_matrix.py --model "$SOL" --label solstice-think-profiles-mtp-min --fixtures "$FIX" \
  --prompt-prefix-map "a2-bugfix={REASON:artemis},v6-custom-constraint={REASON:apollo},a5-long-edit={REASON:artemis}" \
  --expect-settings '{"enable_thinking":true,"mtp_enabled":true,"mtp_fixed_depth":3,"turboquant_kv_enabled":false,"thinking_budget_enabled":false}' \
  --timeout 1800 --unload-after
log "Solstice fertig — 30 s Puffer"; sleep 30
[ "${SOLSTICE_ONLY:-}" = 1 ] && { log "SOLSTICE_ONLY gesetzt — ThinkingCap-Teil uebersprungen"; exit 0; }

log "=== 2/2 ThinkingCap — Thinking AN, Default xhigh, MTP d3 ==="
set_mode "$TC" off 3
python3 run_king_matrix.py --model "$TC" --label thinkingcap-think-xhigh-mtp-min --fixtures "$FIX" \
  --expect-settings '{"enable_thinking":true,"mtp_enabled":true,"mtp_fixed_depth":3,"turboquant_kv_enabled":false,"thinking_budget_enabled":false}' \
  --timeout 1800 --unload-after
log "MODE-FIXTURES FERTIG"
