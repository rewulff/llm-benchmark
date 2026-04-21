#!/bin/bash
# Oracle fuer v6-debug-unmarked.
# Prueft ob der Off-by-one-Bug in get_top_n gefixt wurde.
# Bug: sorted_items[:n-1] liefert nur n-1 Items statt n.
# Fix: sorted_items[:n]
# Exit 0 = PASS, Exit 1 = FAIL.
set -u

FILE="work/server.py"

if [ ! -f "$FILE" ]; then
    echo "FAIL: $FILE nicht erstellt"
    exit 1
fi

# Pruefen: der Bug ([:n-1] oder [: n - 1] etc.) ist noch vorhanden
if grep -qE "sorted_items\s*\[\s*:\s*n\s*-\s*1\s*\]" "$FILE"; then
    echo "FAIL: Bug 'sorted_items[:n-1]' noch vorhanden"
    exit 1
fi

# Pruefen: der Fix ([:n]) ist nun vorhanden
if grep -qE "sorted_items\s*\[\s*:\s*n\s*\]" "$FILE"; then
    echo "PASS: off-by-one in get_top_n gefixt (sorted_items[:n])"
    exit 0
fi

# Alternativer Fix: Funktion vollstaendig umgeschrieben ohne den Slice-Ausdruck
# In diesem Fall pruefen ob get_top_n immer noch existiert und den alten Bug nicht hat
if grep -qE "def\s+get_top_n\s*\(" "$FILE"; then
    echo "PASS (alt): get_top_n neu implementiert ohne [:n-1]-Bug"
    exit 0
fi

echo "FAIL: Fix fuer sorted_items[:n] nicht gefunden"
exit 1
