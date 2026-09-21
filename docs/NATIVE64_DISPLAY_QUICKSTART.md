# REIST native64 Grafik starten

Die begrenzte QEMU-Grafikversion bietet eine serielle Ring-3-Shell und ein
normal gestartetes Programm, das ein farbiges64x64-Pixelfeld zeichnet.
Der native64-Grafikkern ist als Commit `17d12819` abgenommen: zwoelf Gates,
neun Grafik- und zehn CLI-/BIOS-Faelle. Der Starter besteht separat sechs
Gates, zwoelf Hosttests und zwei echte HDD-/Diskettensitzungen mit4/8GiB.

## Windows

Python, QEMU und OpenSSL muessen verfuegbar sein. Im Repository:

```powershell
.\scripts\start-x86_64-display.ps1 -CheckOnly
.\scripts\start-x86_64-display.ps1
```

Der zweite Befehl oeffnet die QEMU-Grafikanzeige. Befehle werden weiterhin
im aufrufenden Terminal eingegeben; die Tastatur im Grafikfenster ist nicht
mit der Shell verbunden. An der Shell-Eingabeaufforderung:

```text
boot.prg
cat /data.txt
ls -1 /
exit
```

`boot.prg` zeichnet oben links ein Farbverlaufsfeld und meldet
`DISPLAY_CLIENT_OK`; sein dokumentierter Selbsttest-Exitstatus ist82.
Die Shell kann anschliessend weitere Programme starten. Es gibt zwei
Shell-Laeufe; nach dem zweiten `exit` haelt der Gast an. `Ctrl+C` im Terminal
beendet die Sitzung. Spaetestens nach320 Sekunden wird sie aufgeraeumt.

`-Layout floppy` verwendet die Rettungsdiskette, `-Ram 8192` acht statt vier
GiB RAM. `-Seconds 60` verkuerzt die Sitzung (zulaessig30..320), `-Headless`
unterdrueckt das Grafikfenster. Bei Bedarf `-OpenSSL 'vollstaendiger Pfad'`.
Python-Einstieg mit denselben Funktionen:

```powershell
python scripts/run_x86_64_display.py --check-only
python scripts/run_x86_64_display.py --headless --seconds 60
```

## Medien und Grenzen

Das unveraenderte abgenommene Paket liegt unter
`build/codex-agent/r83be-display/media04`. Der signierte Index heisst
`display-media.json`, SHA256
`8c0fdfa5020ccd3e001f0225127b985ddc3f25ffcb66edb07c72f380dc1ded3e`.
Der Starter prueft Index, Signaturen, zwoelf Eingaben und alle Medieninhalte
vor dem Start. Die Entwicklungsschluessel sind oeffentliche Testschluessel.
Kopierte komplette Pakete koennen mit `-Directory` gewaehlt werden.

Jede Sitzung verwendet private Copy-on-write-Schichten und prueft anschliessend
beide Medien auf unveraenderte Inhalte. Belege und Fehler bleiben unter
`build/codex-agent/display-sessions`. Kernel oder Medien werden nicht gebaut.

Abgedeckt ist QEMU pc/TCG, qemu64, eine CPU,4/8GiB und VGA. Kein Desktop,
GUI-Eingabetreiber, Netzwerk, Browser, Schreibdateisystem, DMA, Host-Freigaben
oder weitere Hardwareabnahme; R3.6b bleibt vertagt. Die ausfuehrliche Grafik-
Abnahme liegt unter `build/codex-agent/r83be-display/candidate03/`.
Starter-Abnahme, Rohdaten und lokaler Commit-Beleg liegen unter
`build/codex-agent/r83bf-display-delivery/candidate02/`.
Die automatisierten Gastpruefungen liefen headless; die GTK-Fensteroption
ist am Host geprueft, das Fenster wurde dabei nicht manuell bedient.
