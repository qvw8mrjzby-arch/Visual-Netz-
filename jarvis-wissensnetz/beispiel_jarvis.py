"""Beispiel: so baust du das Wissensnetz in deinen Jarvis ein.

Kopiere die markierten Zeilen in deinen Jarvis-Code. `frage_an_ki` steht für
die Stelle, an der dein Jarvis heute schon seine KI aufruft.
"""

import sys
from pathlib import Path

# --- 1. Modul finden (Pfad zum Ordner jarvis-wissensnetz anpassen) ----------
sys.path.insert(0, str(Path(__file__).resolve().parent))
from jarvis_wissen import WissensNetz  # noqa: E402

netz = WissensNetz()


# --- 2. Jarvis informieren, wenn neues Wissen da ist ------------------------
def neues_wissen(n: WissensNetz) -> None:
    s = n.statistik()
    print(f"[Jarvis] Wissensnetz aktualisiert: {s['knoten']} Knoten, {s['kanten']} Verbindungen.")


netz.beobachten(neues_wissen)


# --- 3. Vor jeder Antwort das passende Wissen mitgeben ----------------------
def frage_an_ki(prompt: str) -> str:
    """Platzhalter für deinen bisherigen KI-Aufruf."""
    return f"(Hier antwortet deine KI auf:)\n{prompt}"


def jarvis_antwortet(nutzer_text: str) -> str:
    wissen = netz.kontext_fuer_prompt(nutzer_text)
    return frage_an_ki(f"{wissen}\n\nFrage: {nutzer_text}")


if __name__ == "__main__":
    print(netz.statistik())
    while True:
        try:
            text = input("Du: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text:
            print("Jarvis:", jarvis_antwortet(text))
