---
name: jarvis-merken
description: Speichert gesicherte neue Informationen aus dem Gespräch in Jarvis' Gehirn (Ordner JarvisWissen\fakten). Immer nutzen, wenn der Nutzer etwas Dauerhaftes über sich, seine Projekte, Marken, Kunden, Entscheidungen oder Marketing-Erkenntnisse sagt oder "merk dir", "Jarvis soll wissen", "speichern" sagt. Auch nutzen, wenn eine Recherche ein belegtes Ergebnis liefert, das später nützlich ist.
---

# Jarvis merken

Jarvis ist der persönliche Assistent des Nutzers. Sein Gehirn ist ein Graphify-Wissensnetz über den Ordner `%USERPROFILE%\JarvisWissen`. Alles, was dort als Datei landet, lernt Jarvis innerhalb von Sekunden.

## Was gespeichert wird
Nur **richtige, dauerhafte** Informationen:
- Fakten über den Nutzer, seine Marken (z. B. Faith_Aesthetic), Produkte, Preise, Ziele, Termine
- Entscheidungen ("wir machen ab jetzt …") mit Grund
- Marketing-Erkenntnisse mit Beleg: was funktioniert hat, Zahlen aus Analytics, gewonnene Hooks
- Ergebnisse von Recherchen, mit Quelle

Nicht speichern: Vermutungen, Smalltalk, Zwischenschritte, Passwörter, API-Keys, Kontodaten.
Wenn unklar ist, ob etwas stimmt: kurz nachfragen statt raten.

## Wie
1. Passende Themendatei wählen oder anlegen in `%USERPROFILE%\JarvisWissen\fakten\`:
   `ich.md`, `marken.md`, `marketing-erkenntnisse.md`, `projekte.md`, `entscheidungen.md`, `recherche.md`
2. Am Ende anhängen, ein Fakt pro Zeile, im Format:
   `- 2026-11-09 · <Fakt in einem klaren Satz> · Quelle: <Gespräch / Link / Zahl>`
3. Steht der Fakt schon da und hat sich geändert: alte Zeile durch die neue ersetzen und `(aktualisiert)` dazuschreiben. Keine Dopplungen.
4. Dem Nutzer in einer Zeile sagen, was gespeichert wurde: „Für Jarvis gemerkt: …“

Der Wissensnetz-Dienst merkt die Änderung und baut das Netz automatisch neu.
