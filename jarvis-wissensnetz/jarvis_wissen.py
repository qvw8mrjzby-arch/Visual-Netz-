"""Verbindung zwischen Jarvis und dem Graphify-Wissensnetz.

Jarvis importiert dieses Modul und bekommt damit immer den aktuellen Stand
des Netzes. Sobald der Hintergrund-Dienst (wissensnetz_dienst.py) das Netz
neu gebaut hat, lädt WissensNetz es beim nächsten Aufruf automatisch neu.

    from jarvis_wissen import WissensNetz
    netz = WissensNetz()
    print(netz.frage("Was steht in meinen Notizen über das Auto?"))

Wenn das Paket graphify installiert ist, wird dessen eigene Suche benutzt
(dieselbe wie bei `graphify query`). Fehlt es, greift eine einfache Suche in
reinem Python, damit Jarvis nie abstürzt.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from collections import deque
from pathlib import Path
from typing import Callable

HIER = Path(__file__).resolve().parent


def lade_config() -> dict:
    datei = HIER / "config.json"
    cfg = json.loads(datei.read_text(encoding="utf-8-sig")) if datei.exists() else {}
    cfg.setdefault("ordner", str(Path.home() / "JarvisWissen"))
    cfg["ordner"] = os.path.expandvars(os.path.expanduser(cfg["ordner"]))
    return cfg


def graph_pfad(cfg: dict | None = None) -> Path:
    cfg = cfg or lade_config()
    return Path(cfg["ordner"]) / "graphify-out" / "graph.json"


class WissensNetz:
    """Liest graph.json und beantwortet Fragen daraus. Lädt neu, wenn sich die Datei ändert."""

    def __init__(self, pfad: str | Path | None = None):
        self.pfad = Path(pfad) if pfad else graph_pfad()
        self._stand: float | None = None
        self._daten: dict | None = None
        self._nx_graph = None
        self._lock = threading.Lock()

    # ---------- Laden ----------

    def bereit(self) -> bool:
        return self.pfad.exists()

    def _neu_laden_falls_noetig(self) -> bool:
        if not self.pfad.exists():
            return False
        stand = self.pfad.stat().st_mtime
        if stand == self._stand and self._daten is not None:
            return True
        with self._lock:
            try:
                daten = json.loads(self.pfad.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                # Datei wird gerade geschrieben: alten Stand behalten
                return self._daten is not None
            self._daten = daten
            self._stand = stand
            self._nx_graph = None
        return True

    def _graphify_graph(self):
        """Graph über graphify laden (beste Suche). None, wenn graphify fehlt."""
        if self._nx_graph is not None:
            return self._nx_graph
        try:
            from graphify.serve import _read_graph  # gleiche Funktion wie die CLI
        except Exception:
            return None
        try:
            self._nx_graph = _read_graph(str(self.pfad))
        except Exception:
            return None
        return self._nx_graph

    # ---------- Fragen ----------

    def frage(self, text: str, tief: bool = False, budget: int = 2000) -> str:
        """Antwort-Kontext aus dem Netz für eine Frage.

        tief=False: breite Suche (womit ist X verbunden?)
        tief=True:  einer Kette folgen (wie kommt X zu Y?)
        budget:     ungefähre Obergrenze in Tokens
        """
        if not self._neu_laden_falls_noetig():
            return "Das Wissensnetz ist noch nicht gebaut. Starte den Wissensnetz-Dienst."

        G = self._graphify_graph()
        if G is not None:
            try:
                from graphify.serve import _query_graph_text

                return _query_graph_text(
                    G, text, mode="dfs" if tief else "bfs",
                    token_budget=budget, graph_path=str(self.pfad),
                )
            except Exception:
                pass  # auf einfache Suche ausweichen
        return self._einfache_suche(text, tief=tief, budget=budget)

    def kontext_fuer_prompt(self, text: str, budget: int = 1500) -> str:
        """Fertiger Textblock, den Jarvis vor seinen Prompt an die KI hängen kann."""
        antwort = self.frage(text, budget=budget)
        return (
            "Wissen aus meinem persönlichen Wissensnetz (nur das verwenden, "
            "was hier steht, und Quellen nennen):\n" + antwort
        )

    def zentrale_themen(self, anzahl: int = 10) -> list[tuple[str, int]]:
        """Die am stärksten vernetzten Knoten (God Nodes)."""
        if not self._neu_laden_falls_noetig():
            return []
        grad: dict[str, int] = {}
        for k in self._kanten():
            grad[k["source"]] = grad.get(k["source"], 0) + 1
            grad[k["target"]] = grad.get(k["target"], 0) + 1
        namen = {n["id"]: n.get("label", n["id"]) for n in self._daten.get("nodes", [])}
        top = sorted(grad.items(), key=lambda x: x[1], reverse=True)[:anzahl]
        return [(namen.get(i, i), g) for i, g in top]

    def statistik(self) -> dict:
        if not self._neu_laden_falls_noetig():
            return {"bereit": False}
        return {
            "bereit": True,
            "knoten": len(self._daten.get("nodes", [])),
            "kanten": len(self._kanten()),
            "stand": time.strftime("%d.%m.%Y %H:%M", time.localtime(self._stand)),
        }

    # ---------- Benachrichtigung ----------

    def beobachten(self, rueckruf: Callable[["WissensNetz"], None], intervall: float = 5.0) -> threading.Thread:
        """Ruft rueckruf(netz) auf, sobald das Netz neu gebaut wurde. Läuft im Hintergrund."""

        def schleife():
            letzter = self.pfad.stat().st_mtime if self.pfad.exists() else None
            while True:
                time.sleep(intervall)
                if not self.pfad.exists():
                    continue
                jetzt = self.pfad.stat().st_mtime
                if jetzt != letzter:
                    letzter = jetzt
                    time.sleep(1)  # Schreiben abwarten
                    if self._neu_laden_falls_noetig():
                        try:
                            rueckruf(self)
                        except Exception as fehler:  # Jarvis soll weiterlaufen
                            print(f"[Wissensnetz] Fehler im Rückruf: {fehler}")

        t = threading.Thread(target=schleife, name="wissensnetz-beobachter", daemon=True)
        t.start()
        return t

    # ---------- Einfache Suche ohne graphify ----------

    def _kanten(self) -> list[dict]:
        d = self._daten or {}
        return d.get("links") or d.get("edges") or []

    def _einfache_suche(self, text: str, tief: bool, budget: int) -> str:
        knoten = {n["id"]: n for n in self._daten.get("nodes", [])}
        nachbarn: dict[str, list[tuple[str, dict]]] = {i: [] for i in knoten}
        for k in self._kanten():
            s, t = k.get("source"), k.get("target")
            if s in nachbarn and t in nachbarn:
                nachbarn[s].append((t, k))
                nachbarn[t].append((s, k))

        woerter = [w.lower() for w in re.findall(r"\w+", text) if len(w) >= 3]
        punkte = []
        for i, n in knoten.items():
            name = (n.get("label") or i).lower()
            p = sum(1 for w in woerter if w in name)
            if p:
                punkte.append((p, i))
        punkte.sort(reverse=True)
        start = [i for _, i in punkte[:3]]
        if not start:
            return f"Im Wissensnetz passt nichts zu: {', '.join(woerter) or text}"

        besucht: list[str] = []
        gesehen = set()
        if tief:
            stapel = [(s, 0) for s in reversed(start)]
            while stapel:
                n, tiefe = stapel.pop()
                if n in gesehen or tiefe > 6:
                    continue
                gesehen.add(n)
                besucht.append(n)
                stapel.extend((m, tiefe + 1) for m, _ in nachbarn[n] if m not in gesehen)
        else:
            schlange = deque((s, 0) for s in start)
            while schlange:
                n, tiefe = schlange.popleft()
                if n in gesehen or tiefe > 2:
                    continue
                gesehen.add(n)
                besucht.append(n)
                schlange.extend((m, tiefe + 1) for m, _ in nachbarn[n])

        zeilen = []
        zeichen_max = budget * 4  # grob 4 Zeichen pro Token
        for n in besucht:
            d = knoten[n]
            quelle = d.get("source_file", "")
            ort = d.get("source_location", "")
            fundstelle = f"  [{quelle} {ort}]".replace(" ]", "]") if quelle else ""
            zeilen.append(f"- {d.get('label', n)}{fundstelle}")
            for m, k in nachbarn[n]:
                if m in gesehen:
                    rel = k.get("relation", "verbunden mit")
                    conf = k.get("confidence", "")
                    zeilen.append(f"    {rel} -> {knoten[m].get('label', m)} {('(' + conf + ')') if conf else ''}".rstrip())
            if sum(len(z) for z in zeilen) > zeichen_max:
                zeilen.append("… (gekürzt)")
                break
        return "\n".join(zeilen)


if __name__ == "__main__":
    import sys

    netz = WissensNetz()
    if len(sys.argv) > 1:
        print(netz.frage(" ".join(sys.argv[1:])))
    else:
        print(netz.statistik())
        for name, grad in netz.zentrale_themen():
            print(f"{grad:4d}  {name}")
