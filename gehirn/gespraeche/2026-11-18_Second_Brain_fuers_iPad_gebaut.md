# Second Brain fürs iPad gebaut

Datum: 2026-11-18  
Quelle: Claude Code auf dem iPad

- Ziel: Jarvis' Gehirn auch vom iPad aus nutzen, damit keine Infos verloren gehen, auch wenn der PC aus ist.
- Lösung: Das Gehirn liegt im Repo-Ordner gehirn/ (fakten, notizen, gespraeche). Werkzeug: gehirn.py (uebersicht, suche, merken, notiz, gespraech).
- CLAUDE.md sagt jeder neuen Claude-Sitzung, dass sie das Gehirn zu Beginn liest, Fakten merkt und am Ende eine Zusammenfassung ablegt.
- PC-Seite: jarvis-wissensnetz/gehirn_sync.py gleicht gehirn/ mit JarvisWissen ab (beim Dienst-Start und alle 2 Minuten), Graphify baut daraus das Netz.
- Offen: Auf dem PC Git installieren, Repo klonen, installieren.bat im Klon ausführen (oder gehirn_repo in config.json setzen).
