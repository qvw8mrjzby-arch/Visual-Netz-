"""Baut das Gehirn-Dashboard (3D-Netz + Agenten-Gebäude) aus dem Repo.

    python3 dashboard.py        ->  dashboard/gehirn-dashboard.html

Liest gehirn/ und jarvis-wissensnetz/wissen/, macht daraus ein Netz aus
Bereichen, Dateien, Einträgen und Begriffen, und holt die Arbeit der Agenten
aus der Git-Historie. Die Daten werden in dashboard/vorlage.html eingesetzt.
Nur Python-Standardbibliothek.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import gehirn

WURZEL = Path(__file__).resolve().parent
VORLAGE = WURZEL / "dashboard" / "vorlage.html"
AUSGABE = WURZEL / "dashboard" / "gehirn-dashboard.html"
WISSEN = WURZEL / "jarvis-wissensnetz" / "wissen"

BEREICHE = {
    "fakten": ("Fakten", gehirn.GEHIRN / "fakten"),
    "notizen": ("Notizen", gehirn.GEHIRN / "notizen"),
    "gespraeche": ("Gespräche", gehirn.GEHIRN / "gespraeche"),
    "wissen": ("Wissen", WISSEN),
}

STOPP = set("""
aber alle allem allen aller alles also auch auf aus bei beim bin bis bleibt dann das dass dein deine dem den
denn der des die dies diese diesem diesen dieser doch dort durch ein eine einem einen einer eines erst etwa
für gegen geht gibt hat hier ihr ihre immer ist jede jeder jedes kann kein keine man mehr mit nach nicht nichts
noch nur oder ohne pro schon sehr sein seine sich sie sind so über um und uns unter viel vom von vor war was
weil wenn werden wie wird wir wo zu zum zur zwei drei quelle gespräch ipad datum claude sekunden ab statt
mal neu neue neuen erste ersten wer was beide man einfach immer direkt wenig ende leute teilen inhalt
gut besser macht machen""".split())


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=WURZEL, capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _abschnitte(text: str) -> list[tuple[str, str]]:
    """Markdown in (Überschrift, Inhalt) für jede ##-Ebene zerlegen."""
    teile, titel, puffer = [], None, []
    for z in text.splitlines():
        if z.startswith("## "):
            if titel is not None:
                teile.append((titel, "\n".join(puffer).strip()))
            titel, puffer = z[3:].strip(), []
        elif titel is not None:
            puffer.append(z)
    if titel is not None:
        teile.append((titel, "\n".join(puffer).strip()))
    return teile


def _kurz(text: str, n: int = 70) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def netz_bauen() -> dict:
    knoten, kanten = [], []

    def neu(id_, label, art, **mehr):
        knoten.append({"id": id_, "label": label, "art": art, **mehr})
        return id_

    neu("gehirn", "Jarvis-Gehirn", "kern")
    eintraege: list[tuple[str, str, str]] = []  # (id, text, datei)

    for schluessel, (name, ordner) in BEREICHE.items():
        neu(schluessel, name, "bereich", bereich=schluessel)
        kanten.append(["gehirn", schluessel])
        if not ordner.exists():
            continue
        for datei in sorted(ordner.rglob("*.md")):
            rel = str(datei.relative_to(WURZEL))
            text = datei.read_text(encoding="utf-8")
            kopf = (text.splitlines() or [datei.stem])[0].lstrip("# ").strip() or datei.stem
            did = neu(rel, kopf, "datei", bereich=schluessel, quelle=rel)
            kanten.append([schluessel, did])
            if schluessel == "fakten":
                for nr, z in enumerate(text.splitlines(), 1):
                    if not z.startswith("- "):
                        continue
                    teile = [t.strip() for t in z[2:].split("·")]
                    fakt = teile[1] if len(teile) > 1 else z[2:]
                    eid = neu(f"{rel}:{nr}", _kurz(fakt, 60), "eintrag", bereich=schluessel,
                              quelle=f"{rel}:{nr}", text=z[2:], datum=teile[0] if teile else "")
                    kanten.append([did, eid])
                    eintraege.append((eid, fakt, rel))
            else:
                abschnitte = _abschnitte(text)
                if not abschnitte:  # Datei ohne Unterkapitel: ganze Datei ist ein Eintrag
                    eintraege.append((did, text, rel))
                    knoten[-1]["text"] = text[:1500]
                for titel, inhalt in abschnitte:
                    eid = neu(f"{rel}#{titel}", _kurz(titel, 50), "eintrag", bereich=schluessel,
                              quelle=rel, text=inhalt[:1500])
                    kanten.append([did, eid])
                    eintraege.append((eid, titel + " " + inhalt, rel))

    # Begriffe, die in mehreren Dateien vorkommen, verbinden die Einträge quer
    vorkommen: dict[str, set[str]] = defaultdict(set)
    dateien_pro_wort: dict[str, set[str]] = defaultdict(set)
    schreibweise: dict[str, Counter] = defaultdict(Counter)
    for eid, text, datei in eintraege:
        for wort in re.findall(r"[A-Za-zÄÖÜäöüß][\wÄÖÜäöüß\-]{3,}", text):
            klein = wort.lower().strip("-")
            if klein in STOPP or klein.isdigit():
                continue
            vorkommen[klein].add(eid)
            dateien_pro_wort[klein].add(datei)
            schreibweise[klein][wort] += 1
    for w in [w for w in vorkommen if w.endswith("s") and w[:-1] in vorkommen]:  # Hooks -> Hook
        vorkommen[w[:-1]] |= vorkommen.pop(w)
        dateien_pro_wort[w[:-1]] |= dateien_pro_wort.pop(w)
    grenze = max(4, int(len(eintraege) * 0.5))
    kandidaten = [
        w for w, e in vorkommen.items()
        if len(dateien_pro_wort[w]) >= 2 and 2 <= len(e) <= grenze and schreibweise[w].most_common(1)[0][0][0].isupper()
    ]
    in_fakten = {w for w, e in vorkommen.items() if any(":" in i and "/fakten/" in i for i in e)}
    kandidaten.sort(key=lambda w: (w not in in_fakten, -len(dateien_pro_wort[w]), -len(vorkommen[w]), w))
    for w in kandidaten[:28]:
        bid = neu(f"begriff:{w}", schreibweise[w].most_common(1)[0][0], "begriff")
        for eid in sorted(vorkommen[w]):
            kanten.append([bid, eid])

    return {"knoten": knoten, "kanten": kanten}


