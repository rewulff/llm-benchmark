#!/usr/bin/env bash
# Startet Ornith-1.5 als GGUF mit nativem MTP-Head und llama.cpp-WebUI.
#
# NUR ZUM TESTEN, NUR AUF ZURUF (rwu 01.10.2026). Hauptinferenzserver ist omlx :1235,
# dessen WebUI reicht fuer Modellwechsel und Betrieb. Dieser Server haelt sein Modell in
# Metal-Buffern (unsichtbar im RSS) und drueckt das omlx-Memory-Ceiling von ~26 auf 5,5 GiB —
# der omlx-Knecht (20 GiB) laedt dann nicht mehr. Nach dem Test wieder beenden:
#   pkill -f llama-server
# WebUI danach: http://127.0.0.1:1236 — die brew-Bottle liefert KEINE WebUI-Assets mit
# (404 auf /), daher wird der separat gebaute Build per --path serviert.
# Build erneuern: scratchpad/build-llama-webui.sh (Quelle: llama.cpp tools/ui, Commit 7fe450e)
# Kontext 64k: unser gemessenes Maximum lag bei 45.614 Prompt-Token (r1, 15 Tool-Calls),
# 32k haette das nicht getragen. KV in q8_0 — halbiert den Cache, bei 8 Bit ohne
# messbaren Qualitaetsverlust (anders als TurboQuant 3-bit in MLX, das 5/10 Fixtures riss).
# MTP ist AUS: gemessen 01.10. macht der native MTP-Head Ornith langsamer
# (34,9 statt 48,2 tok/s, draft acceptance nur 38,2 %) — MoE profitiert nicht von
# Spekulation, anders als dense (ThinkingCap: 94,9 % Acceptance, 1,2-1,66x).
# Port 1236, weil 1235 von omlx belegt ist — beide koennen parallel laufen,
# aber NICHT beide gleichzeitig ein grosses Modell geladen halten (RAM).
set -uo pipefail
PORT=${PORT:-1236}
GGUF=$(ls ~/.cache/huggingface/hub/models--mudler--Ornith-1.5-35B-A3B-APEX-MTP-GGUF/snapshots/*/Ornith-1.5-35B-A3B-APEX-MTP-Balanced.gguf 2>/dev/null | head -1)
MMPROJ=$(ls ~/.cache/huggingface/hub/models--mudler--Ornith-1.5-35B-A3B-APEX-MTP-GGUF/snapshots/*/mmproj.gguf 2>/dev/null | head -1)
[ -z "$GGUF" ] && { echo "GGUF nicht gefunden — Download noch nicht fertig?"; exit 1; }

pkill -f "llama-server.*--port $PORT" 2>/dev/null; sleep 1
echo "Modell : $(basename "$GGUF") ($(du -h "$GGUF" | cut -f1))"
echo "WebUI  : http://127.0.0.1:$PORT"
echo "MTP    : AUS (gemessen: 34,9 mit vs 48,2 tok/s ohne — MoE-Spekulation lohnt nicht)"
exec llama-server -m "$GGUF" ${MMPROJ:+--mmproj "$MMPROJ"} \
  --port "$PORT" --host 127.0.0.1 \
  -ngl 99 -c 65536 --jinja \
  --path "$HOME/.local/share/llama-webui" \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --spec-type none \
  --temp 0.6 --top-p 0.95 --top-k 20
