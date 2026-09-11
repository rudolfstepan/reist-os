# Shell, Befehle und Pfade

Stand: 11. September 2026, normale `/bin/shell.prg`, Terminalfarben R3.44 und JS R3.45.

Die Shell orientiert sich bei Navigation und Dateibefehlen an MS-DOS, nutzt
intern aber ausschließlich kanonische VFS-Pfade. Der Prompt zeigt das aktuelle
DOS-Laufwerk und Verzeichnis, beispielsweise `C:\TOOLS>`.

## Befehle

| Zweck | Befehl und Alias |
|---|---|
| Built-ins | `HELP`, `CD`, `CHDIR`, `PWD`, `HISTORY`, `PATH`, `EXIT` |
| Hilfe/Bildschirm | `HELP`, `CLS`, `CLEAR`, `ECHO` |
| Auflisten | `DIR [pfad]`, `LS [pfad]` |
| Verzeichnis wechseln | `CD [pfad]`, `CHDIR [pfad]` |
| Verzeichnis anlegen | `MD pfad`, `MKDIR pfad` |
| Verzeichnis entfernen | `RD pfad`, `RMDIR pfad` |
| Datei anzeigen | `TYPE datei`, `CAT datei` |
| Datei anlegen/löschen | `TOUCH datei`, `DEL datei`, `ERASE`, `RM datei` |
| Kopieren/Umbenennen | `COPY`, `CP`, `RENAME`, `REN`, `MV` |
| Laufwerke | `DRIVES`, `MOUNT laufwerk`, `C:`, `hdd0p2:` |
| Programme | direkter Name oder Pfad, `PS`, `KILL`, `BASIC`, `DESKTOP`, `BROWSER`, `JS` |
| Netzwerk | `GETIP`, `IFCONFIG`, `PING`, `ARP`, `NET` |
| Diagnose | `MEMINFO`, `SYSINFO`, `DRIVES`, `USBINFO`, `AUDIOINFO`, `DATETIME` |

Der reguläre Bootpfad lädt `SHELL.PRG` als Ring-3-Command-Line-Interpreter.
Die fest einkompilierte Kernel-Shell ist ausschließlich die Rettungskonsole,
falls das Userspace-Programm nicht geladen werden kann oder beendet wird.

Die Userspace-Shell verwaltet einen eigenen `PATH`. Das aktuelle Verzeichnis
wird zuerst geprüft, anschließend die mit Semikolon getrennten
Suchverzeichnisse. Standardmäßig enthält `PATH` die kanonischen Verzeichnisse
`/bin`, `/sbin`, `/usr/bin` und `/usr/gui/bin`. Interne Dienste unter
`/libexec/reist` sind nicht Teil des allgemeinen Suchpfads.

Die Tabelle beschreibt ausschließlich Built-ins, Aliase und paketierte
`.PRG`-Programme der normalen Ring-3-Shell. Gleichnamige Diagnosefunktionen der
Kernel-Rettungsshell, etwa der historische `PCI`-Befehl, gelten nicht als
reguläre Benutzerbefehle.

Befehlsnamen sind unabhängig von Groß-/Kleinschreibung. Argumente werden
nicht pauschal großgeschrieben. Dateinamen auf FAT werden beim Nachschlagen
case-insensitiv behandelt.

## Pfadformen

Alle folgenden Formen werden vom selben Resolver verarbeitet:

```text
README.TXT             relativ zum aktuellen Verzeichnis
.\README.TXT           explizit relativ
..\BIN\APP.PRG         mit Elternverzeichnis
\DOCS\README.TXT       absolut auf aktuellem Laufwerk
C:\DOCS\README.TXT     DOS-Laufwerk
C:DOCS\README.TXT      relativ zum gemerkten C:-Verzeichnis
hdd0p2:/DOCS/README.TXT nativer Partitionsname
/hdd0p2/DOCS/README.TXT ältere kompatible VFS-Schreibweise
```

