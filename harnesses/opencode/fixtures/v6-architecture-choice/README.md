# v6-architecture-choice — Architektur-Entscheidung unter Constraints

## Zweck

Testet ob ein Modell eine technische Design-Entscheidung unter mehreren, teilweise
konkurrierenden Constraints treffen und begruenden kann. Es gibt keine einzig richtige
Antwort — mehrere Architekturen sind valide (Kafka, NATS, RabbitMQ-Cluster, SQS/SNS,
Redis Streams). Bewertet wird die Konsistenz von Entscheidung, Begruendung und
Failure-Mode-Analyse.

## Erwarteter Modell-Prozess

1. Constraints analysieren und Spannungsfelder identifizieren:
   - Budget vs. Durability (Managed Services teuer, Self-hosted komplex)
   - Geo-Latenz vs. Order-Guarantees (verteilte Queues + FIFO = komplex)
2. Ein konkretes Pattern auswaehlen und Alternativen explizit abwaegen
3. Happy-Path als ASCII-Sequenzdiagramm skizzieren
4. Pro Constraint: Was passiert bei Verletzung? Wie reagiert die Architektur?
5. Ergebnis in `design.md` schreiben

## Reasoning-Anforderung

Reine Pattern-Wiedergabe genuegt nicht. Das Modell muss:
- Trade-offs zwischen Budget, Komplexitaet und Garantien explizit benennen
- Eine konsistente Linie durch alle Constraint-Antworten ziehen
- Das ASCII-Diagramm muss zum gewaehlten Pattern passen

## Oracle-Status: STUB

Der aktuelle Oracle prueft nur:
- `design.md` existiert und hat >= 30 Zeilen
- Alle 5 Constraints-Schluesselwoerter kommen vor (Heuristik, keine Semantik)

## TODO — Vollausbau (LLM-as-judge)

- [ ] Scoring-Rubrik definieren:
  - 0-2: Jeder Constraint explizit adressiert (5 Punkte)
  - 0-2: Alternativen wurden begruendet abgelehnt
  - 0-2: Failure-Mode-Analyse konsistent mit gewaehltem Pattern
  - 0-2: ASCII-Diagramm entspricht dem beschriebenen Pattern
  - 0-2: Budget-Kalkulation plausibel (reale Preise genannt oder begruendet)
- [ ] Judge-Prompt schreiben: gibt Score 0-10 + Begruendung als JSON
- [ ] Pass-Schwelle festlegen (Vorschlag: >= 6/10)
- [ ] oracle.sh um LLM-Judge-Call erweitern (via local-llm Backend)
- [ ] Referenz-Loesungen fuer Kafka- und NATS-Pfad dokumentieren (als Ground-Truth fuer Judge-Kalibrierung)

## Valide Loesungs-Pfade

| Pattern | Valide? | Hinweis |
|---------|---------|---------|
| Apache Kafka / Redpanda | Ja | Komplex, aber guenstig self-hosted |
| AWS SQS + SNS | Ja | FIFO-Queues, ~$50/Monat bei 10k/h |
| NATS JetStream | Ja | Leichtgewichtig, gut fuer Budget |
| RabbitMQ Cluster | Ja | Klassisch, Quorum-Queues fuer Durability |
| Redis Streams | Bedingt | Ohne Persistence-Config riskant |
| HTTP/REST direkt | Nein | Erfullt Constraint-3 (Downtime) nicht |
