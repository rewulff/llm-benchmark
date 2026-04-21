#!/bin/bash
# Oracle fuer v6-architecture-choice — STUB.
# Vollstaendige Inhaltspruefung erfordert LLM-as-judge.
# Dieser Stub prueft nur: Datei existiert + Mindestlaenge + alle 5 Constraints erwaehnt.
# Exit 0 = PASS (Stub), Exit 1 = FAIL.
set -u

FILE="work/design.md"

if [ ! -f "$FILE" ]; then
    echo "FAIL: design.md nicht erstellt"
    exit 1
fi

LINES=$(wc -l < "$FILE")
if [ "$LINES" -lt 30 ]; then
    echo "FAIL: design.md zu kurz ($LINES Zeilen, Minimum 30)"
    exit 1
fi

# Prueft ob alle 5 Constraints mindestens erwaehnt werden
# (Stub-Heuristik: Schluesselwoerter, nicht semantische Korrektheit)
MISSING=()

grep -qiE "latenc|region|geographic" "$FILE" || MISSING+=("Constraint-1 (latency/region)")
grep -qiE "order|sequence|fifo" "$FILE" || MISSING+=("Constraint-2 (message order)")
grep -qiE "downtime|durabilit|persist|loss|replac" "$FILE" || MISSING+=("Constraint-3 (downtime/durability)")
grep -qiE '\$[0-9]|budget|cost|cheap|free tier' "$FILE" || MISSING+=("Constraint-4 (budget)")
grep -qiE '10.?000|10k|throughput|messages.*hour|peak' "$FILE" || MISSING+=("Constraint-5 (throughput)")

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "FAIL: Folgende Constraints nicht adressiert:"
    for m in "${MISSING[@]}"; do echo "  - $m"; done
    exit 1
fi

echo "PASS (Stub): design.md existiert mit $LINES Zeilen und adressiert alle 5 Constraints."
echo "  HINWEIS: Inhaltliche Qualitaet (Konsistenz, Tiefe, ASCII-Diagramm) wurde NICHT geprueft."
echo "  Fuer vollstaendige Bewertung: LLM-as-judge implementieren (siehe README.md TODO)."
exit 0
