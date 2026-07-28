#!/bin/bash
# Oracle fuer Fixture m1-multiturn-brief.
# Wird im job_dir aufgerufen (nicht in work/) — adressiert work/ als Subpfad.
# Prueft den ENDZUSTAND nach dem dritten Turn. Die Dialog-Metriken
# (asked_clarifying, Turns, Steps, Diff-Groesse) liefert run_multiturn_test.py,
# nicht dieses Script.
# Exit 0 = PASS, Exit 1 = FAIL.
set -u

FIXTURE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="work"
FAIL=0

# md5 der unveraenderten Contract-Dateien (input/-Stand, LF-Zeilenenden):
#   md5 -q input/test_logfilter.py input/sample.log
MD5_TEST="223b554aa40085a8af72b9c1502a00ca"
MD5_LOG="2c9aa78c8f9defdf470e8e5b7fa8ed3f"

md5_of() {
    if command -v md5sum >/dev/null 2>&1; then
        md5sum "$1" | awk '{print $1}'
    else
        md5 -q "$1"
    fi
}

TIMEOUT_PREFIX=""
if command -v timeout >/dev/null 2>&1; then
    TIMEOUT_PREFIX="timeout 90"
elif command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT_PREFIX="gtimeout 90"
fi

# Verifikations-Script wieder entfernen, egal wie das Oracle endet.
cleanup() { rm -f "$WORK/oracle_check.py"; }
trap cleanup EXIT

# --- Check 1: Dateien vorhanden ----------------------------------------------
MISSING=""
for f in logfilter.py test_logfilter.py sample.log; do
    [ -f "$WORK/$f" ] || MISSING="$MISSING $f"
done
if [ -n "$MISSING" ]; then
    echo "FAIL [1/4] Dateien fehlen in $WORK/:$MISSING"
    echo "ERGEBNIS: FAIL"
    exit 1
fi
if ! (cd "$WORK" && python3 -m py_compile logfilter.py) 2>/dev/null; then
    echo "FAIL [1/4] logfilter.py kompiliert nicht"
    echo "ERGEBNIS: FAIL"
    exit 1
fi
echo "PASS [1/4] logfilter.py, test_logfilter.py, sample.log vorhanden und kompilierbar"

# --- Check 2: Contract-Dateien unveraendert ----------------------------------
GOT_TEST=$(md5_of "$WORK/test_logfilter.py")
GOT_LOG=$(md5_of "$WORK/sample.log")
TAMPERED=""
[ "$GOT_TEST" = "$MD5_TEST" ] || TAMPERED="$TAMPERED test_logfilter.py"
[ "$GOT_LOG" = "$MD5_LOG" ] || TAMPERED="$TAMPERED sample.log"
if [ -n "$TAMPERED" ]; then
    echo "FAIL [2/4] veraendert (read-only laut Auftrag):$TAMPERED"
    echo "           test_logfilter.py: $GOT_TEST (erwartet $MD5_TEST)"
    echo "           sample.log:        $GOT_LOG (erwartet $MD5_LOG)"
    FAIL=1
else
    echo "PASS [2/4] test_logfilter.py + sample.log unveraendert (md5)"
fi

# --- Check 3: Baseline-Suite weiterhin gruen ---------------------------------
BASE_OUT=$(cd "$WORK" && $TIMEOUT_PREFIX python3 test_logfilter.py 2>&1)
if [ $? -ne 0 ]; then
    echo "FAIL [3/4] Baseline-Suite gebrochen:"
    echo "$BASE_OUT" | sed 's/^/           /'
    FAIL=1
else
    echo "PASS [3/4] Baseline-Suite test_logfilter.py exit=0"
fi

# --- Check 4: die beiden neuen Features ---------------------------------------
cp "$FIXTURE_DIR/oracle_check.py" "$WORK/oracle_check.py"
FEAT_OUT=$(cd "$WORK" && $TIMEOUT_PREFIX python3 oracle_check.py 2>&1)
if [ $? -ne 0 ]; then
    echo "FAIL [4/4] Feature-Checks (ISO-Datumsbereich / Wochenend-Ausschluss):"
    echo "$FEAT_OUT" | sed 's/^/           /'
    FAIL=1
else
    echo "PASS [4/4] alle 7 Feature-Checks (inklusive Grenzen + --skip-weekends)"
fi

if [ $FAIL -eq 0 ]; then
    echo "ERGEBNIS: PASS — Endzustand nach Turn 3 korrekt"
    exit 0
fi
echo "ERGEBNIS: FAIL"
exit 1
