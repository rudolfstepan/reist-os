# Native64: grafische Forschungssitzung

Der Starter wird erst nach allen acht Paketpruefungen und dem lokalen
Abnahmecommit freigeschaltet. Solange `final.json` fehlt, verweigert er den
Start. Er baut keine Ersatzdateien und waehlt keine ungeprueften Medien aus.

Im Repository mit installiertem Python, QEMU und OpenSSL:

```powershell
.\scripts\start-x86_64-graphical.ps1 -CheckOnly
.\scripts\start-x86_64-graphical.ps1
```

Die serielle Shell erscheint im aufrufenden Terminal. Dort `desktop` eingeben.
Im QEMU-Fenster oeffnen sich ein Textfenster und ein einfaches Zeichenfenster.
Den Fokus per Linksklick oder Alt+Tab wechseln. Das Textfenster nimmt US-ASCII
an; Enter leert seine Zeile. Im Zeichenfenster bewegt die Maus eine Markierung.
Fenster lassen sich am Titel verschieben. Esc beendet die grafische Sitzung
und gibt die serielle Shell frei; dort funktioniert beispielsweise
`cat /data.txt`.

QEMU-Fenster schliessen oder Strg+C beendet den Hostlauf. Die gesamte Sitzung
ist auf180 Sekunden begrenzt, einschliesslich Aufraeumen. Originalmedien bleiben
schreibgeschuetzt; eigene temporaere Overlays und Nachweise liegen unter
`build/codex-agent/r83bi-graphical-session/sessions/`.

Optionen: `-Layout floppy` fuer das Disketten-Bootmedium und `-Ram 8192`
fuer8GiB. Standard: HDD-Bootmedium,4GiB, ein virtueller Prozessor mit TCG.
Die grafische Arbeitsflaeche nutzt640x480 Bildpunkte innerhalb des1024x768-
Framebuffers. Das Profil enthaelt zwei begrenzte Surface-Anwendungen; weitere
Desktopfunktionen, Browser, Netzwerk und physische Hardware sind noch offen.

Technischer Vertrag und Grenzen:
[Native graphical session](../architecture/NATIVE_GRAPHICAL_SESSION_CONTRACT.md).