# ---------- Agenten aus der Git-Historie ----------

AGENTEN = [
    {"id": "merker", "name": "Merker", "rolle": "trägt gesicherte Fakten ein", "pfad": "gehirn/fakten/"},
    {"id": "archivar", "name": "Archivar", "rolle": "fasst Gespräche zusammen", "pfad": "gehirn/gespraeche/"},
    {"id": "schreiber", "name": "Schreiber", "rolle": "legt Notizen und Konzepte ab", "pfad": "gehirn/notizen/"},
    {"id": "bibliothekar", "name": "Bibliothekar", "rolle": "pflegt das Startwissen", "pfad": "jarvis-wissensnetz/wissen/"},
    {"id": "sync", "name": "PC-Sync", "rolle": "gleicht mit Jarvis auf dem PC ab", "pfad": None},
]


def arbeit_lesen() -> list[dict]:
    roh = _git("log", "--date=iso-strict", "--pretty=format:@@%H|%ad|%s", "--name-only", "-n", "300",
               "--", "gehirn", "jarvis-wissensnetz/wissen")
    jobs = []
    for block in roh.split("@@")[1:]:
        zeilen = [z for z in block.splitlines() if z.strip()]
        zeilen = [z for z in zeilen if not z.endswith(".gitkeep")]
        kopf, dateien = zeilen[0], zeilen[1:]
        hash_, zeit, betreff = kopf.split("|", 2)
        if "Abgleich vom PC" in betreff:
            jobs.append({"agent": "sync", "zeit": zeit, "was": betreff, "dateien": dateien})
            continue
        for a in AGENTEN:
            if a["pfad"] and any(d.startswith(a["pfad"]) for d in dateien):
                passend = [d for d in dateien if d.startswith(a["pfad"])]
                jobs.append({"agent": a["id"], "zeit": zeit, "was": betreff.splitlines()[0], "dateien": passend})
    return jobs


def main() -> None:
    netz = netz_bauen()
    uebersicht = gehirn.uebersicht()
    daten = {
        "erstellt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "netz": netz,
        "agenten": AGENTEN,
        "arbeit": arbeit_lesen(),
        "zahlen": {
            "fakten": sum(1 for k in netz["knoten"] if k["art"] == "eintrag" and k.get("bereich") == "fakten"),
            "notizen": len(list((gehirn.GEHIRN / "notizen").glob("*.md"))),
            "gespraeche": len(list((gehirn.GEHIRN / "gespraeche").glob("*.md"))),
            "wissen": len(list(WISSEN.rglob("*.md"))) if WISSEN.exists() else 0,
            "verbindungen": len(netz["kanten"]),
            "start_tokens": round(len(uebersicht) / 4),
        },
    }
    json_text = json.dumps(daten, ensure_ascii=False).replace("</", "<\\/")
    html = VORLAGE.read_text(encoding="utf-8").replace("/*__DATEN__*/null", json_text)
    AUSGABE.write_text(html, encoding="utf-8")
    z = daten["zahlen"]
    print(f"{AUSGABE.relative_to(WURZEL)}: {len(netz['knoten'])} Knoten, {z['verbindungen']} Verbindungen, "
          f"{len(daten['arbeit'])} Arbeiten")


if __name__ == "__main__":
    main()
