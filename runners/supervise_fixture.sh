#!/usr/bin/env bash
# Sichtbarer Supervisor-Lauf einer Fixture in einer opencode-TUI (Orca-Worktree), statt headless
# ueber run_opencode_test.py. rwu 02.10.2026: "sollte ich s1 nicht wieder in einer opencode
# session sehen?" — ja: hier laeuft der Agent in Orca, der Supervisor (Claude) wartet auf DONE,
# fuehrt dann das Fixture-Oracle gegen den Worktree aus und raeumt erst nach rwus Blick auf.
#
# Aufruf: supervise_fixture.sh <fixture> <provider/model> <worktree-name> [repoId]
#   Beispiel: supervise_fixture.sh s1-report-runs omlx/scottlowry--Ornith-1.5-35B-A3B-oQ4e-mtp s1-ornith-nothink
# Nebenwirkungen: legt einen Orca-Worktree (Branch gleichen Namens, Basis feat/omlx-070-oq4e) und ein
# Terminal an, kopiert die Fixture-Eingaben hinein (input/ Referenz, work/ Arbeitskopie), startet
# opencode mit dem Modell und sendet prompt.md. Entfernt NICHTS; Oracle und Aufraeumen sind getrennte
# Schritte (unten ausgegeben). Nie zwei opencode-Instanzen parallel starten.
set -euo pipefail
FX=${1:?fixture}; MODEL=${2:?provider/model}; NAME=${3:?worktree-name}; REPO=${4:-905df726-d675-4f1b-bcb1-dd4e6fab797a}
FXD=/Users/rwu/Arbeitsverzeichnis/lib/local-llm/benchmark/opencode/fixtures/$FX
[ -f "$FXD/prompt.md" ] || { echo "Fixture $FX ohne prompt.md"; exit 1; }
W=/Users/rwu/orca/workspaces/llm-benchmark/$NAME
if [ ! -d "$W" ]; then
  orca worktree create --repo "id:$REPO" --name "$NAME" --base-branch feat/omlx-070-oq4e --json >/dev/null
fi
mkdir -p "$W/input" "$W/work"
[ -d "$FXD/input" ] && cp -R "$FXD/input/." "$W/input/" && cp -R "$FXD/input/." "$W/work/"
# Terminal haengt am Worktree-ROOT (Orca-Selektor), opencode startet in work/ (dort liegen results/ und entsteht runners/)
H=$(orca terminal create --worktree "path:$W" --command "cd work && OPENCODE_DISABLE_AUTOUPDATE=1 opencode --model $MODEL" --json | python3 -c "import json,sys; d=json.load(sys.stdin); r=d.get('result',d); print(r.get('handle') or (r.get('terminal') or {}).get('handle') or '')")
[ -n "$H" ] && [ "$H" != "None" ] || { echo "Terminal konnte nicht angelegt werden"; exit 3; }
SAT=$(orca terminal wait --terminal "$H" --for tui-idle --timeout-ms 90000 --json | python3 -c "import json,sys; d=json.load(sys.stdin); w=d.get('result',d).get('wait',d.get('result',d)); print(w.get('satisfied'))")
[ "$SAT" = "True" ] || { echo "TUI nicht bereit (satisfied=$SAT) — Prompt NICHT gesendet; Terminal $H"; exit 2; }
orca terminal send --terminal "$H" --text "$(cat "$FXD/prompt.md")" --enter --wait-submit 10 --json >/dev/null
echo "gestartet $(date +%H:%M:%S) | worktree=$W | terminal=$H | model=$MODEL"
echo "Oracle nach DONE:  JOB_DIR=$W bash $FXD/oracle.sh"
echo "Aufraeumen danach: orca terminal close --terminal $H --json; orca worktree rm --worktree path:$W --force --json"
