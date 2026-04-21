#!/bin/bash
# Oracle fuer v6-custom-constraint.
# Prueft ob find_sequences(4, 30, 5) den korrekten Wert zurueckgibt.
# Erwarteter Wert: 32 (berechnet via Referenz-Implementation).
# Exit 0 = PASS, Exit 1 = FAIL.
set -u

FILE="work/solve.py"

if [ ! -f "$FILE" ]; then
    echo "FAIL: $FILE nicht erstellt"
    exit 1
fi

grep -qE "def\s+find_sequences\s*\(" "$FILE" || { echo "FAIL: find_sequences nicht definiert"; exit 1; }
grep -qE '__name__\s*==\s*["'"'"']__main__["'"'"']' "$FILE" || { echo "FAIL: __main__-Block fehlt"; exit 1; }

# Ausfuehren und Output pruefen (portable timeout via perl alarm, 15s)
OUT=$(cd work && perl -e 'alarm shift @ARGV; exec @ARGV' 15 python3 solve.py 2>&1)
RC=$?
if [ $RC -ne 0 ]; then
    echo "FAIL: solve.py Exit=$RC"
    echo "  Output: $OUT" | head -5
    exit 1
fi

LAST=$(echo "$OUT" | tail -1 | tr -d ' \t\r\n')
EXPECTED="32"

if [ "$LAST" = "$EXPECTED" ]; then
    echo "PASS: find_sequences(4, 30, 5) count == $EXPECTED"
    exit 0
fi

echo "FAIL: erwartet '$EXPECTED', erhalten '$LAST'"
echo "  Full Output: $OUT" | head -5
exit 1
