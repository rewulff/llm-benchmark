#!/bin/bash
# Oracle fuer Fixture c1-dependent-pipeline.
# Wird im job_dir aufgerufen (nicht in work/) — adressiert work/ als Subpfad.
# Deterministisch, kein LLM: md5-Integritaet + py_compile + Test-Exit-Code.
# Exit 0 = PASS, Exit 1 = FAIL.
set -u

WORK="work"
FAIL=0

# md5 der unveraenderten Fixture-Dateien (input/-Stand, LF-Zeilenenden).
# Neu berechnen wenn die Fixture-Dateien absichtlich geaendert werden:
#   md5 -q input/test_pipeline.py input/sample.json     (macOS)
#   md5sum input/test_pipeline.py input/sample.json     (Linux)
MD5_TEST="7337b40f4510fc27c1f3910d154973c1"
MD5_DATA="bfdfd3ab0c7341c9b1d8f06c565816ad"

md5_of() {
    if command -v md5sum >/dev/null 2>&1; then
        md5sum "$1" | awk '{print $1}'
    else
        md5 -q "$1"
    fi
}

# Portables Timeout (macOS hat weder timeout noch gtimeout out of the box).
TIMEOUT_PREFIX=""
if command -v timeout >/dev/null 2>&1; then
    TIMEOUT_PREFIX="timeout 60"
elif command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT_PREFIX="gtimeout 60"
fi

# --- Check 1: alle Dateien vorhanden -----------------------------------------
MISSING=""
for f in config_loader.py pipeline.py report.py test_pipeline.py sample.json; do
    [ -f "$WORK/$f" ] || MISSING="$MISSING $f"
done
if [ -n "$MISSING" ]; then
    echo "FAIL [1/4] Dateien fehlen in $WORK/:$MISSING"
    FAIL=1
    # Ohne Dateien sind die restlichen Checks sinnlos.
    echo "ERGEBNIS: FAIL"
    exit 1
fi
echo "PASS [1/4] alle 5 Dateien in $WORK/ vorhanden"

# --- Check 2: Test und Daten unveraendert ------------------------------------
GOT_TEST=$(md5_of "$WORK/test_pipeline.py")
GOT_DATA=$(md5_of "$WORK/sample.json")
TAMPERED=""
[ "$GOT_TEST" = "$MD5_TEST" ] || TAMPERED="$TAMPERED test_pipeline.py"
[ "$GOT_DATA" = "$MD5_DATA" ] || TAMPERED="$TAMPERED sample.json"
if [ -n "$TAMPERED" ]; then
    echo "FAIL [2/4] veraendert (Contract-Dateien sind read-only):$TAMPERED"
    echo "           test_pipeline.py: $GOT_TEST (erwartet $MD5_TEST)"
    echo "           sample.json:      $GOT_DATA (erwartet $MD5_DATA)"
    FAIL=1
else
    echo "PASS [2/4] test_pipeline.py + sample.json unveraendert (md5)"
fi

# --- Check 3: die drei Module kompilieren ------------------------------------
COMPILE_OUT=$(cd "$WORK" && python3 -m py_compile config_loader.py pipeline.py report.py 2>&1)
if [ $? -ne 0 ]; then
    echo "FAIL [3/4] Syntaxfehler in den Modulen:"
    echo "$COMPILE_OUT" | sed 's/^/           /'
    FAIL=1
else
    echo "PASS [3/4] config_loader.py, pipeline.py, report.py kompilieren"
fi

# --- Check 4: Test-Suite laeuft durch ----------------------------------------
TEST_OUT=$(cd "$WORK" && $TIMEOUT_PREFIX python3 test_pipeline.py 2>&1)
TEST_RC=$?
if [ $TEST_RC -ne 0 ]; then
    echo "FAIL [4/4] test_pipeline.py exit=$TEST_RC:"
    echo "$TEST_OUT" | sed 's/^/           /'
    FAIL=1
else
    echo "PASS [4/4] test_pipeline.py exit=0 (alle 3 Stufen)"
fi

if [ $FAIL -eq 0 ]; then
    echo "ERGEBNIS: PASS — Bug-Kette vollstaendig aufgeloest"
    exit 0
fi
echo "ERGEBNIS: FAIL"
exit 1
