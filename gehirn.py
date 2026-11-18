"""Jarvis' zweites Gehirn: lesen, suchen und dazulernen.

Das Gehirn liegt als Markdown-Dateien im Ordner `gehirn/` dieses Repos.
Jede Claude-Sitzung (iPad, Web, PC) kann es lesen und beschreiben, und der
Jarvis-Dienst auf dem PC gleicht es mit dem Ordner JarvisWissen ab
(siehe jarvis-wissensnetz/gehirn_sync.py).

    python3 gehirn.py uebersicht
    python3 gehirn.py suche Hooks Faith
    python3 gehirn.py merken marken "Faith_Aesthetic verkauft ab jetzt auch Hoodies" --quelle "Gespräch iPad"
    python3 gehirn.py notiz "Ideen Winter-Kampagne" < text.md
    python3 gehirn.py gespraech "Second Brain fürs iPad" < zusammenfassung.md

Nur Python-Standardbibliothek, läuft überall.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
GEHIRN = WURZEL / "gehirn"
# Zusätzlich durchsucht: das Startwissen des Wissensnetzes (Marketing)
WEITERE_QUELLEN = [WURZEL / "jarvis-wissensnetz" / "wissen"]

THEMEN = {
    "ich": "Über mich",
    "marken": "Meine Marken",
    "marketing-erkenntnisse": "Marketing-Erkenntnisse",
    "projekte": "Projekte",
    "entscheidungen": "Entscheidungen",
    "recherche": "Recherche-Ergebnisse",
}

# Was nie ins Gehirn darf
GEHEIM = re.compile(
    r"(sk-ant-|sk-[A-Za-z0-9]{20}|ghp_|github_pat_|AIza[0-9A-Za-z_-]{20}|passwort\s*[:=]|password\s*[:=]|"
    r"\bIBAN\b\s*[:=]?\s*[A-Z]{2}\d{2})",
    re.IGNORECASE,
)


def _dateien() -> list[Path]:
    alle = []
    for basis in [GEHIRN, *WEITERE_QUELLEN]:
        if basis.exists():
            alle += sorted(p for p in basis.rglob("*.md") if not p.name.startswith("."))
    return alle


def _rel(p: Path) -> str:
    return str(p.relative_to(WURZEL))


def _geheim_pruefen(text: str) -> None:
    if GEHEIM.search(text):
        sys.exit("Abgelehnt: Der Text sieht nach Passwort, Key oder Kontodaten aus. Das gehört nicht ins Gehirn.")


def _name(text: str, laenge: int = 50) -> str:
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"), ("ß", "ss")):
        text = text.replace(alt, neu)
    text = re.sub(r"[^A-Za-z0-9\- ]", "", text).strip().replace(" ", "_")
    return (text or "eintrag")[:laenge]


# ---------- Lesen ----------

def uebersicht() -> str:
    zeilen = ["# Jarvis-Gehirn: Übersicht", ""]
    fakten_ordner = GEHIRN / "fakten"
    zeilen.append("## Fakten (vollständig)")
    for datei in sorted(fakten_ordner.glob("*.md")):
        eintraege = [z for z in datei.read_text(encoding="utf-8").splitlines() if z.startswith("- ")]
        if eintraege:
            zeilen.append(f"\n### {datei.stem}  ({_rel(datei)})")
            zeilen += eintraege
    for ordner, titel in (("gespraeche", "Letzte Gespräche"), ("notizen", "Notizen")):
        dateien = sorted((GEHIRN / ordner).glob("*.md"), reverse=True)
        if dateien:
            zeilen.append(f"\n## {titel} (neueste zuerst)")
            for d in dateien[:10]:
                kopf = d.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
                zeilen.append(f"- {kopf}  ({_rel(d)})")
            if len(dateien) > 10:
                zeilen.append(f"- … und {len(dateien) - 10} ältere")
    weitere = [p for b in WEITERE_QUELLEN if b.exists() for p in sorted(b.rglob("*.md"))]
    if weitere:
        zeilen.append("\n## Wissen (bei Bedarf lesen oder durchsuchen)")
        for d in weitere:
            kopf = d.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
            zeilen.append(f"- {kopf}  ({_rel(d)})")
    return "\n".join(zeilen)


def suche(woerter: list[str], max_treffer: int = 25) -> str:
    begriffe = [w.lower() for w in woerter if len(w) >= 2]
    if not begriffe:
        return "Bitte Suchwörter angeben."
    treffer: list[tuple[int, str, int, str]] = []
    for datei in _dateien():
        zeilen = datei.read_text(encoding="utf-8").splitlines()
        abschnitt = ""
        for nr, zeile in enumerate(zeilen, 1):
            if zeile.startswith("#"):
                abschnitt = zeile.lstrip("# ").strip()
            klein = (zeile + " " + abschnitt).lower()
            punkte = sum(klein.count(b) for b in begriffe)
            if punkte and zeile.strip():
                # alle Begriffe in einer Zeile zählen doppelt
                if all(b in klein for b in begriffe):
                    punkte += 5
                treffer.append((punkte, _rel(datei), nr, zeile.strip()))
    if not treffer:
        return f"Nichts gefunden zu: {' '.join(woerter)}"
    treffer.sort(key=lambda t: (-t[0], t[1], t[2]))
    aus = [f"{t[1]}:{t[2]}  {t[3]}" for t in treffer[:max_treffer]]
    if len(treffer) > max_treffer:
        aus.append(f"… {len(treffer) - max_treffer} weitere Treffer")
    return "\n".join(aus)


# ---------- Schreiben ----------

def merken(thema: str, fakt: str, quelle: str, ersetzt: str | None = None) -> str:
    thema = thema.lower().removesuffix(".md")
    if thema not in THEMEN:
        sys.exit(f"Unbekanntes Thema '{thema}'. Erlaubt: {', '.join(THEMEN)}")
    fakt = " ".join(fakt.split())
    _geheim_pruefen(fakt + " " + quelle)
    datei = GEHIRN / "fakten" / f"{thema}.md"
    datei.parent.mkdir(parents=True, exist_ok=True)
    if not datei.exists():
        datei.write_text(f"# {THEMEN[thema]}\n\n", encoding="utf-8")
    zeilen = datei.read_text(encoding="utf-8").splitlines()

    if any(f"· {fakt} ·" in z for z in zeilen):
        return f"Schon im Gehirn: {fakt}"

    neu = f"- {date.today().isoformat()} · {fakt} · Quelle: {quelle}"
    if ersetzt:
        passend = [i for i, z in enumerate(zeilen) if z.startswith("- ") and ersetzt.lower() in z.lower()]
        if len(passend) != 1:
            sys.exit(f"--ersetzt '{ersetzt}' passt auf {len(passend)} Zeilen, es muss genau eine sein.")
        zeilen[passend[0]] = neu + " (aktualisiert)"
    else:
        while zeilen and not zeilen[-1].strip():
            zeilen.pop()
        zeilen.append(neu)
    datei.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return f"Für Jarvis gemerkt ({_rel(datei)}): {fakt}"


def _text_ablegen(ordner: str, titel: str, text: str, quelle: str) -> str:
    text = text.strip()
    if not text:
        sys.exit("Kein Text bekommen (per Eingabe umleiten oder --text benutzen).")
    _geheim_pruefen(text)
    heute = date.today().isoformat()
    ziel = GEHIRN / ordner / f"{heute}_{_name(titel)}.md"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    if ziel.exists():  # gleicher Titel am selben Tag: ergänzen statt überschreiben
        with ziel.open("a", encoding="utf-8") as f:
            f.write(f"\n\n## Nachtrag\n\n{text}\n")
        return f"Ergänzt: {_rel(ziel)}"
    ziel.write_text(f"# {titel}\n\nDatum: {heute}  \nQuelle: {quelle}\n\n{text}\n", encoding="utf-8")
    return f"Abgelegt: {_rel(ziel)}"


def main() -> None:
    p = argparse.ArgumentParser(description="Jarvis' zweites Gehirn")
    sub = p.add_subparsers(dest="befehl", required=True)
    sub.add_parser("uebersicht", help="Alle Fakten und die neuesten Einträge zeigen")
    s = sub.add_parser("suche", help="Volltextsuche im Gehirn")
    s.add_argument("woerter", nargs="+")
    m = sub.add_parser("merken", help="Einen gesicherten Fakt speichern")
    m.add_argument("thema", help=", ".join(THEMEN))
    m.add_argument("fakt")
    m.add_argument("--quelle", default="Gespräch mit Claude")
    m.add_argument("--ersetzt", help="Teil der alten Zeile, die durch den neuen Fakt ersetzt wird")
    for name, hilfe in (("notiz", "Längere Notiz ablegen"), ("gespraech", "Zusammenfassung eines Gesprächs ablegen")):
        n = sub.add_parser(name, help=hilfe)
        n.add_argument("titel")
        n.add_argument("--text", help="Text direkt angeben statt per Eingabe")
        n.add_argument("--quelle", default="Claude auf dem iPad")
    a = p.parse_args()

    if a.befehl == "uebersicht":
        print(uebersicht())
    elif a.befehl == "suche":
        print(suche(a.woerter))
    elif a.befehl == "merken":
        print(merken(a.thema, a.fakt, a.quelle, a.ersetzt))
    else:
        text = a.text if a.text is not None else sys.stdin.read()
        ordner = "notizen" if a.befehl == "notiz" else "gespraeche"
        print(_text_ablegen(ordner, a.titel, text, a.quelle))


if __name__ == "__main__":
    main()
