#!/usr/bin/env bash
# Wartet auf das Ende des Benchmarks und laesst den Server dann dauerhaft laufen (WebUI).
set -uo pipefail
cd "$(dirname "$0")"
OUT=/private/tmp/claude-501/-Users-rwu-Arbeitsverzeichnis/f82e366c-03f9-4119-97d5-842bfa1ff161/scratchpad/gguf-mtp.out
until grep -q "GGUF-MTP-TEST FERTIG" "$OUT" 2>/dev/null; do sleep 30; done
sleep 5
echo "[$(date +%H:%M:%S)] Benchmark durch — starte Dauerbetrieb mit WebUI"
exec ./start-ornith-gguf.sh
