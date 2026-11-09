# Jarvis-Wissensnetz einrichten (Windows)
# Installiert graphify, legt den Wissens-Ordner an, speichert den KI-Schluessel
# und startet den Hintergrund-Dienst automatisch bei jeder Anmeldung.

$ErrorActionPreference = "Stop"
$Hier = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Hier

function Schritt($text) { Write-Host ""; Write-Host "==> $text" -ForegroundColor Yellow }

# 1. Python finden
Schritt "Python suchen"
$Python = $null
foreach ($kandidat in @("py", "python")) {
    $cmd = Get-Command $kandidat -ErrorAction SilentlyContinue
    if ($cmd) {
        $pfad = & $kandidat -c "import sys; print(sys.executable if sys.version_info >= (3,10) else '')" 2>$null
        if ($pfad) { $Python = $pfad.Trim(); break }
    }
}
if (-not $Python) {
    Write-Host "Python 3.10 oder neuer fehlt." -ForegroundColor Red
    Write-Host "Installiere es mit:  winget install Python.Python.3.12"
    Write-Host "oder von https://www.python.org/downloads/ (Haken bei 'Add to PATH' setzen)."
    Write-Host "Danach dieses Skript nochmal starten."
    exit 1
}
Write-Host "Gefunden: $Python"
$PythonW = Join-Path (Split-Path $Python) "pythonw.exe"

# 2. KI fuer Dokumente waehlen
Schritt "Welche KI soll deine Dokumente lesen?"
Write-Host "  1) Claude   - beste Qualitaet, braucht API-Key von console.anthropic.com (kostet pro Nutzung)"
Write-Host "  2) Gemini   - guenstig, braucht API-Key von aistudio.google.com"
Write-Host "  3) Ollama   - laeuft komplett lokal und gratis, braucht Ollama (ollama.com), langsamer"
$wahl = Read-Host "Nummer eingeben [1]"
switch ($wahl) {
    "2" { $Backend = "gemini"; $Extra = "gemini"; $KeyName = "GEMINI_API_KEY" }
    "3" { $Backend = "ollama"; $Extra = "ollama"; $KeyName = $null }
    default { $Backend = "claude"; $Extra = "anthropic"; $KeyName = "ANTHROPIC_API_KEY" }
}

# 3. graphify installieren
Schritt "graphify installieren (kann ein paar Minuten dauern)"
& $Python -m pip install --upgrade pip | Out-Null
& $Python -m pip install --upgrade "graphifyy[$Extra,pdf,office]"
if ($LASTEXITCODE -ne 0) { Write-Host "Installation fehlgeschlagen." -ForegroundColor Red; exit 1 }

# 4. Schluessel speichern
if ($KeyName) {
    $vorhanden = [Environment]::GetEnvironmentVariable($KeyName, "User")
    if ($vorhanden) {
        Write-Host "$KeyName ist schon gespeichert."
    } else {
        Schritt "API-Key eingeben (wird nicht angezeigt)"
        $sicher = Read-Host "$KeyName" -AsSecureString
        $klar = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sicher))
        if ($klar) {
            [Environment]::SetEnvironmentVariable($KeyName, $klar, "User")
            Set-Item -Path "env:$KeyName" -Value $klar
            Write-Host "Gespeichert in deinen Windows-Benutzervariablen."
        } else {
            Write-Host "Kein Key eingegeben. Code wird trotzdem erfasst, Dokumente erst mit Key." -ForegroundColor Red
        }
    }
} else {
    Write-Host "Ollama: Stelle sicher, dass Ollama laeuft und ein Modell geladen ist, z. B.:"
    Write-Host "  ollama pull qwen2.5:7b"
    Write-Host "  setx OLLAMA_MODEL qwen2.5:7b"
}

# 5. Ordner und Einstellungen
Schritt "Wissens-Ordner festlegen"
$Standard = Join-Path $env:USERPROFILE "JarvisWissen"
$Ordner = Read-Host "Ordner fuer Jarvis' Wissen [$Standard]"
if (-not $Ordner) { $Ordner = $Standard }
New-Item -ItemType Directory -Force -Path $Ordner | Out-Null
$cfg = Get-Content (Join-Path $Hier "config.json") -Raw | ConvertFrom-Json
$cfg.ordner = $Ordner
$cfg.backend = $Backend
$cfg | ConvertTo-Json | Set-Content (Join-Path $Hier "config.json") -Encoding UTF8
Write-Host "Ordner: $Ordner"

# 5b. Startwissen (Marketing) und Ordner fuer Fakten/Gespraeche
Schritt "Marketing-Wissen und Gedaechtnis-Ordner anlegen"
Copy-Item -Path (Join-Path $Hier "wissen\*") -Destination $Ordner -Recurse -Force
foreach ($u in @("fakten", "gespraeche", "_import")) { New-Item -ItemType Directory -Force -Path (Join-Path $Ordner $u) | Out-Null }
Write-Host "Marketing-Wissen kopiert nach $(Join-Path $Ordner 'marketing')"

# 5c. Claude beibringen, Fakten fuer Jarvis zu speichern
Schritt "Skill 'jarvis-merken' fuer Claude Code installieren"
$SkillZiel = Join-Path $env:USERPROFILE ".claude\skills\jarvis-merken"
New-Item -ItemType Directory -Force -Path $SkillZiel | Out-Null
Copy-Item -Path (Join-Path $Hier "claude-skill\jarvis-merken\SKILL.md") -Destination $SkillZiel -Force
Write-Host "Installiert: $SkillZiel"
Write-Host "Fuer die Claude-App: SKILL.md unter Einstellungen > Faehigkeiten (Skills) hochladen."

# 6. Autostart
Schritt "Autostart einrichten"
$Startup = [Environment]::GetFolderPath("Startup")
$Link = Join-Path $Startup "Jarvis Wissensnetz.lnk"
$shell = New-Object -ComObject WScript.Shell
$sc = $shell.CreateShortcut($Link)
$sc.TargetPath = $PythonW
$sc.Arguments = "`"$(Join-Path $Hier 'wissensnetz_dienst.py')`""
$sc.WorkingDirectory = $Hier
$sc.Description = "Haelt das Graphify-Wissensnetz fuer Jarvis aktuell"
$sc.Save()
Write-Host "Startet ab jetzt bei jeder Anmeldung: $Link"

# 7. Jetzt starten
Schritt "Dienst jetzt starten"
Start-Process -FilePath $PythonW -ArgumentList "`"$(Join-Path $Hier 'wissensnetz_dienst.py')`"" -WorkingDirectory $Hier
Write-Host ""
Write-Host "Fertig! Leg Dateien in $Ordner - das Netz baut sich automatisch." -ForegroundColor Green
Write-Host "Protokoll: $(Join-Path $Hier 'wissensnetz.log')"
Write-Host "In Jarvis:  from jarvis_wissen import WissensNetz"
Read-Host "Enter zum Schliessen"
