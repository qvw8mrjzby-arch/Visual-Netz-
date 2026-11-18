"""Gleicht Jarvis' Gehirn zwischen PC und iPad ab (über das GitHub-Repo).

Auf dem iPad schreibt Claude Fakten, Notizen und Gesprächs-Zusammenfassungen in
den Ordner `gehirn/` des Repos. Auf dem PC schreibt der Skill `jarvis-merken`
in den Ordner JarvisWissen. Dieses Skript bringt beide Seiten zusammen:

    Repo gehirn/fakten      <->  JarvisWissen/fakten
    Repo gehirn/notizen     <->  JarvisWissen/notizen
    Repo gehirn/gespraeche  <->  JarvisWissen/gespraeche_ipad
    Repo gehirn/jarvis       <-   Jarvis' eigenes Gehirn (config "jarvis_gehirn"), nur Lesekopie

Ablauf: git pull -> Dateien in beide Richtungen abgleichen -> commit -> push.
Haben sich beide Seiten derselben Datei geändert, werden die Zeilen
zusammengeführt (nichts geht verloren). Gelöschte Dateien werden bewusst nicht
gelöscht, sondern beim nächsten Mal von der anderen Seite zurückgeholt; so kann
ein Fehler auf einer Seite das Gehirn nicht leeren. Zum Löschen eine Datei auf
beiden Seiten entfernen.

Der Wissensnetz-Dienst ruft das automatisch auf, wenn in config.json
"gehirn_repo" gesetzt ist. Von Hand:  python gehirn_sync.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from jarvis_wissen import lade_config

HIER = Path(__file__).resolve().parent
ZUSTAND = HIER / "gehirn_sync_zustand.json"
ZUORDNUNG = {
    "fakten": "fakten",
    "notizen": "notizen",
    "gespraeche": "gespraeche_ipad",
}


def _hash(p: Path) -> str | None:
    try:
        return hashlib.sha1(p.read_bytes()).hexdigest()
    except OSError:
        return None


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    return subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True,
        encoding="utf-8", errors="replace", creationflags=flags,
    )


def _zusammenfuehren(a: str, b: str) -> str:
    """Zeilen aus a behalten, Zeilen aus b anhängen, die in a fehlen."""
    zeilen = a.rstrip("\n").splitlines()
    vorhanden = set(zeilen)
    for z in b.splitlines():
        if z.strip() and z not in vorhanden:
            zeilen.append(z)
            vorhanden.add(z)
    return "\n".join(zeilen) + "\n"


def _abgleichen(repo_ordner: Path, pc_ordner: Path, zustand: dict, schluessel: str) -> list[str]:
    """Gleicht zwei Ordner ab. Gibt eine Liste der Änderungen zurück."""
    aenderungen = []
    repo_ordner.mkdir(parents=True, exist_ok=True)
    pc_ordner.mkdir(parents=True, exist_ok=True)
    namen = {p.name for p in repo_ordner.glob("*.md")} | {p.name for p in pc_ordner.glob("*.md")}
    for name in sorted(namen):
        r, l = repo_ordner / name, pc_ordner / name
        hr, hl = _hash(r), _hash(l)
        alt = zustand.get(f"{schluessel}/{name}")
        if hr == hl:
            pass
        elif hl is None or (hr is not None and hl == alt):
            shutil.copy2(r, l)  # nur das Repo (iPad) hat sich geändert
            aenderungen.append(f"iPad -> PC: {schluessel}/{name}")
        elif hr is None or hr == alt:
            shutil.copy2(l, r)  # nur der PC hat sich geändert
            aenderungen.append(f"PC -> iPad: {schluessel}/{name}")
        else:  # beide geändert
            text = _zusammenfuehren(r.read_text(encoding="utf-8"), l.read_text(encoding="utf-8"))
            r.write_text(text, encoding="utf-8")
            l.write_text(text, encoding="utf-8")
            aenderungen.append(f"zusammengeführt: {schluessel}/{name}")
        if r.exists():
            zustand[f"{schluessel}/{name}"] = _hash(r)
    return aenderungen


GEHEIM = re.compile(
    r"(sk-ant-|sk-[A-Za-z0-9]{20}|ghp_|github_pat_|AIza[0-9A-Za-z_-]{20}|xox[bp]-|\d{8,10}:[A-Za-z0-9_-]{30,}|"
    r"passwort\s*[:=]|password\s*[:=]|api[_-]?key\s*[:=]|token\s*[:=])",
    re.IGNORECASE,
)


def repo_ist_privat(repo: Path) -> bool:
    """True nur, wenn GitHub das Repo ohne Anmeldung NICHT zeigt (also privat ist)."""
    import urllib.error
    import urllib.request

    url = _git(repo, "remote", "get-url", "origin").stdout.strip()
    treffer = re.search(r"github\.com[:/]([^/]+)/(.+?)(?:\.git)?$", url)
    if not treffer:
        return False
    api = f"https://api.github.com/repos/{treffer.group(1)}/{treffer.group(2)}"
    try:
        urllib.request.urlopen(urllib.request.Request(api, headers={"User-Agent": "jarvis-gehirn-sync"}), timeout=10)
        return False  # öffentlich sichtbar
    except urllib.error.HTTPError as fehler:
        return fehler.code == 404
    except Exception:
        return False  # offline: lieber nichts spiegeln


def jarvis_spiegeln(quelle: Path, ziel: Path, log=print) -> list[str]:
    """Jarvis' eigenes Gehirn (PC) ins Repo spiegeln, nur in diese Richtung.

    Jarvis bleibt Herr über seine Notizen; das iPad bekommt eine Lesekopie in
    gehirn/jarvis/. Dateien, die nach Passwort, Key oder Token aussehen,
    werden übersprungen. Auf dem PC gelöschte Notizen verschwinden auch hier.
    """
    if not quelle.exists():
        return []
    aenderungen, gesehen = [], set()
    for datei in sorted(quelle.rglob("*.md")):
        rel = datei.relative_to(quelle)
        if any(t.startswith(".") for t in rel.parts):
            continue
        try:
            text = datei.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if GEHEIM.search(text):
            log(f"Gehirn-Sync: übersprungen (sieht nach Geheimnis aus): {rel}")
            continue
        gesehen.add(rel)
        z = ziel / rel
        if not z.exists() or z.read_text(encoding="utf-8", errors="replace") != text:
            z.parent.mkdir(parents=True, exist_ok=True)
            z.write_text(text, encoding="utf-8")
            aenderungen.append(f"Jarvis -> iPad: jarvis/{rel.as_posix()}")
    if ziel.exists():
        for alt in ziel.rglob("*.md"):
            if alt.relative_to(ziel) not in gesehen:
                alt.unlink()
                aenderungen.append(f"entfernt (auf dem PC gelöscht): jarvis/{alt.relative_to(ziel).as_posix()}")
    return aenderungen


def synchronisieren(log=print) -> int:
    cfg = lade_config()
    repo_text = (cfg.get("gehirn_repo") or "").strip()
    if not repo_text:
        return 0
    repo = Path(os.path.expandvars(os.path.expanduser(repo_text)))
    if not (repo / ".git").exists():
        log(f"Gehirn-Sync: {repo} ist kein Git-Repo. 'gehirn_repo' in config.json prüfen.")
        return 0
    wissen = Path(cfg["ordner"])

    ergebnis = _git(repo, "pull", "--no-rebase", "--no-edit", "--quiet")
    if ergebnis.returncode != 0:
        # offline oder Konflikt: trotzdem lokal abgleichen, push später
        log("Gehirn-Sync: git pull fehlgeschlagen: " + (ergebnis.stderr.strip().splitlines() or ["?"])[-1])

    try:
        zustand = json.loads(ZUSTAND.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        zustand = {}

    aenderungen: list[str] = []
    for repo_name, pc_name in ZUORDNUNG.items():
        aenderungen += _abgleichen(repo / "gehirn" / repo_name, wissen / pc_name, zustand, repo_name)
    jarvis_text = (cfg.get("jarvis_gehirn") or "").strip()
    if jarvis_text and not repo_ist_privat(repo):
        log("Gehirn-Sync: Jarvis' Gehirn wird NICHT gespiegelt, weil das GitHub-Repo öffentlich ist (oder offline). Repo auf privat stellen.")
    elif jarvis_text:
        quelle = Path(os.path.expandvars(os.path.expanduser(jarvis_text)))
        aenderungen += jarvis_spiegeln(quelle, repo / "gehirn" / "jarvis", log)
    ZUSTAND.write_text(json.dumps(zustand, indent=1, ensure_ascii=False), encoding="utf-8")

    for a in aenderungen:
        log("Gehirn-Sync: " + a)

    _git(repo, "add", "gehirn")
    if _git(repo, "diff", "--cached", "--quiet").returncode != 0:
        _git(repo, "commit", "-m", "Gehirn: Abgleich vom PC (Jarvis)", "--quiet")
    status = _git(repo, "status", "-sb").stdout
    if "ahead" in status:
        push = _git(repo, "push", "--quiet")
        if push.returncode != 0:
            log("Gehirn-Sync: git push fehlgeschlagen (offline?), nächster Versuch beim nächsten Abgleich.")
    return len(aenderungen)


if __name__ == "__main__":
    print(f"{synchronisieren()} Gehirn-Dateien abgeglichen.")
