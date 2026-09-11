# Quickstart

Stand: 11. September 2026; angenommener Softwarestand bis R3.44.

Diese Anleitung beschreibt den bevorzugten, vollständig nativen Windows-Weg.
WSL, GRUB und ein Cross-GCC sind dafür nicht nötig.

## Voraussetzungen

- Windows 10 oder 11 mit PowerShell
- GNU Make
- NASM
- Zig
- Python 3
- OpenSSL 3, Perl und GNU gperf (Bootsignatur und Parsergeneratoren)
- MSYS2 mit `sh.exe` und den grundlegenden Unix-Werkzeugen
- VMware Workstation zum Starten der fertigen VM
- optional QEMU für den Raw-Image-Test

`scripts/build-windows.ps1` prüft konfigurierte Werkzeugpfade und danach
`PATH`. Unterstützte Pfade stehen im Skript. Fehlende Werkzeuge werden
mit ihrem Programmnamen gemeldet; es findet keine automatische Installation
statt.

## Kernel, Tests und VMware-Paket bauen

Im Projektstamm:

```powershell
.\scripts\build-windows.ps1 -Target vmware -Video vga
```

Der Build arbeitet inkrementell: unveränderte Kernelobjekte und Ring-3-
Programme bleiben erhalten. Ein Konfigurationswechsel löst gezielt einen
sauberen Neubau aus; `-Clean` erzwingt ihn ausdrücklich. Danach werden beide
BIOS-Stufen, das Raw-Image und das VMware-Paket aktualisiert.

`-RunTests` ergänzt bewusst die gesamte Hostsuite. Für gezielte Änderungen
gelten die eingefrorenen Pakettests; keine parallelen Builds/Cleans starten.
Das Skript hat `real_hw` als Standard: Ziel immer explizit angeben.
Die Referenzplatte hat 512 MiB, die VM-Startwege verwenden 1024 MiB RAM.

Wichtige Ergebnisse:

```text
build/kernel.bin
build/stage1_mbr.bin
build/stage2_bios.bin
build/reist-os.img
build/programs/HELLO.PRG
build/programs/DESKTOP.PRG
build/programs/NOTEPAD.PRG
build/programs/IMAGEVIEWER.PRG
build/programs/SOUNDPLAYER.PRG
build/vmware/reist-os/reist-os.vmx
build/vmware/reist-os/START-VMWARE.cmd
```

## Starten

VMware:

```powershell
.\build\vmware\reist-os\START-VMWARE.cmd
```

QEMU mit bereits gebautem Raw-Image:

Den QEMU-Stand zuvor mit
`.\scripts\build-windows.ps1 -Target qemu -Video vga` bauen.
`-NoBuild` wandelt ein vorhandenes VMware-Profil nicht in ein QEMU-Profil um.

```powershell
.\scripts\run-windows.ps1 -NoBuild
```

QEMU über AHCI/SATA:

```powershell
.\scripts\run-windows.ps1 -NoBuild -Sata
```

Ein Headless-QEMU-Start zeigt die Bootloader-Diagnose, stellt aber keine
interaktive VGA-Shell auf der Konsole bereit:

```powershell
.\scripts\run-windows.ps1 -NoBuild -Headless
```

## Grafischen Desktop starten

Der normale VMware- und QEMU-Entwicklungsweg darf im VGA-Textmodus booten.
Aus der Ring-3-Shell aktiviert `desktop` den geprüften Grafikpfad zur Laufzeit:

```text
C:\> desktop
```

Ein Framebuffer-Build startet ebenfalls zuerst die Shell, nun im Boot-Framebuffer:

```powershell
.\scripts\build-windows.ps1 -Target qemu -Video framebuffer -RunTests
.\scripts\run-windows.ps1 -NoBuild
```

Stage 2 bevorzugt VBE 1024x768x32 und versucht danach 800x600x32. `desktop`
startet danach ausdrücklich `/usr/gui/bin/desktop.prg`. Der Desktop zeigt einen
Explorer mit
verschieb- und skalierbaren Ordnerfenstern. Ein Doppelklick öffnet Ordner oder
startet eine validierte Dateizuordnung. Notepad und Image Viewer bleiben als
getrennte Ring-3-Surface-Fenster gleichzeitig mit dem Desktop aktiv;
`surfacedemo` prüft denselben öffentlichen Clientvertrag. Noch nicht migrierte
Programme verwenden den Vollbild-Kompatibilitätspfad und kehren danach in die
unveränderte Desktopsitzung zurück. `Esc` beendet die Laufzeitsitzung und
stellt die VGA-Shell wieder her.

