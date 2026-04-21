#!/bin/bash
# Oracle fuer Fixture a2-bugfix.
# Wird im work/-Verzeichnis des Jobs aufgerufen.
# Exit 0 = PASS, Exit 1 = FAIL.
set -u

FAIL=0

# Check 1: multiply() benutzt * statt +
if ! grep -qE "a \* b|a\*b" work/calculator.py 2>/dev/null; then
    echo "FAIL: multiply() nicht gefixt (erwartet: 'a * b' oder 'a*b')"
    FAIL=1
fi

# Check 2: divide() hat Zero-Division-Check
if ! grep -qE "ZeroDivisionError|ValueError|raise|if b == 0|if b==0" work/calculator.py 2>/dev/null; then
    echo "FAIL: divide() hat keinen Zero-Division-Check"
    FAIL=1
fi

# Check 3: average() hat return-Statement
if ! grep -qE "return sum\b|return sum\(|return total" work/calculator.py 2>/dev/null; then
    echo "FAIL: average() fehlt return-Statement"
    FAIL=1
fi

if [ $FAIL -eq 0 ]; then
    echo "PASS: alle 3 Bugs gefixt"
    exit 0
else
    exit 1
fi
