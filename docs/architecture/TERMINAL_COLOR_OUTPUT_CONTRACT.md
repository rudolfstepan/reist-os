# Typisierte Terminal-Farbausgabe (R3.44)

Eingefroren am 11. September 2026 auf `396c29f2`, vor Implementierung.
Voraussetzung für die gewünschte einfache Shell-/JS-Farbausgabe: Die neue
Kernel-Publikationsgrenze wird eigenständig geprüft, bevor untrusted JS-
Ausgaberecords erweitert werden. JS-Host/Wireformat bleiben hier unverändert.

## Standard und bewusst begrenzter Adapter

Referenz: [ECMA-48](https://ecma-international.org/publications-and-standards/standards/ecma-48/),
SGR-Farbreihenfolge schwarz, rot, grün, gelb, blau, magenta, cyan, weiß.
REIST überträgt diese Auswahl typisiert, nicht als Escape-Sequenz. Vordergrund
0..7 plus ausdrücklich REIST-intensiv 8..15; Hintergrund nur 0..7 (kein VGA-
Blinkbit). Keine ANSI-/VT-/termios-Kompatibilitätszusage. Palette ist die
vorhandene VGA/Framebuffer-Palette, keine freie RGB-, Cursor- oder Geräte-API.

Append-only Syscall131 TERMINAL_WRITE_COLOR mit genau96 Bytes:
uint32 version=1, struct_size=96, descriptor, length, foreground, background,
reserved[2]=0; danach inline text[64]. 1..64 Bytes, druckbares ASCII, TAB
und höchstens ein LF; restliche Textbytes null. Diese Fragmentgrenze hält
synchrone Render-/Scrollarbeit klein. Unicode und mehrzeilige/umfangreichere
Ausgabe gehören in den Ring-3-Adapter, nicht in einen neuen Kernelparser.
Kein Readback/Userpointer im Request, keine Heapallokation, kein Farbzustand.

Der SDK-Aufruf schreibt genau ein Fragment oder meldet einen negativen errno;
keine versteckte Wiederholung, kein Dateifallback. `echo --color red Text`
und die acht Farbnamen sowie `bright-<name>` sind der normale Shell-Zugang.
Vor Ausgabe werden Farbe und alle Argumentbytes/Größen geprüft. Ohne Option
bleibt das bisherige ECHO-Verhalten unverändert. CLI begrenzt Gesamtausgabe
auf4096 Bytes/5s und fragmentiert ohne den Kernelvertrag zu lockern.

## Autorität, Fehler und Lebensdauer

Aktueller Prozess, lesbarer kompletter Request, Version/Größe/Reserved,
Text und Palette werden vor Wirkung geprüft. Der Descriptor muss ein
schreibbarer Terminaldescriptor sein (einschließlich seiner gültigen Aliase),
keine Datei. Die bereits vorhandene CHECK-Operation verlangt die exakte
lebende Vordergrund-PID/Generation. Script-Profile erhalten Syscall131 nicht;
ein nativer JS-Fehler darf keinen direkten Ausgabepfad gewinnen.

Fehler: EFAULT für nicht lesbaren Request; EINVAL für ungültigen Inhalt;
EBADF für ungültigen/nicht schreibbaren FD; ENOTSUP für Nicht-Terminal-FD;
bestehender CHECK-Fehler für fehlenden Vordergrund/Exit; EBUSY bei aktiver
Grafik oder Moduswechsel, vorhandener Mutexfehler bei gescheiterter Reservation.
Keine Ausgabe vor abgeschlossener Admission. Ein erfolgreich zugelassener
synchroner Span darf fertig werden; CHECK ist keine dauerhaft delegierte Lease.

Der vorhandene begrenzte Display-State-Mutex schützt Publikation gegen
Moduswechsel. Kein Prozess-/Input-Spinlock bleibt über Rendering oder UART
gehalten. Kein zeitweiliges Setzen globaler Farben, keine Escape-Auswertung.
Raw-Glyph-Helfer verwenden explizite Farben und validierte Geometrie; der
VGA-Hardwarecursor wird vor Indexbildung geprüft. Scrollhintergrund bleibt
die normale Console-Vorgabe. Serielle Spiegelung ist nur Text, ohne Steuer-
sequenzen. Fehler, Prozessende und Wiederstart hinterlassen keine Farbrechte,
Puffer oder Rücksetzpflicht für die nächste Shellgeneration.

VGA und die bereits initialisierte Boot-Framebuffer-Konsole teilen diesen
Vertrag. Ein aktiver grafischer Desktop wird nicht überzeichnet. Bestehende
Legacy-Ausgabe, deren ANSI-Parser und allgemeine Konsoleninterleavings bleiben
sichtbare Migrationsschuld; dieses Paket behauptet keine vollständige
Terminalisolation oder Reparatur aller alten Ausgabepfade.

## Eingefrorene Abnahme

Exakte Dateiliste und13 Gruppen stehen in der Queue. Regression zuerst:
echter C-Code O0/O2 für Admission, Fehler-vor-Wirkung, Palette, VGA-Glyphen,
Framebuffer-Glyphen, unveränderte globale Farben und Geometriegrenzen;
negative Gast-/Pixelprüfer. Neue ABI-Indizes, Script-Deny und bestehender
Vordergrund-Lifecycle werden separat geprüft. Native Hosttests dialogfrei.

VMware-VGA, QEMU-Framebuffer samt eigener unveränderter Prüfbildkopie,
danach QEMU-VGA. Beide Image-Layouts enthalten ECHO und COLORTST am normalen
Shell-Suchpfad. Authentifizierte R3.42-Referenzen schützen BENCHMARK/MATHTEST/
TEXTTEST bytegenau; keine neue VMware-/WCET-Behauptung aus einem Build.
Headless-QEMU prüft beide Konsolenmodi mit echten Pixeln, normalen ECHO-
Aufrufen, vollständigen Negativfällen, Ende/Reap und anschließender Shell.
Bestehende JS-/Datei-/Beispiel- und Browser-External-Gastgates bleiben bestehen.
Keine sichtbaren VM-Fenster, Agenten, parallelen Builds oder Pushs.

Belege unter `build/codex-agent/r344-terminal-color/`; ursprüngliche Fehler
behalten. Keine spätere JS-Binding-/CLI-Exit-/Dateirechteimplementierung in
diesem Paket. R341-H1/H2 und die R3.6b-Zurückstellung bleiben unverändert.