Ist kein geeignetes natives oder vorbereitetes VBE-Backend vorhanden, bleibt
VGA-Text aktiv und `desktop` meldet den Fehler ohne eine unvollständige
Grafiksitzung zu veröffentlichen. `DESKTOP_OK` und `DESKTOP_SURFACE_OK` im
seriellen Log bestätigen Render- beziehungsweise Surface-Gastnachweis.

## Erster Funktionstest

Beim standardmäßigen VGA-Build sollte nach dem Boot der Prompt `C:\>`
erscheinen. Danach:

```text
C:\> DIR
C:\> TYPE README.TXT
C:\> HELLO
C:\> GETIP
C:\> NET STATUS
```

`HELLO.PRG` meldet bei Erfolg `USERSPACE-E2E-OK`. Bei einer gebridgten
VMware-Verbindung zeigt `GETIP` die per DHCP bezogene VM-Netzadresse.

Das erzeugte VMware-Paket verwendet standardmäßig NAT-DHCP, nicht Bridging.
`browser`, `display` und `mouse` sind über den Shell-Suchpfad erreichbar.
Anzeige-/Mauseinstellungen gelten beim nächsten Desktopstart; keine freie
Farbtiefenwahl oder Live-Modusumschaltung. Die Systemsteuerung bietet eigene
Applets, Fenster besitzen Minimieren/Maximieren/Wiederherstellen.

```text
js /htdocs/jsargs.js hallo 42
js /htdocs/mandel.js
js --read /htdocs/hello.js /htdocs/jsread.js
```

Sieben [JS-Beispiele](JS_SHELL_EXAMPLES.md) liegen in beiden Images.
`js DATEI` ergänzt kein `.js`. Die Shell hat keine Quote-Auswertung, Pipes
oder `%ERRORLEVEL%`; einfache Farben und `system`-/`fs`-APIs sind noch geplant.

## Eigenes Programm

```powershell
.\scripts\build-windows.ps1 -Target vmware -RunTests `
  -ProgramSource C:\Projekte\meinprog.c `
  -ProgramName MEINPRG.PRG
```

Der Name im Image muss ein eindeutiger ASCII-8.3-Name mit der Endung `.PRG`
sein. Mehrere Quellen werden als PowerShell-Array übergeben:

```powershell
.\scripts\build-windows.ps1 -Target vmware `
  -ProgramSource .\app.c,.\math.c,.\helper.S `
  -ProgramName APP.PRG
```

Nur das mitgelieferte SDK ist die öffentliche Programmierschnittstelle. Siehe
[USER_PROGRAM_TOOLCHAIN.md](USER_PROGRAM_TOOLCHAIN.md).

## Direkte Make-Ziele

Auf Linux/macOS oder in einer entsprechend eingerichteten Shell:

```bash
make kernel TARGET=qemu VIDEO=vga
make user-program
make native-image TARGET=real_hw VIDEO=vga
make run-native TARGET=qemu VIDEO=vga
make run-fb
make test-unit
make test-smoke TARGET=qemu VIDEO=vga
```

`make all`, `make run` und `make native-image` verwenden den eigenen
BIOS-Bootloader. Sie entsprechen damit dem nativen Windows-/VMware-
Paket.

`make test-smoke` startet das QEMU-Image ohne Anzeige, führt den automatischen
Ring-3-Test aus und schreibt das serielle Protokoll nach
`build/guest-smoke.log`. Der Test benötigt `qemu-system-i386` im `PATH`.

## Häufige Fehler

### Werkzeug nicht gefunden

Das gemeldete Programm installieren oder in den `PATH` aufnehmen. Bei
portablen Paketen kann der Fallbackpfad in `build-windows.ps1` ergänzt werden.

### VMware-VM läuft beim Neubau

Die VM sauber herunterfahren. Das Buildskript verweigert das Überschreiben
einer laufenden paketierten VM.

### Kein LAN

Zuerst NAT-/DHCP-Dienste und den verbundenen E1000 prüfen. Nur bei bewusst
gewähltem Bridging `VMnet0` dem Hostadapter zuordnen; WLAN-Client-Isolation
kann dann Gäste blockieren. Danach mit `NET DHCP`
den automatisch durch `REIST.PRG` verwalteten Lease-Zustand und mit `GETIP`
die aktive Konfiguration prüfen.

### Programm wird abgelehnt

Den Packer verwenden und keine fremde ELF-Datei nur in `.PRG` umbenennen. Der
Loader akzeptiert ausschließlich geprüfte MYPR-Images für Basisadresse
`0x40000000` und maximal 8 MiB. Der Kernel liest die Datei in einen
dynamischen Heap-Puffer, kopiert sie in private Prozessseiten und gibt den
Puffer danach wieder frei; es gibt keine zweite Link- oder Ausführungsadresse.
