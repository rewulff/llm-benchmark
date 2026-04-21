#!/bin/bash
# Oracle fuer Fixture a5-long-edit.
# Wird im job_dir aufgerufen (Datei liegt unter work/large_module.py).
# Exit 0 = PASS (alle 8 Bugs gefixt), Exit 1 = FAIL.
set -u

PASS1=0
PASS2=0
PASS3=0
PASS4=0
PASS5=0
PASS6=0
PASS7=0
PASS8=0

# Bug 1: calculate_discount — Rabatt abziehen statt addieren
# Erwartet: price * (1 - percentage / 100) o.ae.
if grep -qE "price\s*\*\s*\(1\s*-\s*percentage|price\s*-\s*price\s*\*\s*percentage|price\s*\*\s*\(100\s*-\s*percentage" work/large_module.py 2>/dev/null; then
    PASS1=1
fi

# Bug 2: is_palindrome — s == s[::-1] statt s == s
if grep -qE "s\s*==\s*s\s*\[\s*::\s*-\s*1\s*\]" work/large_module.py 2>/dev/null; then
    PASS2=1
fi

# Bug 3: flatten_list — rekursiver Aufruf von flatten_list muss vorkommen
# Zaehlstrategie: mindestens 2 Vorkommen des Namens (Definition + rekursiver Call)
COUNT3=$(grep -c 'flatten_list' work/large_module.py 2>/dev/null || true)
if [ "${COUNT3:-0}" -ge 2 ] 2>/dev/null; then
    # Zusaetzlich pruefen dass kein "return nested" mehr ungeaendert vorhanden
    if ! grep -qE "^\s*return nested\s*$" work/large_module.py 2>/dev/null; then
        PASS3=1
    fi
fi

# Bug 4: safe_divide — try/except oder if-check fuer b==0
# Prueft ob im safe_divide-Kontext ein Schutz gegen b=0 existiert.
# Strategie: if b == 0 / if not b / ZeroDivisionError muss in der Datei stehen
if grep -qE "if\s+b\s*==\s*0|if\s+not\s+b\b|ZeroDivisionError" work/large_module.py 2>/dev/null; then
    PASS4=1
fi

# Bug 5: word_count — len(text.split(...)) statt len(text)
if grep -qE "len\s*\(\s*text\.split\s*\(" work/large_module.py 2>/dev/null; then
    PASS5=1
fi

# Bug 6: merge_dicts — b muss eingebunden werden (akzeptiert Immutable-Merge via Copy+Update)
if grep -qE "\{\s*\*\*\s*\w+\s*,\s*\*\*\s*\w+\s*\}|\.update\s*\(\s*b\s*\)|a\s*\|\s*b|dict\(\s*a\s*,\s*\*\*\s*b\s*\)" work/large_module.py 2>/dev/null; then
    PASS6=1
fi

# Bug 7: reverse_words — Woerter umkehren (split + Umkehrung + join)
if grep -qE "sentence\.split\s*\(|words\s*\[\s*::\s*-\s*1\s*\]|reversed\s*\(" work/large_module.py 2>/dev/null; then
    # sentence[::-1] muss weg sein (Zeichenketten-Umkehr)
    if ! grep -qE "sentence\s*\[\s*::\s*-\s*1\s*\]" work/large_module.py 2>/dev/null; then
        PASS7=1
    fi
fi

# Bug 8: fibonacci — Rekursion oder Iteration, nicht n*n
if grep -qE "fibonacci\s*\(\s*n\s*-\s*1\s*\)|fib\s*\(\s*n\s*-\s*1\s*\)" work/large_module.py 2>/dev/null; then
    PASS8=1
else
    # Iterativer Ansatz: Schleife die a, b akkumuliert
    if grep -qE "a\s*,\s*b\s*=\s*b\s*,\s*a\s*\+\s*b" work/large_module.py 2>/dev/null; then
        PASS8=1
    fi
fi

TOTAL=$((PASS1 + PASS2 + PASS3 + PASS4 + PASS5 + PASS6 + PASS7 + PASS8))
echo "A5 Oracle: $TOTAL / 8 bugs fixed"

if [ $TOTAL -eq 8 ]; then
    echo "PASS: alle 8 Bugs gefixt"
    exit 0
else
    echo "FAIL: nur $TOTAL von 8 gefixt"
    [ $PASS1 -eq 0 ] && echo "  FAIL: Bug 1 — calculate_discount (Rabatt addiert statt abgezogen)"
    [ $PASS2 -eq 0 ] && echo "  FAIL: Bug 2 — is_palindrome (vergleicht s mit s statt s[::-1])"
    [ $PASS3 -eq 0 ] && echo "  FAIL: Bug 3 — flatten_list (keine Rekursion / return nested unveraendert)"
    [ $PASS4 -eq 0 ] && echo "  FAIL: Bug 4 — safe_divide (kein Schutz vor b=0)"
    [ $PASS5 -eq 0 ] && echo "  FAIL: Bug 5 — word_count (zaehlt Zeichen statt Woerter)"
    [ $PASS6 -eq 0 ] && echo "  FAIL: Bug 6 — merge_dicts (b wird ignoriert)"
    [ $PASS7 -eq 0 ] && echo "  FAIL: Bug 7 — reverse_words (Zeichenkette statt Woerter umgekehrt)"
    [ $PASS8 -eq 0 ] && echo "  FAIL: Bug 8 — fibonacci (gibt n*n statt Fibonacci-Zahl)"
    exit 1
fi
