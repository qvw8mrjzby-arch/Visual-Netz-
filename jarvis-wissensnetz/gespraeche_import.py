"""Holt deine Gespräche mit Claude in Jarvis' Gehirn.

Zwei Quellen:
1. Claude Code auf diesem PC: liest die Verläufe aus  %USERPROFILE%\\.claude\\projects
   (läuft automatisch, jedes Mal wenn der Wissensnetz-Dienst prüft).
2. Claude-App / claude.ai: dort gibt es keinen direkten Zugriff. Exportiere deine
   Daten unter Einstellungen > Datenschutz > Daten exportieren. Die ZIP-Datei aus
   der Mail einfach in den Ordner  JarvisWissen\\_import  legen, der Rest passiert
   automatisch.

Jedes Gespräch wird als lesbare Markdown-Datei in  JarvisWissen\\gespraeche\\
gespeichert. Graphify zieht daraus die Fakten und Verbindungen ins Netz.
Werkzeug-Ausgaben (Dateiinhalte, Befehle) werden weggelassen, nur das, was
gesagt wurde, kommt rein.
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from jarvis_wissen import lade_config

MIN_ZEICHEN = 200  # ganz kurze Gespräche ("hi") überspringen


def _sicherer_name(text: str, laenge: int = 60) -> str:
    text = re.sub(r"[^\w\- äöüÄÖÜß]", "", text).strip().replace(" ", "_")
    return (text or "gespraech")[:laenge]


def _text_aus_inhalt(inhalt) -> str:
    if isinstance(inhalt, str):
        return inhalt
    teile = []
    for block in inhalt or []:
        if isinstance(block, dict) and block.get("type") == "text":
            teile.append(block.get("text", ""))
    return "\n".join(teile)


def _schreiben(ziel: Path, titel: str, datum: str, nachrichten: list[tuple[str, str]], quelle: str) -> bool:
    text = "\n\n".join(f"**{wer}:** {was.strip()}" for wer, was in nachrichten if was.strip())
    if len(text) < MIN_ZEICHEN:
        return False
    inhalt = f"# {titel}\n\nDatum: {datum}  \nQuelle: {quelle}\n\n{text}\n"
    if ziel.exists() and ziel.read_text(encoding="utf-8") == inhalt:
        return False  # unverändert: nichts tun, damit graphify nicht neu liest
    ziel.write_text(inhalt, encoding="utf-8")
    return True


def claude_code_importieren(ziel_ordner: Path) -> int:
    quelle = Path.home() / ".claude" / "projects"
    if not quelle.exists():
        return 0
    neu = 0
    for datei in quelle.rglob("*.jsonl"):
        nachrichten: list[tuple[str, str]] = []
        datum = ""
        titel = ""
        try:
            zeilen = datei.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for zeile in zeilen:
            try:
                e = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            if e.get("type") == "summary" and e.get("summary"):
                titel = e["summary"]
            if e.get("type") not in ("user", "assistant") or e.get("isMeta"):
                continue
            msg = e.get("message") or {}
            text = _text_aus_inhalt(msg.get("content"))
            if not text or text.startswith(("<command-", "<local-command", "<system-reminder")):
                continue
            datum = datum or (e.get("timestamp") or "")[:10]
            wer = "Ich" if e["type"] == "user" else "Claude"
            nachrichten.append((wer, text))
        if not nachrichten:
            continue
        titel = titel or nachrichten[0][1].splitlines()[0][:80]
        name = f"{datum}_code_{_sicherer_name(titel, 40)}_{datei.stem[:8]}.md"
        if _schreiben(ziel_ordner / name, titel, datum, nachrichten, "Claude Code"):
            neu += 1
    return neu


def claude_export_importieren(import_ordner: Path, ziel_ordner: Path) -> int:
    neu = 0
    for zip_datei in sorted(import_ordner.glob("*.zip")):
        try:
            with zipfile.ZipFile(zip_datei) as z:
                name = next((n for n in z.namelist() if n.endswith("conversations.json")), None)
                if not name:
                    continue
                gespraeche = json.loads(z.read(name).decode("utf-8"))
        except (zipfile.BadZipFile, json.JSONDecodeError, OSError):
            continue
        for g in gespraeche:
            nachrichten = []
            for m in g.get("chat_messages", []):
                text = m.get("text") or _text_aus_inhalt(m.get("content"))
                wer = "Ich" if m.get("sender") == "human" else "Claude"
                nachrichten.append((wer, text or ""))
            titel = g.get("name") or "Ohne Titel"
            datum = (g.get("created_at") or "")[:10]
            datei = f"{datum}_app_{_sicherer_name(titel, 40)}_{(g.get('uuid') or '')[:8]}.md"
            if _schreiben(ziel_ordner / datei, titel, datum, nachrichten, "Claude-App"):
                neu += 1
    return neu


def alles_importieren() -> int:
    ordner = Path(lade_config()["ordner"])
    ziel = ordner / "gespraeche"
    ziel.mkdir(parents=True, exist_ok=True)
    import_ordner = ordner / "_import"
    import_ordner.mkdir(parents=True, exist_ok=True)
    return claude_code_importieren(ziel) + claude_export_importieren(import_ordner, ziel)


if __name__ == "__main__":
    print(f"{alles_importieren()} Gespräche neu oder aktualisiert.")
