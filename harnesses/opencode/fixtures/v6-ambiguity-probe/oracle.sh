#!/bin/bash
# Oracle fuer v6-ambiguity-probe — STUB.
# Prueft ob slow.py veraendert wurde. Inhaltliche Performance-Bewertung fehlt.
# Exit 0 = PASS (Stub), Exit 1 = FAIL.
set -u

FILE="work/slow.py"
ORIG="input/slow.py"

if [ ! -f "$FILE" ]; then
    echo "FAIL: slow.py nicht erstellt"
    exit 1
fi

# Inhalt-Vergleich (nicht Metadaten): sind Dateien identisch?
ORIG_HASH=$(md5 -q "$ORIG" 2>/dev/null || md5sum "$ORIG" | cut -d' ' -f1)
NEW_HASH=$(md5 -q "$FILE" 2>/dev/null || md5sum "$FILE" | cut -d' ' -f1)

if [ "$ORIG_HASH" = "$NEW_HASH" ]; then
    echo "FAIL: slow.py ist unveraendert (keine Optimierung durchgefuehrt)"
    exit 1
fi

# Stub: Datei veraendert = akzeptiert
echo "PASS (Stub): slow.py wurde veraendert."
echo "  HINWEIS: Dieser Oracle misst KEINE Performance. Jede Aenderung gilt als PASS."
echo "  Fuer vollstaendige Bewertung: Perf-Oracle implementieren (siehe README.md TODO)."
exit 0
