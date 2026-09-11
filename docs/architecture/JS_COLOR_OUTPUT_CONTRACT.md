# JS-Farbausgabe: getrennte Erzeugung und Publikation (R3.45)

Eingefroren am 11. September 2026 auf `c66f5de9`, vor Implementierung.
Ein Ring-3-Host-Ausgabepaket auf dem abgenommenen Syscall131. Keine Änderung
an Kernel, SDK, QuickJS-Sprachkern, Scheduler, Browserbindings oder Autorität.

## API und bestehende Grenzen

ECMA-262-Ausführung und die vorhandene QuickJS-Stringkonversion bleiben erhalten.
`reist.printColor(name, ...values)` schreibt stdout, `reist.errorColor` stderr,
mit Leerzeichen zwischen Werten und abschließendem LF wie bisheriges `print`.
Nur primitive Strings als Farbname: black, red, green, yellow, blue, magenta,
cyan, white sowie bright-<name>. ECMA-48-Grundreihenfolge und ausdrückliche
REIST-Bright-Erweiterung wie im [Terminalvertrag](TERMINAL_COLOR_OUTPUT_CONTRACT.md).
Keine WHATWG-Console-/ANSI-/Node-Kompatibilitätszusage, keine neue console-API.
Ungültige Namen/fehlende Farbe werfen ohne Veröffentlichung dieses Records.
Aufgefangene normale Konversionsfehler behalten frühere vollständige Records;
Quota/Reentry vergiften weiterhin die gesamte Evaluation, ohne gültiges Präfix.

Bindings nur nach SCRIPT/CAP_SCRIPT-Attach auf frischer Engine. Browser-EVAL
bekommt sie nicht. Keine Engine-I/O-Callbacks, persistenten Farbeinstellungen,
Handles, Endpunkte, VFS-/Netz-/Prozess-/Adminrechte oder neuen Worker-Syscalls.
60KiB/256 Records, 32MiB Engine, 64MiB Worker, 16KiB Stack, 1024 Jobs,
5s Ausführung/Ausgabe und 1s Reap bleiben unverändert.

## Versionierte private Records

Der äußere 72-Byte-Header/Version1 und alle Operationsnummern bleiben unverändert.
Der bestehende 24-Byte-Reply hat zusätzlich Version2. Version1 bleibt akzeptiert
und erlaubt nur die bisherigen Records (stream1/2, length, UTF8-Text mit LF).
Version2 akzeptiert diese unverändert sowie Typ3/4 für farbiges stdout/stderr:
uint32 type, uint32 length, dann uint32 foreground0..15 und Text mit LF.
length umfasst Farbwort und Text; Hintergrund ist fest schwarz, kein Reset nötig.
Neue Worker antworten mit Version2; alte Workerantworten bleiben lesbar.
Das ist eine dokumentierte lokale Protokollerweiterung, keine globale Capability.

Der Host validiert Version, exakte Größe, sämtliche Typen/Längen/Farben und
End-LF sowie Gesamtzahlen vor dem ersten sichtbaren Byte. Danach stateless
Publikation über feste Deskriptoren1/2 und ausschließlich den abgenommenen
SDK-Farbaufruf. Fragmente maximal64 Bytes/ein LF, vorhandene absolute5s-Frist.
Keine verborgene Wiederholung oder Datei/Klartext-Fallback nach Ablehnung.
Kurze/fehlerhafte typisierte Ausgabe meldet I/O-Fehler74. Alte Klartextrecords
behalten Short-Write-Verhalten und UTF8-Bytes; C0 außer TAB/LF und DEL werden
weiter durch '?' ersetzt. Farbspans ersetzen zusätzlich jedes Nicht-ASCII-Byte
durch '?' wegen des expliziten ASCII-Kernelvertrags. Kein Unicode-Farbclaim.
Vollständiger Workerabschluss/Reap und Broker-Close bleiben vor Publikation.

## Abnahme und Beispiele

`js /htdocs/jscolors.js` prüft Namen, stderr, ungültige Argumente, längere und
mehrzeilige Records sowie unveränderte Normalfarbe. `js /htdocs/mandelc.js`
liefert ein begrenztes farbiges ASCII-Mandelbrot; vorhandenes mandel.js bleibt
unverändert. Keine Schreib-/Dateigrants, Autostarts oder sichtbaren Fenster.
Windows und Make paketieren identische Dateien; normale Ring-3-Shelldispatches.

17 Gruppen in der Queue: echte Core-/Runner-/Files-/Service-/Domain-Hosttests,
negative Bild-/Transcriptprüfer, Dokumentation, Basisarchiv, drei Builds samt
Framebufferarchiv, exakter Imagevergleich und vier Gastgruppen. Kernel und
alle bisherigen PRGs außer JS, JSWORK, JSRUNTST müssen byteidentisch bleiben.
R3.44-Imagepins (SHA256):

- QEMU-VGA: `68f4a69eee6b215f74b26cccd9f2d423ad4ecce003fa558393bc15e356417c8a`
- VMware-VGA: `0b136069c5e5f082eda47d9601c69744d94f8ed6d52b7869c0d1c71a064b77dd`
- archivierter QEMU-Framebuffer: `02095ab59e45ea9f0d87b74c7eb21a7ee04e9f55e53232519b155dcd9a5e6580`

Echte QEMU-Gäste: headless, 1024MiB, Snapshot, 180s je Lauf. Exakte Skriptausgabe,
Mandelbrotbild, VGA-/Framebuffer-Farb-Pixel, wiederholte Shellaufrufe nach
Fehlern und vorhandene Worker-/Browser-Recovery. Keine neue VMware-/WCET-Zusage.
Belege unter `build/codex-agent/r345-js-colors/`; Fehler nicht überschreiben.
R341-H1/H2 und VMware-R3.6b-Zurückstellung bleiben offen. Kein Folgepaket hier.
