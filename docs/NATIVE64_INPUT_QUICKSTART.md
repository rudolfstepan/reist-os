# Native64: Tastatur und Maus in QEMU

Forschungsprofil R8.3bg: zehn Paketgates und22 frische Gastfaelle bestanden.
Die Eingabesitzung ist auf fuenf Sekunden begrenzt. Die Shell verwendet
weiterhin das serielle Terminal.

```powershell
.\scripts\start-x86_64-input.ps1 -CheckOnly
.\scripts\start-x86_64-input.ps1
```

Im seriellen Terminal `boot.prg` eingeben. Sobald `INPUT_READY` erscheint,
im QEMU-Grafikfenster Shift+A druecken, die Maus bewegen und klicken.
Ereignisse erscheinen im Terminal; Mausbewegungen zeichnen ein farbiges Feld.
Nach `INPUT_END` kann `boot.prg` erneut gestartet werden. `cat /data.txt`
und `ls -1 /` verwenden die bisherigen schreibgeschuetzten Dateidienste.

Optionen: `-Layout floppy`, `-Ram 8192`, `-Seconds 60` oder `-Headless`.
Ohne Angabe endet die QEMU-Sitzung nach320 Sekunden; Ctrl+C beendet sie
vorzeitig. `exit` beendet den jeweiligen Shell-Lauf.

Der Starter prueft Signaturen und feste Eingabehashes, verwendet private
Schreibschutz-Abbilder und prueft beide Medien vor und nach dem Lauf.
Nachweise liegen unter `build/codex-agent/input-sessions/`.
Die Medien unter `build/codex-agent/r83bg-input/media05/` gehoeren zum
QEMU-Forschungsprofil mit oeffentlichem Entwicklungsschluessel.

Ein dauerhafter Desktop, Tastatureingabe in die Shell, USB-Eingabegeraete und
physische Hardware sind noch nicht Bestandteil dieses Profils.
