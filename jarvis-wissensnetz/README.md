# Jarvis-Wissensnetz

Ein Graphify-Wissensnetz auf deinem Windows-PC, das sich selbst aktuell hält und mit deinem Jarvis verbunden ist.

```
Dein Ordner  ──►  Wissensnetz-Dienst  ──►  graph.json  ──►  jarvis_wissen.py  ──►  Jarvis
(Dokumente)       (läuft im Hintergrund,    (das Netz)       (lädt automatisch
                   baut bei Änderungen neu)                   neu, beantwortet Fragen)
```

## Einrichten (einmalig, ca. 5 Minuten)

1. Diesen Ordner `jarvis-wissensnetz` auf deinen PC kopieren, z. B. nach `C:\Jarvis\jarvis-wissensnetz`.
2. **Doppelklick auf `installieren.bat`.** Das Skript
   - prüft Python (3.10 oder neuer),
   - fragt, welche KI deine Dokumente lesen soll (Claude, Gemini oder Ollama lokal),
   - installiert graphify,
   - speichert deinen API-Key in deinen Windows-Benutzervariablen (er wird beim Tippen nicht angezeigt),
   - legt den Wissens-Ordner an (Standard: `C:\Users\<du>\JarvisWissen`),
   - richtet den Autostart ein und startet den Dienst sofort.
3. Dateien in den Wissens-Ordner legen: Notizen (`.md`, `.txt`), PDFs, Word, Excel, Bilder, Code. Nach etwa 20 Sekunden Ruhe baut sich das Netz neu.

## Was in Jarvis' Gehirn landet

```
JarvisWissen\
  marketing\    Startwissen: Hooks, Copywriting, Kurzvideo-Strategie, Funnel, Kennzahlen
  fakten\       gesicherte Fakten, die Claude mit dem Skill "jarvis-merken" einträgt
  gespraeche\   deine Claude-Gespräche als Text (automatisch)
  _import\      hier die Export-ZIP aus der Claude-App ablegen
```

**Gespräche mit Claude:**
- **Claude Code auf diesem PC:** wird alle 5 Minuten automatisch übernommen.
- **Claude-App / claude.ai:** dort kommt kein Programm direkt ran. Unter Einstellungen → Datenschutz → Daten exportieren die ZIP anfordern und in `JarvisWissen\_import` legen. Neue Exporte einfach dazulegen.
- **Gezielt merken:** Der Skill `jarvis-merken` bringt Claude bei, gesicherte Fakten (über dich, deine Marken, Marketing-Erkenntnisse mit Zahlen) sauber in `fakten\` einzutragen. Sag einfach „merk dir für Jarvis …“. Das Installationsskript legt ihn für Claude Code an; in der Claude-App lädst du `claude-skill\jarvis-merken\SKILL.md` unter Einstellungen → Fähigkeiten hoch.

Passwörter, Keys und Kontodaten gehören nicht in diese Ordner. Graphify schickt Dokumente zum Lesen an die gewählte KI.

## In Jarvis einbauen

```python
import sys
sys.path.insert(0, r"C:\Jarvis\jarvis-wissensnetz")   # Pfad anpassen
from jarvis_wissen import WissensNetz

netz = WissensNetz()

# Vor jeder Antwort das passende Wissen holen und der KI mitgeben:
wissen = netz.kontext_fuer_prompt(nutzer_text)
antwort = deine_ki(f"{wissen}\n\nFrage: {nutzer_text}")

# Optional: Jarvis sagt Bescheid, wenn neues Wissen da ist
netz.beobachten(lambda n: print("Neues Wissen:", n.statistik()))
```

Ein vollständiges Beispiel steht in `beispiel_jarvis.py`.

| Funktion | Was sie macht |
|---|---|
| `netz.frage(text)` | Breite Suche: alles, was mit dem Thema verbunden ist, mit Fundstellen |
| `netz.frage(text, tief=True)` | Einer Kette folgen: „Wie hängt A mit B zusammen?“ |
| `netz.kontext_fuer_prompt(text)` | Fertiger Textblock für den Prompt deiner KI |
| `netz.zentrale_themen()` | Die am stärksten vernetzten Themen |
| `netz.statistik()` | Anzahl Knoten und Verbindungen, Stand des Netzes |
| `netz.beobachten(funktion)` | Ruft deine Funktion auf, sobald das Netz neu gebaut wurde |

Jarvis bekommt immer den neuesten Stand: `WissensNetz` merkt bei jedem Aufruf, ob `graph.json` neu ist, und lädt es dann nach. Ist graphify installiert, nutzt das Modul dessen eigene Suche. Sonst sucht es mit einer einfachen Suche in reinem Python weiter, damit Jarvis nie abstürzt.

## Prüfen, ob alles läuft

- `wissensnetz.log` zeigt, wann gebaut wurde und ob Fehler auftraten.
- `status.json` zeigt den aktuellen Zustand (`bereit`, `baut`, `fehler`).
- Im Wissens-Ordner liegt `graphify-out\graph.html`. Doppelklick öffnet das Netz im Browser.
- Schnelltest in der Eingabeaufforderung: `python jarvis_wissen.py Auto Werkstatt`

## Kosten und Datenschutz

- **Code** wird lokal und kostenlos gelesen, ohne KI.
- **Dokumente, PDFs, Bilder** liest eine KI. Mit Claude oder Gemini gehen diese Inhalte an deren Server und kosten pro Nutzung. Graphify liest nur neue oder geänderte Dateien erneut. Mit **Ollama** bleibt alles auf deinem PC und ist gratis, dafür langsamer und etwas ungenauer.
- Die Kosten pro Lauf stehen in `graphify-out\cost.json`.

## Einstellungen (`config.json`)

| Feld | Bedeutung |
|---|---|
| `ordner` | Welcher Ordner überwacht wird |
| `backend` | `claude`, `gemini` oder `ollama` |
| `pruef_intervall_sekunden` | Wie oft der Dienst nachschaut (Standard 10) |
| `warten_nach_aenderung_sekunden` | Wie lange nach der letzten Änderung gewartet wird, bevor neu gebaut wird (Standard 20) |

## Ausschalten

Verknüpfung `Jarvis Wissensnetz` aus dem Autostart-Ordner löschen (`Win+R`, `shell:startup`) und im Task-Manager den Prozess `pythonw.exe` beenden.
