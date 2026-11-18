# Jarvis' zweites Gehirn

Dieses Repo ist das zweite Gehirn des Nutzers. Es wird von zwei Seiten benutzt:

- **Claude auf dem iPad / im Web** (Cloud-Sitzungen): liest und beschreibt den Ordner `gehirn/` direkt hier im Repo.
- **Jarvis auf dem Windows-PC**: `jarvis-wissensnetz/gehirn_sync.py` gleicht `gehirn/` mit dem Ordner `JarvisWissen` ab, sobald der PC läuft. Graphify baut daraus das Wissensnetz.

Der PC ist oft aus. Das Repo ist deshalb die gemeinsame Quelle: was hier landet, geht nicht verloren.

## Zu Beginn jeder Sitzung

1. `python3 gehirn.py uebersicht` ausführen und den Stand still lesen (nicht vorlesen).
2. Bei Fragen zu Person, Marken, Projekten, Marketing oder früheren Gesprächen erst `python3 gehirn.py suche <Wörter>` benutzen und die Treffer verwenden, statt zu raten.

## Während der Sitzung: merken

Sagt der Nutzer etwas Dauerhaftes (über sich, Marken wie Faith_Aesthetic, Produkte, Preise, Ziele, Kunden, Entscheidungen mit Grund, Marketing-Ergebnisse mit Zahlen, belegte Recherche) oder sagt er „merk dir“, „Jarvis soll wissen“, „speichern“:

```
python3 gehirn.py merken <thema> "<Fakt in einem klaren Satz>" --quelle "<Gespräch iPad / Link / Zahl>"
```

Themen: `ich`, `marken`, `marketing-erkenntnisse`, `projekte`, `entscheidungen`, `recherche`.
Hat sich ein Fakt geändert: `--ersetzt "<Teil der alten Zeile>"`. Danach in einer Zeile sagen: „Für Jarvis gemerkt: …“

Nicht speichern: Vermutungen, Smalltalk, Zwischenschritte, Passwörter, API-Keys, Kontodaten (das Werkzeug lehnt offensichtliche Geheimnisse ab). Wenn unklar ist, ob etwas stimmt: kurz nachfragen.

Längere Inhalte (Konzepte, Skripte, Ideen-Listen): `python3 gehirn.py notiz "<Titel>" --text "<Text>"`.

## Am Ende einer Sitzung mit Inhalt

Kurze Zusammenfassung ablegen (5–15 Zeilen: worum ging es, was wurde entschieden, was ist offen):

```
python3 gehirn.py gespraech "<Thema>" --text "<Zusammenfassung>"
```

## Speichern = committen und pushen

Änderungen in `gehirn/` gelten erst als gemerkt, wenn sie auf GitHub sind. Nach jedem Merken:

```
git add gehirn && git commit -m "Gehirn: <was>" && git push
```

Damit die nächste Sitzung das Wissen sieht, muss es auf dem Standard-Branch des Repos landen (neue Sitzungen starten von dort). Der Nutzer hat erlaubt, reine Gehirn-Änderungen (nur Dateien in `gehirn/`) zusätzlich direkt auf den Standard-Branch zu pushen:

```
git fetch origin && git push origin HEAD:refs/heads/$(git remote show origin | sed -n 's/.*HEAD branch: //p')
```

Schlägt das fehl (Branch weiter), erst `git pull --no-rebase --no-edit origin <Standard-Branch>` (Gehirn-Dateien werden per `.gitattributes` zeilenweise zusammengeführt), dann erneut pushen. Code-Änderungen außerhalb von `gehirn/` gehen wie üblich nur auf den Sitzungs-Branch.

## Aufbau

```
gehirn.py                 Werkzeug: uebersicht, suche, merken, notiz, gespraech
gehirn/fakten/            ein Fakt pro Zeile: "- Datum · Fakt · Quelle: …"
gehirn/notizen/           längere Notizen
gehirn/gespraeche/        Zusammenfassungen von Claude-Gesprächen
jarvis-wissensnetz/       PC-Seite: Graphify-Dienst, Jarvis-Anbindung, Sync, Marketing-Startwissen
```