`/` und `\` dürfen gemischt werden. Mehrfache Trennzeichen und `.` werden
entfernt; `..` steigt höchstens bis zur Laufwerkswurzel auf. Ein zu langer
oder ungültiger Pfad wird abgelehnt, nicht abgeschnitten.

## Laufwerkswechsel

Gemountete Festplatten-/Partitionsvolumes werden ab `C:` und Disketten ab
`A:` zugeordnet. Das Root-Volume erhält `C:`; konkrete Gerätenamen und
Resource-IDs werden immer mit `DRIVES` ermittelt:

```text
hdd0p2 -> C:  hdd1p1 -> D:
fdd0 -> A:    fdd1 -> B:
```

Ein reines Laufwerkstoken wechselt das aktive Laufwerk:

```text
C:\DOCS> D:
D:\> C:
C:\DOCS>
```

Jedes Laufwerk merkt sein eigenes aktuelles Verzeichnis. Ein Pfad mit
explizitem Laufwerk greift auf dieses Laufwerk zu, ohne bei reinen Lese- oder
Dateioperationen den Prompt dauerhaft umzuschalten. `CD D:\TOOLS` wechselt
dagegen bewusst Laufwerk und Verzeichnis.

## Einheitliche VFS-Verwendung

`DIR`, `CD`, `TYPE`, Mutationen und `COPY` verwenden die VFS-/Objektadapter.
Ein inzwischen entferntes oder gesperrtes Objekt darf nach einer Auflistung
dennoch abgelehnt werden. Programme werden direkt mit Namen/Pfad gestartet.
`RUN`, `EXEC`, `OPEN` und `MKFILE` sind keine Built-ins/Aliase dieser Shell.

`TYPE` liest Dateien blockweise und benötigt weder eine NUL-Terminierung noch
einen komplett im Speicher liegenden Inhalt. `COPY` überschreibt kein
vorhandenes Ziel und entfernt ein unvollständiges Ziel nach einem Fehler.
`CD` übernimmt einen neuen Pfad erst, nachdem VFS dessen Verzeichnisstatus
bestätigt hat.

## Parser

- 256 Byte Zeilenpuffer, höchstens 255 Eingabebytes plus NUL
- maximal 16 Tokens einschließlich Programmname
- Leerzeichen und Tabs trennen Argumente
- keine Quote-Auswertung: Anführungszeichen sind gewöhnliche Zeichen
- der Zeilenpuffer nimmt darüber hinaus keine Zeichen an; der Splitter
  verarbeitet nur die ersten 16 Tokens, ohne behauptete Syntaxfehlermeldung
- keine Pipes, Umleitungen, Variablenexpansion oder bedingte Verkettung

Beispiel:

```text
C:\> ECHO mehrere getrennte Argumente
```

## Zeilenbearbeitung

| Taste | Wirkung |
|---|---|
| Links/Rechts | Cursor innerhalb der Zeile bewegen |
| Pos1/Ende | Anfang/Ende der Eingabe |
| Entf | Zeichen unter dem Cursor löschen |
| Rücktaste | Zeichen vor dem Cursor löschen |
| Hoch/Runter | Verlauf durchsuchen und Entwurf wiederherstellen |
| `Ctrl+C` | aktuelle Eingabe verwerfen |
| `Ctrl+L` | Bildschirm löschen und Eingabe neu zeichnen |
| `Ctrl+U` | komplette Zeile löschen |
| `Ctrl+K` | vom Cursor bis Zeilenende löschen |

`HISTORY` zeigt bis zu 50 gespeicherte Befehle. Unmittelbar aufeinanderfolgende
Duplikate werden nicht erneut aufgenommen.

Tab vervollständigt das aktuelle Wort. Am Zeilenanfang werden Built-ins,
Aliase und `.PRG`-Programme aus dem aktuellen Verzeichnis und `PATH`
durchsucht; die Erweiterung `.PRG` muss dabei nicht eingegeben werden. Bei
Argumenten werden Dateien und Verzeichnisse relativ zum aktuellen oder
explizit angegebenen Pfad ergänzt. Eindeutige Verzeichnisse erhalten einen
abschließenden Backslash.

## Beispiele

```text
C:\> DIR
C:\> MD TEST
C:\> CD TEST
C:\TEST> TOUCH INFO.TXT
C:\TEST> TYPE ..\README.TXT
C:\TEST> COPY ..\HELLO.PRG APP.PRG
C:\TEST> APP.PRG
C:\TEST> CD \
C:\> RD TEST
```

Ein nicht leeres Verzeichnis oder ein aktives aktuelles Verzeichnis wird vom
Dateisystem bzw. der Shell nicht blind entfernt; die konkrete Unterstützung
hängt vom gemounteten Dateisystemadapter ab.

## JavaScript, Exitstatus und Farben

```text
js /htdocs/jsargs.js test
js /htdocs/mandel.js
js --read /htdocs/hello.js /htdocs/jsread.js
```

`js` ist `/usr/bin/js.prg`. Der Quellname ist exakt und relativ zum aktuellen
Verzeichnis, ohne automatische `.js`-Ergänzung. `scriptArgs[0]` trägt diesen
Namen, weitere Argumente sind Strings. `print`/`console.log` und `console.error`
liefern getrennte stdout-/stderr-Records, gepuffert und vor Ausgabe validiert.
[Beispiele und Grenzen](../development/JS_SHELL_EXAMPLES.md).

`reist.setExitCode(n)` setzt 0..125 für normalen Abschluss, beendet aber nicht
die Ausführung. Die Shell wartet/reapt, stellt jedoch noch kein `%ERRORLEVEL%`
oder anderes Skriptäquivalent bereit. `system.exit` ist nur ein Vorschlag.
Die native Farbausgabe verwendet einen zustandslosen, typisierten Farbspan:

```text
echo --color red Fehler
echo --color bright-green Fertig
echo Normalfarbe bleibt unveraendert
colortst
```

Namen: `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`,
jeweils auch mit `bright-`. Nur Vordergrundprogramme an schreibbaren
Terminaldeskriptoren dürfen ausgeben, nicht auf den aktiven Desktop.
Der native Adapter prüft höchstens 4096 ASCII-Bytes/5s; die Shell bleibt bei
ihrer bestehenden 256-Byte-Zeile/16 Argumenten und kennt keine Quote-Auswertung.
Ohne `--color` bleibt ECHO unverändert. Details:
[Farbvertrag](../architecture/TERMINAL_COLOR_OUTPUT_CONTRACT.md).

JS-Farbausgabe R3.45 (Abnahmestand in CURRENT_WORK):

```javascript
reist.printColor('green', 'Fertig', 42);
reist.errorColor('bright-red', 'Fehler');
print('Wieder normale Farbe');
```

Dieselben 16 Namen, Leerzeichen zwischen Werten, abschließendes LF.
Keine Farbzustände oder nötigen Resetbefehle. Farbtext ist ASCII; ESC und
Nicht-ASCII-Bytes werden durch `?` ersetzt. Quoten, Reap und Hostvalidierung
bleiben verbindlich. Rohes ANSI wird noch nicht als Terminalformat unterstützt.
`js /htdocs/jscolors.js` und `js /htdocs/mandelc.js` zeigen beide Ausgabewege.
[JS-Farbvertrag](../architecture/JS_COLOR_OUTPUT_CONTRACT.md).
