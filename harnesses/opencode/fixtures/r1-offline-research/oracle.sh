#!/bin/bash
# Oracle fuer Fixture r1-offline-research.
# Wird im job_dir aufgerufen (nicht in work/) — adressiert work/ als Subpfad.
# Deterministisch, kein LLM: grep auf work/answers.md.
#
# Drei Gruppen:
#   A) Kernfakten     — die 4 richtigen Antworten
#   B) Zitate         — die jeweils tragende Quelldatei ist genannt
#   C) Decoy-Negativ  — die falschen Faehrten tauchen NICHT als Antwort auf
# PASS nur wenn alle drei Gruppen halten (plus Integritaet der Dokumente).
# Exit 0 = PASS, Exit 1 = FAIL.
set -u

WORK="work"
ANS="$WORK/answers.md"
FAIL=0

# md5 der unveraenderten Dokumentensammlung (alle *.md/*.txt ausser answers.md,
# LC_ALL=C-sortiert konkateniert). Neu berechnen bei absichtlicher Aenderung:
#   find input -maxdepth 1 -type f \( -name '*.md' -o -name '*.txt' \) \
#     ! -name 'answers.md' | LC_ALL=C sort | xargs cat | md5
MD5_DOCS="4f9040cc3431c53c2db902ee4c0d1f8c"

md5_stdin() {
    if command -v md5sum >/dev/null 2>&1; then
        md5sum | awk '{print $1}'
    else
        md5 -q
    fi
}

# --- Vorbedingung: answers.md existiert --------------------------------------
if [ ! -f "$ANS" ]; then
    echo "FAIL [pre] $ANS wurde nicht angelegt"
    echo "ERGEBNIS: FAIL"
    exit 1
fi
echo "PASS [pre] $ANS vorhanden"

# --- Vorbedingung: Dokumente unveraendert ------------------------------------
GOT_DOCS=$(find "$WORK" -maxdepth 1 -type f \( -name '*.md' -o -name '*.txt' \) \
    ! -name 'answers.md' | LC_ALL=C sort | xargs cat | md5_stdin)
if [ "$GOT_DOCS" != "$MD5_DOCS" ]; then
    echo "FAIL [pre] Dokumentensammlung veraendert (md5 $GOT_DOCS, erwartet $MD5_DOCS)"
    FAIL=1
else
    echo "PASS [pre] Dokumentensammlung unveraendert (md5)"
fi

# --- Extraktion: Block / Answer-Zeile / Sources-Zeile pro Frage ---------------
qblock() {
    local n="$1"
    local next=$((n + 1))
    if [ "$n" -ge 4 ]; then
        sed -n "/^##[[:space:]]*[Qq]4/,\$p" "$ANS"
    else
        sed -n "/^##[[:space:]]*[Qq]$n/,/^##[[:space:]]*[Qq]$next/p" "$ANS"
    fi
}

answer_of() { qblock "$1" | grep -i -m1 "^[[:space:]]*Answer:"; }
sources_of() { qblock "$1" | grep -i -m1 "^[[:space:]]*Sources:"; }

must() {   # label, text, regex  — Text MUSS matchen
    if printf '%s' "$2" | grep -qiE "$3"; then
        echo "PASS $1"
    else
        echo "FAIL $1  (Zeile: ${2:-<fehlt>})"
        FAIL=1
    fi
}

must_not() {   # label, text, regex — Text darf NICHT matchen
    if printf '%s' "$2" | grep -qiE "$3"; then
        echo "FAIL $1  (Zeile: ${2:-<fehlt>})"
        FAIL=1
    else
        echo "PASS $1"
    fi
}

A1=$(answer_of 1); S1=$(sources_of 1)
A2=$(answer_of 2); S2=$(sources_of 2)
A3=$(answer_of 3); S3=$(sources_of 3)
A4=$(answer_of 4); S4=$(sources_of 4)

# --- Gruppe A: Kernfakten ----------------------------------------------------
echo "-- A: Kernfakten"
must     "[A1] Q1 nennt Release 2.4"                 "$A1" "2\.4"
must     "[A2] Q2 nennt chunk_strategy"              "$A2" "chunk_strategy"
must     "[A3] Q2 nennt den Wert fixed"              "$A2" "\bfixed\b"
must     "[A4] Q3 nennt Brightwave"                  "$A3" "brightwave"
must     "[A5] Q3 nennt Version 2.3.2"               "$A3" "2\.3\.2"
must     "[A6] Q4 nennt Release 2.7"                 "$A4" "2\.7"
must     "[A7] Q4 nennt Ticket KES-914"              "$A4" "KES-?914"

# --- Gruppe B: Zitate --------------------------------------------------------
echo "-- B: Zitate"
must     "[B1] Q1 zitiert CHANGELOG.md"              "$S1" "CHANGELOG"
must     "[B2] Q2 zitiert config-reference-2.6.md"   "$S2" "config-reference-2\.6"
must     "[B3] Q3 zitiert log-brightwave-*"          "$S3" "log-brightwave"
must     "[B4] Q4 zitiert meeting-notes-2026-06-16"  "$S4" "meeting-notes-2026-06-16"

# --- Gruppe C: Decoy-Negativchecks -------------------------------------------
echo "-- C: Decoys"
must_not "[C1] Q1 faellt nicht auf 2.3 herein"       "$A1" "2\.3"
must_not "[C2] Q2 faellt nicht auf chunk_size_mb=64" "$A2" "chunk_size_mb.*64|64.*chunk_size_mb"
must_not "[C3] Q3 nennt nicht Northwind/ACME"        "$A3" "northwind|acme"
must_not "[C4] Q4 nennt nicht das erledigte KES-877" "$A4" "KES-?877"
ALL_SOURCES=$(printf '%s\n%s\n%s\n%s' "$S1" "$S2" "$S3" "$S4")
must_not "[C5] keine Decoy-Datei als Beleg zitiert"  "$ALL_SOURCES" "support-playbook|wiki-tuning-guide"

if [ $FAIL -eq 0 ]; then
    echo "ERGEBNIS: PASS — alle 4 Fakten belegt, keine Decoy-Faehrte uebernommen"
    exit 0
fi
echo "ERGEBNIS: FAIL"
exit 1
