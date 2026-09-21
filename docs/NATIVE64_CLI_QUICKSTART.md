# REIST native64 CLI — QEMU-Forschungsversion

Status: Als begrenzte CLI-Forschungsversion abgenommen am 21. September 2026:
neun Prüfgruppen und alle zehn BIOS-/Gastfälle bestanden. Es verwendet den
bereits abgenommenen 64-Bit-Kernel und die normalen
Ring-3-Programme unverändert. Kein Kernel-Neubau zum Starten nötig.

## Start unter Windows

Im Repository mit Python, QEMU und OpenSSL im Suchpfad:

```powershell
.\scripts\start-x86_64-cli.ps1 -CheckOnly
.\scripts\start-x86_64-cli.ps1
```

Bei Bedarf `-OpenSSL 'C:\Program Files\FireDaemon OpenSSL 4\bin\openssl.EXE'`
angeben. `-Layout floppy` wählt den Rettungs-Diskettenstart; `-Ram 8192`
wählt 8 statt 4 GiB Gast-RAM. Python-Einstieg:

```powershell
python scripts/run_x86_64_cli.py --check-only
python scripts/run_x86_64_cli.py
```

Das Paket liegt unter `build/codex-agent/r83bd-cli-delivery/candidate01/media`.
`cli-media.json` benennt das signierte Unterverzeichnis mit BIOS-HDD,
Rettungsdiskette und `system.ext2`. Nicht einzelne Images austauschen.
Das abgenommene Unterverzeichnis heißt
`shell-media-18c7322802ed49f9a8c1abb1b1d52c2a`; SHA-256 des Index:
`f1c2d433430ce3d367dbfc0d4c2d7d19fd04e2867df57d5ca469df95c1c941c2`.
Vor jedem Start werden Signaturen, die zwölf abgenommenen Eingaben,
Medieneinbettung und tatsächliche Dateiinhalte geprüft. Ein Fehler verhindert
den Gaststart. Die Entwicklungsschlüssel sind öffentliche Testschlüssel,
keine Produktions-Secure-Boot-Vertrauenskette.

## Shell verwenden

Die normale Shell läuft in Ring 3 an der seriellen Konsole. Beispiele:

```text
cat /data.txt
ls -1 /
probe /data.txt
exit
```

`cat`, `ls` und `probe` sind echte gestartete `.prg`-Programme. Sie erhalten
explizit begrenzte, widerrufbare Nur-Lese-Objekte; keinen rohen Gerätezugriff.
`probe` ist das normale Prüfprogramm, nicht die Lasttest-Variante.

Diese Version hat zwei Shell-Läufe; nach dem zweiten `exit` folgt der
Qualifikationshalt. Die Sitzung endet spätestens nach 320 Sekunden,
einschließlich Cleanup; `Ctrl+C` beendet sie früher. Ein Halt ist kein Desktop.
Eine Sitzung ist keine Wiederholung der vollständigen Fehlerfall-Abnahme.

## Grenzen und Nachweise

Nur QEMU `pc`/TCG, `qemu64`, eine CPU, 4/8 GiB sind abgedeckt. BIOS-HDD als
primärer Slave beziehungsweise Rettungsdiskette; separate Nur-Lese-Daten als
primärer Master. Der Starter erzeugt private Copy-on-write-Schichten und
prüft nach Ende beide Medien vollständig auf unveränderte Basis und fehlende
Schreiballokationen. Sitzungsdateien und Fehler bleiben unter
`build/codex-agent/cli-sessions` erhalten. Keine Benutzerfestplatten anbinden.

Kein Netzwerk, Desktop, Browser, Schreibdateisystem, DMA, Host-Freigaben,
VMware- oder physischer Hardware-Nachweis; keine POSIX-Kompatibilitäts-,
Zertifizierungs- oder Produktionsfreigabe. Diese Punkte sind nicht Teil der
vom Benutzer vorgezogenen CLI-Erstlieferung.

Der lokale Abschlussbeleg mit Implementierungs-Commit und gebundenen Nachweisen
liegt unter `build/codex-agent/r83bd-cli-delivery/candidate02/verification-status-cli-delivery-final.json`.
Die vollständige Abnahme umfasst fünf positive Fälle (Ersatzslot/Treiberneustart,
wiederholte Befehle, normaler Start, 8 GiB, Diskette/Anwendungshänger) und fünf
Boot-Ablehnungen bei beschädigten Signaturen, Prüfsummen oder Manifesten.
Insgesamt zehn physische Gäste/585.8585124001256 Sekunden, ein Medienpaket,
kein Kernel-/Programm-Neubau. Der ursprüngliche Prüfadapter-Fehlversuch bleibt
erhalten; seine Rohdaten wurden nach gezielter Korrektur vollständig nachgeprüft.
