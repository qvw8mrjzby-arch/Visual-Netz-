"""Hintergrund-Dienst: hält das Wissensnetz für Jarvis aktuell.

Schaut alle paar Sekunden in deinen Wissens-Ordner. Hat sich etwas geändert
(neue, geänderte oder gelöschte Datei), wartet er kurz, bis du fertig bist,
und baut das Netz mit `graphify extract` neu. Graphify liest dabei nur die
Dateien neu, die sich wirklich geändert haben.

Start:  pythonw wissensnetz_dienst.py      (ohne Fenster, macht der Autostart)
        python  wissensnetz_dienst.py      (mit Fenster, zum Zuschauen)
        python  wissensnetz_dienst.py --einmal   (einmal bauen und beenden)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from jarvis_wissen import lade_config

HIER = Path(__file__).resolve().parent
LOG = HIER / "wissensnetz.log"
STATUS = HIER / "status.json"
IGNORIEREN = {"graphify-out", ".git", "__pycache__"}


def log(text: str) -> None:
    zeile = f"{datetime.now():%d.%m.%Y %H:%M:%S}  {text}"
    print(zeile, flush=True)
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(zeile + "\n")
        if LOG.stat().st_size > 2_000_000:  # Log klein halten
            LOG.write_text(zeile + "\n", encoding="utf-8")
    except OSError:
        pass


def status(**werte) -> None:
    werte["zeit"] = datetime.now().isoformat(timespec="seconds")
    try:
        STATUS.write_text(json.dumps(werte, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def momentaufnahme(ordner: Path) -> dict[str, tuple[float, int]]:
    """Name -> (Änderungszeit, Größe) für alle Dateien im Ordner."""
    stand: dict[str, tuple[float, int]] = {}
    for wurzel, ordnernamen, dateien in os.walk(ordner):
        ordnernamen[:] = [o for o in ordnernamen if o not in IGNORIEREN and not o.startswith(".")]
        for d in dateien:
            if d.startswith(("~$", ".")):  # Office-Sperrdateien, versteckte Dateien
                continue
            p = Path(wurzel) / d
            try:
                s = p.stat()
            except OSError:
                continue
            stand[str(p)] = (s.st_mtime, s.st_size)
    return stand


def graphify_befehl() -> list[str]:
    exe = shutil.which("graphify")
    if exe:
        return [exe]
    # Fallback: über das gleiche Python starten
    python = sys.executable.replace("pythonw.exe", "python.exe")
    return [python, "-m", "graphify"]


def netz_bauen(ordner: Path, backend: str) -> bool:
    befehl = graphify_befehl() + ["extract", str(ordner), "--backend", backend]
    log("Baue Wissensnetz: " + " ".join(befehl))
    status(zustand="baut", ordner=str(ordner))
    start = time.time()
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        ergebnis = subprocess.run(
            befehl, cwd=str(ordner), capture_output=True, text=True,
            encoding="utf-8", errors="replace", creationflags=flags,
        )
    except FileNotFoundError:
        log("FEHLER: graphify ist nicht installiert. Führe installieren.bat aus.")
        status(zustand="fehler", meldung="graphify nicht installiert")
        return False

    for zeile in (ergebnis.stdout + ergebnis.stderr).strip().splitlines()[-15:]:
        log("  " + zeile)
    dauer = round(time.time() - start)
    if ergebnis.returncode == 0:
        log(f"Fertig in {dauer} s.")
        status(zustand="bereit", ordner=str(ordner), dauer_sekunden=dauer)
        return True
    log(f"FEHLER (Code {ergebnis.returncode}). Häufigste Ursache: API-Key fehlt oder Ollama läuft nicht.")
    status(zustand="fehler", meldung=f"graphify Code {ergebnis.returncode}, siehe wissensnetz.log")
    return False


def main() -> None:
    cfg = lade_config()
    ordner = Path(cfg["ordner"])
    ordner.mkdir(parents=True, exist_ok=True)
    backend = cfg.get("backend", "claude")
    intervall = float(cfg.get("pruef_intervall_sekunden", 10))
    ruhe = float(cfg.get("warten_nach_aenderung_sekunden", 20))

    log(f"Wissensnetz-Dienst gestartet. Ordner: {ordner} · KI: {backend}")
    letzter = momentaufnahme(ordner)
    if letzter:
        # Beim Start immer einmal abgleichen: erfasst auch Änderungen, die
        # passiert sind, während der PC aus war. Unveränderte Dateien kosten nichts.
        netz_bauen(ordner, backend)
        letzter = momentaufnahme(ordner)
    else:
        status(zustand="wartet", meldung="Ordner ist noch leer")

    if "--einmal" in sys.argv:
        return

    geaendert_seit: float | None = None
    while True:
        time.sleep(intervall)
        jetzt = momentaufnahme(ordner)
        if jetzt != letzter:
            letzter = jetzt
            geaendert_seit = time.time()  # Uhr neu starten, solange du noch kopierst
            continue
        if geaendert_seit and time.time() - geaendert_seit >= ruhe:
            geaendert_seit = None
            netz_bauen(ordner, backend)
            letzter = momentaufnahme(ordner)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Dienst beendet.")
