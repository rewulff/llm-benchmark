# Prompt-Patterns für OpenCode-Delegationen

Empirisch validierte Prompt-Bausteine für Agent-Tasks mit lokalen LLMs.
Basis sind Produktiv-Tests (Issue #170, v6-produktiv-fqdn-bug) — nicht theoretische Best-Practices.

---

## Pattern: Small-Diff-Constraint

### Problem

Gemma-4-26B-A4B (und vermutlich andere Modelle dieser Größenklasse) interpretieren Bug-Fix-Tasks standardmäßig als *"ganze Funktion neu schreiben"*. Der generierte `edit`-Tool-Call mit massivem `newString` trifft dann das Output-Token-Cap (~32000 bei `@ai-sdk/openai-compatible`). Abgeschnittenes JSON → `invalid tool_use` → Session-Chaos.

### Symptome im Event-Stream

- `step_finish.reason: "length"` (statt `"stop"` oder `"tool-calls"`)
- `step_finish.tokens.output >= 32000`
- Nachfolgend `tool_use.tool: "invalid"` mit JSON-Parsing-Fehler
- Modell retry't → exzessive Step-Zahl (20+), eventuell Aufgabe

### Fix — Diff-Regel als Prompt-Suffix

```markdown
## Diff-Regel (kritisch!)
- `oldString` = 2-5 Zeilen (nur die direkt betroffenen)
- `newString` = so klein wie möglich, maximal ±30 Zeilen vs `oldString`
- NIEMALS ganze Funktionen neu schreiben — nur die geänderten Zeilen
- Eine einzelne `edit`-Operation bevorzugen
```

### Empirischer Effekt (Issue #170-Pattern)

| Metrik | ohne Regel | mit Regel |
|---|---|---|
| Output-Tokens | 32000 (truncated) | **335** |
| Steps | 21 (Chaos) | **5** |
| Duration | 502s | **36s** |
| Stop-Reason | `length` | **`stop`** |
| Oracle | FAIL | **7/7 PASS** |
| Fix-Qualität | korrumpiert | **besser als baseline** (nutzt `urllib.parse.urlparse`) |

**95× weniger Output-Tokens, klarer Abschluss, höhere Code-Qualität.**

### Warum "besser als baseline"?

Kleine Diffs **zwingen** das Modell zu punktuellen, überlegteren Änderungen. Bei Full-Rewrites tendiert es zu Reasoning-im-Code (inline Pseudo-Code-Kommentare) und Token-Drift (`true` statt `True`, `branch::` statt `branch:`, ähnliche Doppelbuchstaben-Artefakte).

---

## Pattern: Abschluss-Trigger

### Problem
Ohne klares End-Signal fragt das Modell nach weiteren Anweisungen statt zu beenden.

### Fix
```markdown
## Abschluss
Nach dem Edit: kurze `CHANGES.md` (max 15 Zeilen), dann antworte mit "DONE".
Nicht weiter nachfragen.
```

Das explizite "Nicht weiter nachfragen" ist wichtig — sonst öffnet das Modell gerne mit "What would you like me to do next?".

---

## Pattern: Scope-Limitierung

### Problem
Modell wandert ab in verwandte aber unangeforderte Refactorings.

### Fix
```markdown
## Scope (strikt!)
- Nur `{pfad/zur/datei}` ändern
- Andere Dateien NICHT anfassen
- Imports nicht re-organisieren, keine Style-Changes
```

---

## Pattern: DACH-Compliance (deutsche Webseiten)

### Problem

Internationale Modelle wie Gemma-4 oder Qwen arbeiten nach US-Landingpage-Mustern und vergessen dabei systematisch die rechtlichen Pflichten deutscher Webseiten. Beispiel aus dem Brezel-Bistro-Test (21.04.2026): Gemma-4-26B-A4B hat eine vollständig wirkende Landingpage gebaut — ohne Impressum, ohne Datenschutz-Erklärung, ohne Hinweise auf §5 TMG oder DSGVO.

Das ist kein Bug des Modells, sondern eine Scope-Lücke der Default-Prompts. Wenn nicht explizit erwähnt, kommt es nicht.

### Wer ist betroffen

Jede geschäftsmäßige Webseite in Deutschland muss enthalten:
- **Impressum** (§5 TMG) — Verantwortliche, Adresse, Kontakt, ggf. Registernummer, USt-IdNr
- **Datenschutz-Erklärung** (DSGVO Art. 13) — Verantwortlicher, erhobene Daten, Rechtsgrundlage, Betroffenenrechte
- **Cookie-Banner** — nur wenn Tracking/Analytics/Third-Party-Cookies eingebunden werden
- Bei Webshops zusätzlich: AGB, Widerrufsbelehrung, Preisangaben nach PAngV

### Fix — Standard-Prompt-Suffix bei kommerziellen deutschen Webseiten

```markdown
## DACH-Compliance (Pflicht für kommerzielle Webseiten in Deutschland)

Plane folgendes automatisch mit ein:
- Footer-Links: `Impressum` und `Datenschutz` (beide obligatorisch)
- Stub-Datei `impressum.html` mit Platzhaltern für: Firmenname, Adresse,
  Vertretungsberechtigter, Kontakt, Handelsregister-Eintrag, USt-IdNr
- Stub-Datei `datenschutz.html` mit Platzhalter-Sektionen für:
  Verantwortlicher, erhobene Daten, Rechtsgrundlage, Betroffenenrechte, Kontakt
- ALLE Platzhalter eindeutig kennzeichnen (z.B. `[PLATZHALTER — vom Kunden ersetzen]`)
- KEINE erfundenen Rechtstexte, KEINE plausible klingenden Phantasie-Daten
```

### Warum "Platzhalter" statt fertigem Rechtstext

Ein LLM darf keine rechtsverbindlichen Texte generieren — weder für Impressum noch für Datenschutz. Diese müssen vom Kunden oder einem Anwalt erstellt werden. Das Modell darf nur **Gerüst + Sektionen** liefern, nicht die rechtliche Substanz.

Der Prompt muss diese Grenze klar ziehen, sonst halluziniert das Modell plausibel klingende Nonsense-Texte die dann aus Versehen produktiv gehen.

---

## Checkliste für neue Produktiv-Fixtures

- [ ] Prompt enthält Small-Diff-Regel
- [ ] Prompt enthält Abschluss-Trigger (`"DONE"` + "nicht weiter nachfragen")
- [ ] Prompt enthält Scope-Limitierung
- [ ] Oracle prüft Syntax (`py_compile`)
- [ ] Oracle prüft Lint (`ruff --select F`) — oder Fallback auf `grep -qE "=\s*(true|false)\s*[,)]"`
- [ ] Oracle prüft Heuristik gegen Pseudo-Code-Kommentar-Blöcke (≥6 zusammenhängende `#`-Zeilen)

Siehe `fixtures/v6-produktiv-fqdn-bug/` als Referenz-Implementation.
